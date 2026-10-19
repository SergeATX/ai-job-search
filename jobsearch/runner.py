import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import filters
from .profile import REGISTRY
from .store import Store


def _reg(name):
    return json.loads((REGISTRY / name).read_text())


def _terms(p):
    """search_text may be one string or a list; each term is a separate server-side query (deduped by URL later)."""
    t = p.search_text
    return list(t) if isinstance(t, (list, tuple)) else [t]


def _tasks(p):
    """Yield (source, company, zero-arg fetcher returning raw jobs)."""
    srcs = p.sources
    if "ats" in srcs:
        from .sources import ats, bamboohr, rippling, smartrecruiters, workable
        direct = {"rippling": rippling.fetch_jobs, "smartrecruiters": smartrecruiters.fetch_jobs, "workable": workable.fetch_jobs, "bamboohr": bamboohr.fetch_jobs}
        for co, kind in _reg("watchlist.json")["confirmed"].items():
            fn = direct.get(kind)
            yield "ats", co, ((lambda co=co, fn=fn: fn(co)) if fn else (lambda co=co, kind=kind: ats.fetch_jobs(co, kind)))
    if "workday" in srcs:
        from .sources import workday
        for co, c in _reg("workday_sites.json").items():
            def f(c=c):
                out = []
                for term in _terms(p):
                    out += workday.fetch_all_jobs(c["subdomain"], c["tenant"], c["site"], search_text=term)
                return out
            yield "workday", co, f
    if "icims" in srcs:
        from .sources import icims
        for co, c in _reg("icims_sites.json").items():
            yield "icims", co, (lambda c=c: icims.fetch_all_jobs(c["tenant"]))
    if "oracle" in srcs:
        from .sources import oracle
        for co, c in _reg("oracle_sites.json").items():
            def f(c=c):
                out = []
                for term in _terms(p):
                    out += oracle.fetch_jobs(c["host"], c["site"], keyword=term)
                return out
            yield "oracle", co, f
    if "simplify" in srcs:
        from .sources import simplify
        yield "simplify", "simplify", simplify.fetch_jobs
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


def run(p, dry_run=False, workers=8):
    store = Store(p.db_path)
    tasks = [t for t in _tasks(p) if p.company_ok(t[1])]
    raw = new = 0
    errors, per_company = [], {}
    shortlist = []
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(t[2]): t for t in tasks}
        for fut in as_completed(futs):
            source, company, _ = futs[fut]
            try:
                jobs = fut.result()
            except Exception as e:  # one broken site must not sink the run
                errors.append(f"{source}/{company}: {e}")
                continue
            raw += len(jobs)
            for j in jobs:
                j = _norm(j, source, company)
                if not j["url"] or not filters.keep(j, p) or store.seen(j["url"]):
                    continue
                if not dry_run:
                    store.add(j)
                shortlist.append(j)
                per_company[company] = per_company.get(company, 0) + 1
    # a job can be returned twice in one run (e.g. several locations) - collapse by url
    uniq = {j["url"].split("?")[0]: j for j in shortlist}
    shortlist = sorted(uniq.values(), key=lambda j: (j["company"], j["title"] or ""))
    if not dry_run:
        # the shortlist is every not-yet-reviewed candidate, so re-running never loses unreviewed rows
        pending = [dict(zip(("company", "title", "location", "source", "url"), r)) for r in store.candidates()]
        write_shortlist(p, pending)
    print(f"[{p.name}] {len(tasks)} sources, {raw} raw postings, {len(shortlist)} new candidates, {len(errors)} errors")
    for c, n in sorted(per_company.items(), key=lambda x: -x[1])[:8]:
        print(f"  {c}: {n}")
    for e in errors[:10]:
        print(f"  ! {e}", file=sys.stderr)
    return shortlist


def write_shortlist(p, shortlist):
    sl = p.out_dir / "shortlist.md"
    boost = re.compile(p.cfg["titles"]["boost"], re.I) if p.cfg["titles"].get("boost") else None
    mark = lambda j: bool(boost and boost.search(j["title"] or ""))
    shortlist = sorted(shortlist, key=lambda j: (not mark(j), j["company"] or "", j["title"] or ""))
    sl.write_text("\n".join(f"- {'★ ' if mark(j) else ''}{j['title']} | {j['company']} | {j['location']} | {j['url']}" for j in shortlist) + "\n")
    notes = p.fitcheck_notes or ""
    gates = "\n".join(f"- {g}" for g in p.gates)
    resume = p.resume or "(no resume path configured)"
    (p.out_dir / "fitcheck-prompt.md").write_text(f"""You are a resume-fit-check agent for the job-search profile "{p.name}".

1. Read the candidate's resume: {resume}
2. Candidates are listed in {sl} (one per line: title | company | location | url). Fetch each posting's full description
   (Greenhouse: boards-api.greenhouse.io/v1/boards/<co>/jobs/<id>; Lever: api.lever.co/v0/postings/<co>/<id>;
   Workday: POST/GET the /wday/cxs/... job JSON; otherwise WebFetch). Work in parallel batches.
3. Disqualify ONLY for these gates (anything else is a fit, even a different stack):
{gates}
{notes}
4. Verdicts: GOOD / WEAK / SKIP. Quote the deciding requirement text.
5. Write JSON to {p.out_dir}/fitcheck.json: a list of {{"url","title","company","location","verdict","reason"}}.
   Do not edit trackers or send email. Final report: counts plus a table of GOOD and WEAK rows.
""")
