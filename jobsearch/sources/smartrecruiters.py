"""SmartRecruiters public posting API (no key)."""
import json
import urllib.request


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def fetch_jobs(company, max_jobs=1000):
    out, offset = [], 0
    while offset < max_jobs:
        d = _get(f"https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100&offset={offset}")
        items = d.get("content", [])
        for j in items:
            loc = j.get("location") or {}
            place = ", ".join(x for x in (loc.get("city"), (loc.get("region") or "").upper() or None, loc.get("country", "").upper() or None) if x)
            if loc.get("remote"):
                place += " (Remote)"
            out.append({"title": j.get("name"), "location": place,
                        "url": f"https://jobs.smartrecruiters.com/{company}/{j.get('id')}"})
        offset += 100
        if offset >= d.get("totalFound", 0) or not items:
            break
    return out
