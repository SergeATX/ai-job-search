"""ClearanceJobs adapter (stdlib). Public JSON used by the site's own Nuxt front-end:
POST https://api.clearancejobs.com/api/v1/jobs/search  {"keywords":..,"pagination":{"page":N,"size":20}}
No key needed in testing. Location filter 'loc' wants internal numeric ids, so filter client-side to TX/Remote.
Note: undocumented API; ToS risk. Most jobs require an active clearance (a candidate without one will not qualify for most).
"""
import json, time, urllib.request
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
URL = "https://api.clearancejobs.com/api/v1/jobs/search"
KEYWORDS = ["junior software engineer", "entry level software", "software developer", "data analyst", "junior data scientist"]

def _post(body):
    for i in range(3):
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
              headers={"User-Agent": UA, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r: return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            raise
    return {}

def fetch_jobs(slug=None, max_pages=10):
    """slug = one search keyword string (default: several entry-level SWE/data keywords). Keeps TX + remote only."""
    keywords = [slug] if slug else None
    seen, jobs = set(), []
    for kw in keywords or KEYWORDS:
        for p in range(1, max_pages + 1):
            d = _post({"keywords": kw, "pagination": {"page": p, "size": 20}})
            time.sleep(0.6)
            for j in d.get("data", []):
                locs = [(l.get("location") or "") for l in j.get("locations", [])]
                types = [(l.get("type") or "") for l in j.get("locations", [])]
                ok = any(", TX" in l or "Texas" in l for l in locs) or any("emote" in l for l in locs) or any("emote" in t for t in types)
                if not ok or j["job_url"] in seen: continue
                seen.add(j["job_url"])
                jobs.append({"title": j["job_name"], "company": j.get("company_name", ""),
                             "location": "; ".join(locs) or "unspecified", "url": j["job_url"],
                             "posted": (j.get("created_at") or "")[:10], "clearance": j.get("clearance")})
            if not d.get("data") or not d.get("paginator", {}).get("next_page"): break
    return jobs

if __name__ == "__main__":
    js = fetch_jobs(max_pages=5); print(len(js)); [print(j) for j in js[:6]]
