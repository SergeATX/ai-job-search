import importlib
import json
import random
import re
import sys
import threading
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import filters
from .profile import REGISTRY
from .store import Store


# Rate limits are enforced per host, so concurrency and spacing are limited per host (not per vendor), failures that
# look transient are retried with exponential backoff + jitter (honouring Retry-After), and tasks are shuffled so
# consecutive requests rarely hit the same host.
_LIMITS = {"workable": 3, "smartrecruiters": 6, "rippling": 6, "bamboohr": 6, "icims": 6,
           "greenhouse": 8, "lever": 6, "ashby": 6}  # concurrent requests per host key; default _DEFAULT_LIMIT
_DEFAULT_LIMIT = 3
_SPACING = {"workday": 0.3}  # min seconds between request starts per host key prefix; default _DEFAULT_SPACING
_DEFAULT_SPACING = 0.1
_TRANSIENT = {429, 500, 502, 503, 504, 520, 522, 524}
_host_lock = threading.Lock()
_hosts = {}  # key -> (semaphore, spacing lock, [last start time])


def _host(key):
    with _host_lock:
        if key not in _hosts:
            lim = _LIMITS.get(key, _LIMITS.get(key.split(":")[0], 2 if key.startswith("workday:") else _DEFAULT_LIMIT))
            _hosts[key] = (threading.Semaphore(lim), threading.Lock(), [0.0])
        return _hosts[key]


def _transient(e):
    if isinstance(e, urllib.error.HTTPError):
        return e.code in _TRANSIENT
    return isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)) and not isinstance(e, urllib.error.HTTPError)


_MAX_WAIT = 120  # longest Retry-After we sleep through; Workable sends 8+ hours, which used to park every worker thread


class HostBlocked(Exception):
    """The host asked us to come back later than _MAX_WAIT: give up on it for now instead of sleeping."""
    code = 429

    def __init__(self, retry_after, cause):
        super().__init__(f"{cause} (Retry-After {int(retry_after)}s)")
        self.retry_after = retry_after


def _wait(e, attempt):
    ra = getattr(e, "headers", None) and e.headers.get("Retry-After")
    ra = float(ra) if ra and str(ra).replace(".", "", 1).isdigit() else None
    if ra is not None and ra > _MAX_WAIT:
        raise HostBlocked(ra, e) from e
    base = ra if ra is not None else min(60, 3 * 2 ** attempt)
    time.sleep(base + random.uniform(0, 2))


def _guarded(key, fn, attempts=5):
    sem, spacing_lock, last = _host(key)
    gap = _SPACING.get(key.split(":")[0], _DEFAULT_SPACING)

    def run():
        for attempt in range(attempts):
            try:
                with sem:
                    with spacing_lock:  # serialise request *starts* per host, not the requests themselves
                        time.sleep(max(0.0, last[0] + gap - time.time()))
                        last[0] = time.time()
                    return fn()
            except Exception as e:
                if not _transient(e) or attempt == attempts - 1:
                    raise
                _wait(e, attempt)
    return run


def _reg(name):
    return json.loads((REGISTRY / name).read_text())


def _terms(p):
    """search_text may be one string or a list; each term is a separate server-side query (deduped by URL later)."""
    t = p.search_text
    return list(t) if isinstance(t, (list, tuple)) else [t]


def _tasks(p):
    """Yield (source, company, zero-arg fetcher returning raw jobs)."""
    srcs = p.sources
    for tier, reg_file in (("ats", "watchlist.json"), ("ats_ext", "watchlist_extended.json")):
        # "ats_ext" = bulk-mined boards (Common Crawl, VC portfolios): same fetchers, separate source name so it can
        # run on a slower source_cadence and show up separately in `jobsearch yield`
        if tier not in srcs:
            continue
        from .sources import ats, bamboohr, breezy, personio, recruitee, rippling, smartrecruiters, teamtailor, workable
        direct = {"rippling": rippling.fetch_jobs, "smartrecruiters": smartrecruiters.fetch_jobs, "workable": workable.fetch_jobs, "bamboohr": bamboohr.fetch_jobs,
                  "recruitee": recruitee.fetch_jobs, "breezy": breezy.fetch_jobs, "personio": personio.fetch_jobs, "teamtailor": teamtailor.fetch_jobs}
        for co, kind in _reg(reg_file)["confirmed"].items():
            fn = direct.get(kind)
            yield tier, co, _guarded(kind, (lambda co=co, fn=fn: fn(co)) if fn else (lambda co=co, kind=kind: ats.fetch_jobs(co, kind)))
    if "workday" in srcs:
        from .sources import workday
        for co, c in _reg("workday_sites.json").items():
            def f(c=c):
                out = []
                for term in _terms(p):
                    out += workday.fetch_all_jobs(c["subdomain"], c["tenant"], c["site"], search_text=term)
                return out
            yield "workday", co, _guarded(f"workday:{c['subdomain']}", f)
    if "icims" in srcs:
        from .sources import icims
        for co, c in _reg("icims_sites.json").items():
            yield "icims", co, _guarded("icims", lambda c=c: icims.fetch_all_jobs(c["tenant"]))
    if "oracle" in srcs:
        from .sources import oracle
        for co, c in _reg("oracle_sites.json").items():
            def f(c=c):
                out = []
                for term in _terms(p):
                    out += oracle.fetch_jobs(c["host"], c["site"], keyword=term)
                return out
            yield "oracle", co, _guarded(f"oracle:{c['host']}", f)
    if "simplify" in srcs:
        from .sources import simplify
        yield "simplify", "simplify", simplify.fetch_jobs
    for name in ("builtin", "muse", "capps", "remote_boards"):
        if name in srcs:
            mod = importlib.import_module(f".sources.{name}", __package__)
            opts = (p.cfg.get("source_options") or {}).get(name) or {}
            yield name, name, _guarded(name, lambda mod=mod, opts=opts: mod.fetch_jobs(**opts))
    if "jibe" in srcs:
        from .sources import jibe
        for co, c in _reg("jibe_sites.json").items():
            def f(c=c):
                out = []
                for cat in c.get("categories") or [None]:
                    out += jibe.fetch_jobs(c["domain"], category=cat)
                return out
            yield "jibe", co, f


def _norm(job, source, company):
    loc = job.get("location")
    if not loc and (job.get("city") or job.get("state")):
        loc = ", ".join(x for x in (job.get("city"), job.get("state")) if x)
    return {"title": job.get("title"), "location": loc, "url": job.get("url"),
            "company": job.get("company") or company, "source": source}


def _cadence_filter(p, tasks, force):
    """Drop sources scanned more recently than the profile's `source_cadence: {source: days}` allows (low-yield, slow
    sources need not run every batch). -> (tasks, skipped source names, state dict, path)"""
    path = p.out_dir / "source-state.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    cad = p.cfg.get("source_cadence") or {}
    skipped = set()
    if not force:
        today = time.time()
        for src, days in cad.items():
            last = state.get(src)
            if last and today - time.mktime(time.strptime(last, "%Y-%m-%d")) < (float(days) - 0.5) * 86400:
                skipped.add(src)
    return [t for t in tasks if t[0] not in skipped], sorted(skipped), state, path


def run(p, dry_run=False, workers=8, force_all=False, subset=False):
    store = Store(p.db_path)
    tasks = [t for t in _tasks(p) if p.company_ok(t[1])]
    skipped_src, state, state_path = [], {}, None
    if not subset:  # an explicit --sources subset always scans exactly what was asked
        tasks, skipped_src, state, state_path = _cadence_filter(p, tasks, force_all)
        if skipped_src:
            print(f"[{p.name}] skipping recently scanned low-yield sources (source_cadence): {', '.join(skipped_src)}; use --all to force", flush=True)
    random.Random(time.strftime("%Y%m%d%H")).shuffle(tasks)  # spread consecutive requests across hosts
    raw = new = 0
    errors, per_company = [], {}
    shortlist = []
    def handle(source, company, jobs):
        nonlocal raw
        raw += len(jobs)
        for j in jobs:
            j = _norm(j, source, company)
            if not j["url"] or not filters.keep(j, p) or store.seen(j["url"]):
                continue
            if not dry_run:
                store.add(j)
            shortlist.append(j)
            per_company[company] = per_company.get(company, 0) + 1

    def sweep(batch, nworkers):
        """-> list of (task, exception) that failed. Prints a progress line every 10% so long scans are never silent."""
        failed, done, started = [], 0, time.time()
        step = max(1, len(batch) // 10)
        with ThreadPoolExecutor(nworkers) as ex:
            futs = {ex.submit(t[2]): t for t in batch}
            for fut in as_completed(futs):
                done += 1
                if done % step == 0 or done == len(batch):
                    print(f"[{p.name}] progress {done}/{len(batch)} ({round(100 * done / len(batch))}%), {len(shortlist)} new so far, "
                          f"{len(failed)} failed, {int(time.time() - started)}s elapsed", flush=True)
                t = futs[fut]
                try:
                    handle(t[0], t[1], fut.result())
                except Exception as e:  # one broken site must not sink the run
                    failed.append((t, e))
        return failed

    failed = sweep(tasks, workers)
    again = [t for t, e in failed if _transient(e)]
    recovered = 0
    if again:  # second pass: only transient failures (429/5xx/timeouts), slowly, after a cooldown
        print(f"[{p.name}] retrying {len(again)} transient failures after a cooldown...")
        time.sleep(20)
        failed2 = sweep(again, 2)
        recovered = len(again) - len(failed2)
        failed = [(t, e) for t, e in failed if not _transient(e)] + failed2
    errors = [f"{t[0]}/{t[1]}: {e}" for t, e in failed]
    if state_path and not dry_run:
        today = time.strftime("%Y-%m-%d")
        for src in {t[0] for t in tasks}:
            state[src] = today
        state_path.write_text(json.dumps(state, indent=1))
    # a job can be returned twice in one run (e.g. several locations) - collapse by url
    uniq = {j["url"].split("?")[0]: j for j in shortlist}
    shortlist = sorted(uniq.values(), key=lambda j: (j["company"], j["title"] or ""))
    if not dry_run:
        # the shortlist is every not-yet-reviewed candidate, so re-running never loses unreviewed rows
        pending = [dict(zip(("company", "title", "location", "source", "url"), r)) for r in store.candidates()]
        write_shortlist(p, pending)
    print(f"[{p.name}] {len(tasks)} sources, {raw} raw postings, {len(shortlist)} new candidates, {len(errors)} errors"
          + (f" ({recovered} recovered on retry)" if recovered else ""))
    print(f"  coverage: {len(tasks) - len(errors)}/{len(tasks)} sources scanned ({round(100 * (len(tasks) - len(errors)) / max(1, len(tasks)), 1)}%)")
    for c, n in sorted(per_company.items(), key=lambda x: -x[1])[:8]:
        print(f"  {c}: {n}")
    if errors:
        from collections import Counter
        kinds = Counter((e.split(":", 1)[0].split("/")[0], e.split(": ", 1)[-1][:28]) for e in errors)
        print("  errors by (source, kind): " + "; ".join(f"{s}/{k} x{n}" for (s, k), n in kinds.most_common(6)))
        (p.out_dir / "errors.log").write_text("\n".join(errors) + "\n")
    return shortlist


def write_shortlist(p, shortlist):
    sl = p.out_dir / "shortlist.md"
    boost = re.compile(p.cfg["titles"]["boost"], re.I) if p.cfg["titles"].get("boost") else None
    mark = lambda j: bool(boost and boost.search(j["title"] or ""))
    shortlist = sorted(shortlist, key=lambda j: (not mark(j), j["company"] or "", j["title"] or ""))
    sl.write_text("\n".join(f"- {'★ ' if mark(j) else ''}{j['title']} | {j['company']} | {j['location']} | {j['url']}" for j in shortlist) + "\n")
    (p.out_dir / "fitcheck-prompt.md").write_text(fitcheck_prompt(p, p.out_dir))


def fitcheck_prompt(p, base):
    """Prompt for a fit-check agent whose queue, posting texts and output all live under `base`."""
    labels = p.cfg.get("resume_labels") or []
    label_rule = f', "resume" (one of: {", ".join(labels)} - which of the candidate\'s resumes fits best)' if labels else ""
    notes = p.fitcheck_notes or ""
    gates = "\n".join(f"- {g}" for g in p.gates)
    resume = p.resume or "(no resume path configured)"
    return f"""You are a resume-fit-check agent for the job-search profile "{p.name}".

1. Read the candidate's resume: {resume}
2. The queue is {base}/fitcheck-queue.json (a list of {{n,title,company,locations,urls,prescreen,note}}). Each posting's text is already on disk
   at {base}/jd/<n>.txt - read that file; do NOT re-fetch the web unless the file is empty (then WebFetch urls[0]).
   Mechanical gates (explicit years, clearance, graduate degree) were already applied; you judge what is left.
   prescreen=WEAK means a soft/1-year experience mention: read it in context.
3. Disqualify ONLY for these gates (anything else is a fit, even a different stack):
{gates}
{notes}
4. Verdicts: GOOD / WEAK / SKIP. Quote the deciding requirement text. A verdict applies to every url of the group.
5. Write JSON to {base}/fitcheck.json: a list of {{"url","title","company","location","verdict","reason","missing_skills"{label_rule}}} - one row per url in the group.
   "missing_skills" is REQUIRED on every GOOD/WEAK row: a list of short canonical skill/tool names (e.g. "Docker", "TypeScript", "Kubernetes") that the posting asks for and the resume lacks; [] if none.
   Skills only - no years-of-experience, no domain facts.
   Do not edit trackers or send email. Final report: counts plus a table of GOOD and WEAK rows.
"""
