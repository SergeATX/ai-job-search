"""Grow the employer registry automatically from real posting URLs.

Any job URL reveals the employer's ATS and board slug (boards.greenhouse.io/<slug>/..., <x>.wd5.myworkdayjobs.com/<site>/...).
Feed URLs from a curated list (e.g. SimplifyJobs) and every board not yet in the registry is probed live and, if it
returns jobs, saved. Probing is the safety net: a regex match alone is never trusted.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

from .profile import REGISTRY

PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_app\?for=)?([A-Za-z0-9_-]+)")),
    ("lever", re.compile(r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_.-]+)")),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)")),
    ("smartrecruiters", re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)")),
    ("workable", re.compile(r"apply\.workable\.com/([A-Za-z0-9_-]+)")),
    ("rippling", re.compile(r"ats\.rippling\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)/jobs")),
    ("bamboohr", re.compile(r"https?://([a-z0-9-]+)\.bamboohr\.com/")),
]
WORKDAY = re.compile(r"https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)")
ORACLE = re.compile(r"https?://([a-z0-9.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[a-zA-Z_-]+/sites/([A-Za-z0-9_]+)")
ICIMS = re.compile(r"https?://([a-z0-9-]+)\.icims\.com/")
SKIP_SLUGS = {"embed", "jobs", "careers", "api", "v1", "j"}


def classify(urls):
    ats, workday, icims, oracle = {}, {}, {}, {}
    for u in urls:
        m = ORACLE.match(u or "")
        if m:
            oracle[m.group(1).split('.')[0]] = {"host": m.group(1), "site": m.group(2)}
            continue
        m = WORKDAY.match(u or "")
        if m:
            tenant, wd, site = m.groups()
            workday[f"{tenant}"] = {"subdomain": f"{tenant}.{wd}", "tenant": tenant, "site": site}
            continue
        m = ICIMS.match(u or "")
        if m:
            icims[m.group(1)] = {"tenant": m.group(1)}
            continue
        for kind, rx in PATTERNS:
            m = rx.search(u or "")
            if m and m.group(1).lower() not in SKIP_SLUGS:
                ats[m.group(1)] = kind
                break
    return ats, workday, icims, oracle


def _load(name):
    p = REGISTRY / name
    return json.loads(p.read_text()) if p.exists() else {}


def _probe_ats(slug, kind):
    from .sources import ats, bamboohr, rippling, smartrecruiters, workable
    fn = {"smartrecruiters": smartrecruiters.fetch_jobs, "workable": workable.fetch_jobs,
          "bamboohr": bamboohr.fetch_jobs, "rippling": rippling.fetch_jobs}.get(kind)
    return len(fn(slug)) if fn else len(ats.fetch_jobs(slug, kind))


def _probe_workday(cfg):
    from .sources import workday
    return len(workday.fetch_all_jobs(cfg["subdomain"], cfg["tenant"], cfg["site"], max_results=20))


def _probe_icims(cfg):
    from .sources import icims
    return len(icims.fetch_all_jobs(cfg["tenant"], max_pages=1))


def _probe_oracle(cfg):
    from .sources import oracle
    return len(oracle.fetch_jobs(cfg["host"], cfg["site"], max_jobs=50))


def discover(urls, save=True, workers=24):
    ats, workday, icims, oracle = classify(urls)
    wl = _load("watchlist.json")
    known_ats = set(wl["confirmed"]) | set(wl.get("not_on_these_ats", []))
    known_ats_l = {k.lower() for k in known_ats}
    wd, ic, orc = _load("workday_sites.json"), _load("icims_sites.json"), _load("oracle_sites.json")
    known_wd = {(v["subdomain"], v["site"]) for v in wd.values()}
    todo = []
    todo += [("ats", s, k) for s, k in ats.items() if s.lower() not in known_ats_l]
    todo += [("workday", s, c) for s, c in workday.items() if (c["subdomain"], c["site"]) not in known_wd and s not in wd]
    todo += [("icims", s, c) for s, c in icims.items() if s not in ic]
    known_or = {(v["host"], v["site"]) for v in orc.values()}
    todo += [("oracle", s, c) for s, c in oracle.items() if (c["host"], c["site"]) not in known_or]

    def probe(t):
        kind, slug, v = t
        try:
            n = {"ats": lambda: _probe_ats(slug, v), "workday": lambda: _probe_workday(v), "icims": lambda: _probe_icims(v), "oracle": lambda: _probe_oracle(v)}[kind]()
        except Exception:
            n = 0
        return t, n

    added = {"ats": 0, "workday": 0, "icims": 0, "oracle": 0}
    with ThreadPoolExecutor(workers) as ex:
        for (kind, slug, v), n in ex.map(probe, todo):
            if n <= 0:
                continue  # empty/unreachable board or slug collision: never saved
            added[kind] += 1
            if kind == "ats":
                wl["confirmed"][slug] = v
            elif kind == "workday":
                wd[slug] = v
            elif kind == "oracle":
                orc[slug] = v
            else:
                ic[slug] = v
    if save:
        for name, data in (("watchlist.json", wl), ("workday_sites.json", wd), ("icims_sites.json", ic), ("oracle_sites.json", orc)):
            (REGISTRY / name).write_text(json.dumps(data, indent=2) + "\n")
    return {"candidates": len(todo), "added": added}


def _slugs(name, website=None):
    base = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|company|technologies|technology|holdings|group)\b\.?", "", name, flags=re.I)
    plain = re.sub(r"[^a-z0-9]", "", base.lower())
    dash = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    out = {plain, dash}
    if website:
        m = re.match(r"https?://(?:www\.)?([a-z0-9-]+)\.", website.lower())
        if m:
            out.add(m.group(1))
    return {s for s in out if len(s) >= 3}


def discover_names(entries, save=True, workers=24):
    """entries: iterable of (name, website-or-None). Probes greenhouse/lever/ashby/workable/smartrecruiters/rippling by slug."""
    wl = _load("watchlist.json")
    known = {k.lower() for k in wl["confirmed"]} | {k.lower() for k in wl.get("not_on_these_ats", [])}
    todo = []
    for name, site in entries:
        for s in _slugs(name, site):
            if s not in known:
                known.add(s)  # one attempt per slug per run
                todo += [(s, k) for k in ("greenhouse", "lever", "ashby", "workable", "smartrecruiters", "rippling")]

    def probe(t):
        try:
            return t, _probe_ats(*t)
        except Exception:
            return t, 0

    found = {}
    with ThreadPoolExecutor(workers) as ex:
        for (slug, kind), n in ex.map(probe, todo):
            if n > 0 and slug not in found:
                found[slug] = kind
    wl["confirmed"].update(found)
    if save:
        (REGISTRY / "watchlist.json").write_text(json.dumps(wl, indent=2) + "\n")
    return {"probes": len(todo), "found": len(found)}
