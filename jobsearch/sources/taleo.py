"""Oracle Taleo (careersection) adapter, urllib only. slug = "<host>|<section>" e.g. "textron.taleo.net|bell".
Discovers the portal id from the jobsearch page, then POSTs /careersection/rest/jobboard/searchjobs."""
import json, re, sys, urllib.request, http.cookiejar
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
EMPTY = [{"id": i, "selectedValues": []} for i in ("POSTING_DATE", "LOCATION", "JOB_FIELD", "JOB_TYPE", "JOB_SCHEDULE", "JOB_LEVEL")]


def fetch_jobs(slug, max_jobs=2000):
    host, _, sec = slug.partition("|")
    base = f"https://{host}/careersection"
    html = OP.open(urllib.request.Request(f"{base}/{sec}/jobsearch.ftl?lang=en", headers={"User-Agent": UA}), timeout=30).read().decode("utf8", "ignore")
    m = re.search(r"portal=(\d+)", html) or re.search(r"portalNo[\"':= ]+(\d+)", html)
    portal = m.group(1) if m else ""
    out, page = [], 1
    while len(out) < max_jobs:
        body = {"multilineEnabled": False, "sortingSelection": {"sortBySelectionParam": "3", "ascendingSortingOrder": "false"},
                "fieldData": {"fields": {"KEYWORD": "", "LOCATION": ""}, "valid": True},
                "filterSelectionParam": {"searchFilterSelections": EMPTY},
                "advancedSearchFiltersSelectionParam": {"searchFilterSelections": [{"id": i, "selectedValues": []} for i in ("ORGANIZATION", "LOCATION", "JOB_FIELD", "JOB_NUMBER", "URGENT_JOB", "EMPLOYEE_STATUS", "STUDY_LEVEL", "WILL_TRAVEL", "JOB_SHIFT")]},
                "pageNo": page}
        req = urllib.request.Request(f"{base}/rest/jobboard/searchjobs?lang=en&portal={portal}", data=json.dumps(body).encode(),
                                     headers={"User-Agent": UA, "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest", "tz": "GMT-06:00", "Referer": f"{base}/{sec}/jobsearch.ftl?lang=en"})
        d = json.loads(OP.open(req, timeout=30).read())
        rl = d.get("requisitionList") or []
        for r in rl:
            c = r.get("column") or []
            # columns: title, (req no), location (json list string), posted date ...
            loc = c[1] if len(c) > 1 else ""
            try: loc = ", ".join(json.loads(loc)) if loc.startswith("[") else loc
            except Exception: pass
            out.append({"title": c[0] if c else None, "company": host.split(".")[0], "location": loc,
                        "url": f"https://{host}/careersection/{sec}/jobdetail.ftl?job={r.get('jobId')}&lang=en",
                        "posted": c[2] if len(c) > 2 else None})
        pg = d.get("pagingData") or {}
        if not rl or page * (pg.get("pageSize") or len(rl)) >= (pg.get("totalCount") or 0): break
        page += 1
    return out

if __name__ == "__main__":
    for s in (sys.argv[1:] or ["textron.taleo.net|bell"]):
        js = fetch_jobs(s, 40); print(s, len(js)); [print(j) for j in js[:3]]
