"""USAJOBS adapter (stdlib). Official data.usajobs.gov API needs a free key (Authorization-Key + User-Agent=email)
-> returns 401 without it. NOT used here. Instead uses the site's own public search JSON:
POST https://www.usajobs.gov/Search/ExecuteSearch  (JSON body, no key/cookie/token needed in testing, 25/page).
"""
import json, time, urllib.request
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
URL = "https://www.usajobs.gov/Search/ExecuteSearch"
KEYWORDS = ["software", "developer", "data scientist", "data analyst", "computer science", "IT specialist 2210", "Pathways"]

def _post(body):
    for i in range(3):
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
            headers={"User-Agent": UA, "Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            raise
    return {}

def fetch_jobs(slug="2210@Texas", max_pages=8):
    """slug = "<query>[@<location>]". A 4-digit query is an occupational series (JobCategoryCode filter, e.g. 2210 IT Mgmt,
    1550 Computer Science, 1560 Data Science); anything else is a free-text Keyword. Location defaults to Texas
    (use "@" with nothing for nationwide). Examples: "2210@Texas", "software@Texas", "Johnson Space Center", "1550@Texas"."""
    q, _, loc = slug.partition("@")
    body0 = {"JobCategoryCode": [q]} if q.isdigit() and len(q) == 4 else {"Keyword": q}
    if "@" not in slug: loc = "Texas"
    if loc: body0["LocationName"] = [loc]
    seen, jobs = set(), []
    for p in range(1, max_pages + 1):
        d = _post({**body0, "Page": str(p)})
        time.sleep(0.6)
        for j in d.get("Jobs", []):
            u = j["PositionURI"].replace(":443", "")
            if u in seen: continue
            seen.add(u)
            jobs.append({"title": j["Title"], "company": f'{j["Agency"]} ({j.get("Department","")})',
                         "location": j["LocationDisplay"], "url": u,
                         "posted": (j.get("PositionStartDate") or "")[:10]})
        if not d.get("Pager", {}).get("HasNextPage"): break
    return jobs

if __name__ == "__main__":
    import sys
    js = fetch_jobs(sys.argv[1] if len(sys.argv) > 1 else "2210@Texas")
    print(len(js)); [print(j) for j in js[:6]]
