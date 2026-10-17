"""Workable public careers API (no key)."""
import json
import urllib.request


def fetch_jobs(account, max_pages=20):
    out, token = [], None
    for _ in range(max_pages):
        body = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
        if token:
            body["token"] = token
        req = urllib.request.Request(f"https://apply.workable.com/api/v3/accounts/{account}/jobs",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
        for j in d.get("results", []):
            loc = j.get("location") or {}
            place = ", ".join(x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x)
            if j.get("remote") or j.get("workplace") == "remote":
                place += " (Remote)"
            out.append({"title": j.get("title"), "location": place,
                        "url": f"https://apply.workable.com/{account}/j/{j.get('shortcode')}/"})
        token = d.get("nextPage")
        if not token:
            break
    return out
