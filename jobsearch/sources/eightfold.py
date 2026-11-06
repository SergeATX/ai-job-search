"""Eightfold AI career-site adapter (urllib only). slug = "<subdomain>|<domain>" e.g. "lockheedmartin|lockheedmartin.com",
or "<careers host>|<domain>" for a site on its own domain ("apply.careers.microsoft.com|microsoft.com").

- search: https://<host>/api/pcsx/search?domain=<domain>&start=N&num=10 (10 a page whatever num asks, newest first)
- one job, with its description: /api/pcsx/position_details?position_id=<id>&domain=<domain>
- every open job's id and last change: /careers/sitemap.xml (one request; not every site has it)

The sites answer 429 to a burst (Lockheed Martin after ~9 requests in 4s; Microsoft after 2-3 at one a second), so
requests to one host are spaced (GAP, widened after each 429) and a 429 is waited out and retried: a few times, or
with stop_at until then (Microsoft answers about half its requests with 429 even six seconds apart)."""
import datetime
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
GAP, MAX_GAP = 1.0, 6.0  # seconds between request starts to one host; each 429 widens it by half, up to MAX_GAP
BACKOFF = (5, 10, 20, 30)  # seconds waited after each 429 in a row; with stop_at, the last repeats until then
_lock = threading.Lock()
_hosts = {}  # host -> [gap, time of the last request start]


def host_domain(slug):
    sub, _, domain = slug.partition("|")
    return (sub if "." in sub else f"{sub}.eightfold.ai"), domain


def _get(host, path, q=None, accept="application/json", stop_at=None):
    url = f"https://{host}{path}" + ("?" + urllib.parse.urlencode(q) if q else "")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    attempt = 0
    while True:
        with _lock:
            st = _hosts.setdefault(host, [GAP, 0.0])
            wait = st[1] + st[0] - time.time()
            st[1] = time.time() + max(0.0, wait)
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            return json.loads(body) if accept == "application/json" else body.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            pause = BACKOFF[min(attempt, len(BACKOFF) - 1)]
            if e.code != 429 or (attempt >= len(BACKOFF) if stop_at is None else time.time() + pause > stop_at):
                raise
            with _lock:
                st[0] = min(MAX_GAP, st[0] * 1.5)
            time.sleep(pause)
            attempt += 1


def _day(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d") if ts else None


def _job(host, domain, p):
    j = {"id": str(p.get("id")), "title": p.get("name"), "company": domain,
         "location": "; ".join(p.get("locations") or []),
         "url": f"https://{host}{p.get('positionUrl') or '/careers/job/' + str(p.get('id'))}",
         "posted": _day(p.get("postedTs") or p.get("creationTs"))}
    if p.get("jobDescription"):
        j["description_html"] = p["jobDescription"]
    return j


def search_page(slug, start, location="", stop_at=None):
    """-> (jobs on the page, the listing's total)."""
    host, domain = host_domain(slug)
    q = {"domain": domain, "query": "", "start": start, "num": 10, "sort_by": "timestamp"}
    if location:
        q["location"] = location
    d = _get(host, "/api/pcsx/search", q, stop_at=stop_at).get("data") or {}
    return [_job(host, domain, p) for p in d.get("positions") or []], d.get("count") or 0


def position(slug, pid, stop_at=None):
    """One job with its description_html, or None when the site has no such job."""
    host, domain = host_domain(slug)
    d = _get(host, "/api/pcsx/position_details", {"position_id": pid, "domain": domain, "hl": "en"}, stop_at=stop_at)
    d = d.get("data") or {}
    return _job(host, domain, d) if d.get("id") else None


def sitemap(slug):
    """{job id: last change (YYYY-MM-DD or None)} for every open job, or None when the site publishes no sitemap."""
    host, _ = host_domain(slug)
    try:
        page = _get(host, "/careers/sitemap.xml", accept="application/xml")
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return None
        raise
    if "<urlset" not in page:
        return None  # a redirect to the site's home page
    out = {}
    for block in re.findall(r"<url>(.*?)</url>", page, re.S):
        m = re.search(r"/careers/job/(\d+)", block)
        if m:
            lm = re.search(r"<lastmod>(\d{4}-\d\d-\d\d)", block)
            out[m[1]] = lm[1] if lm else None
    return out


def fetch_jobs(slug, max_jobs=2000, location=""):
    out, start = [], 0
    while start < max_jobs:
        jobs, _ = search_page(slug, start, location)
        out += jobs
        if len(jobs) < 10:
            break
        start += len(jobs)
    return out


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "lockheedmartin|lockheedmartin.com"
    js = fetch_jobs(slug, max_jobs=30)
    print(len(js), "jobs"); [print(j) for j in js[:3]]
    sm = sitemap(slug)
    print(None if sm is None else f"sitemap: {len(sm)} jobs")
    if js:
        print({k: (v[:80] if isinstance(v, str) else v) for k, v in (position(slug, js[0]["id"]) or {}).items()})
