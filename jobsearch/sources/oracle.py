"""Oracle Recruiting Cloud (HCM) Candidate Experience public REST API (no key)."""
import json
import urllib.parse
import urllib.request


def fetch_jobs(host, site, keyword="", max_jobs=600):
    out, offset, page = [], 0, 50
    while offset < max_jobs:
        finder = f"findReqs;siteNumber={site},limit={page},offset={offset},sortBy=POSTING_DATES_DESC"
        if keyword:
            finder += ",keyword=" + urllib.parse.quote(keyword)
        url = (f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
               f"&expand=requisitionList.secondaryLocations&finder={finder}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            items = json.loads(r.read()).get("items") or [{}]
        reqs = items[0].get("requisitionList") or []
        for j in reqs:
            out.append({"title": j.get("Title"), "location": j.get("PrimaryLocation"),
                        "url": f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{j.get('Id')}"})
        offset += page
        if len(reqs) < page or offset >= items[0].get("TotalJobsCount", 0):
            break
    return out
