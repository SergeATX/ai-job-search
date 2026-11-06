"""Amazon's own careers site (amazon.jobs), US jobs. slug = "amazon.jobs" (or "amazon.jobs|<country code>").

Endpoint: https://www.amazon.jobs/en/search.json?country=USA&sort=recent&offset=N&result_limit=100 (100 a page, with
each job's description and qualifications). A query lists at most 10,000 jobs, and the US has more, so a query that
reaches the cap is read job category by category (category[]; each job has one, so the slices add up to the whole).
About 125 requests for the US's ~12,400 jobs."""
import datetime
import json
import sys
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
BASE = "https://www.amazon.jobs"
PAGE, CAP, GAP = 100, 10000, 1.0  # GAP: seconds between requests


def _get(q):
    req = urllib.request.Request(f"{BASE}/en/search.json?" + urllib.parse.urlencode(q, doseq=True),
                                 headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def _places(j):
    out = []
    for s in j.get("locations") or []:
        try:
            loc = json.loads(s) if isinstance(s, str) else s
        except ValueError:
            continue
        if loc.get("normalizedLocation"):
            out.append(loc["normalizedLocation"])
    return "; ".join(dict.fromkeys(out)) or j.get("normalized_location") or j.get("location")


def _posted(s):
    try:
        return datetime.datetime.strptime(" ".join((s or "").split()), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _job(j):
    parts = [j.get("description"), j.get("basic_qualifications") and "<h3>Basic qualifications</h3>" + j["basic_qualifications"],
             j.get("preferred_qualifications") and "<h3>Preferred qualifications</h3>" + j["preferred_qualifications"]]
    return {"title": j.get("title"), "company": "Amazon", "location": _places(j), "url": BASE + (j.get("job_path") or ""),
            "posted": _posted(j.get("posted_date")), "description_html": "<br/>".join(p for p in parts if p)}


def _read(q, out, first=None):
    """Every page of one query. -> its hit count."""
    hits, offset = None, 0
    while True:
        d = first if offset == 0 and first else _get({**q, "offset": offset, "result_limit": PAGE, "sort": "recent"})
        hits = d.get("hits") or 0 if hits is None else hits
        jobs = d.get("jobs") or []
        for j in jobs:
            out.setdefault(j.get("id_icims") or j.get("id"), j)
        offset += PAGE
        if len(jobs) < PAGE or offset >= min(hits, CAP):
            return hits
        time.sleep(GAP)


def fetch_jobs(slug="amazon.jobs"):
    q, out = {"country": (slug or "").partition("|")[2] or "USA"}, {}
    first = _get({**q, "offset": 0, "result_limit": PAGE, "sort": "recent", "facets[]": ["category"]})
    if (first.get("hits") or 0) < CAP:
        _read(q, out, first)
    else:  # past the 10,000 a query can list: one query per job category
        cats = [k for f in (first.get("facets") or {}).get("category_facet") or [] for k in f]
        for c in cats:
            time.sleep(GAP)
            if _read({**q, "category[]": c}, out) >= CAP:
                raise ValueError(f"amazon.jobs: {c} alone lists over {CAP} jobs, more than a query can read")
    return [_job(j) for j in out.values()]


if __name__ == "__main__":
    t = time.time()
    js = fetch_jobs(sys.argv[1] if len(sys.argv) > 1 else "amazon.jobs")
    print(len(js), "jobs in", round(time.time() - t), "s")
    print({k: (v[:100] if isinstance(v, str) else v) for k, v in js[0].items()})
