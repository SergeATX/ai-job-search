"""Rippling ATS public board API (no key)."""
import json
import urllib.request


def fetch_jobs(slug, max_pages=20):
    out = []
    for page in range(max_pages):
        req = urllib.request.Request(f"https://ats.rippling.com/api/v2/board/{slug}/jobs?page={page}&pageSize=50",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())
        for j in d.get("items", []):
            locs = j.get("locations") or [{}]
            place = "; ".join(l.get("name") or "" for l in locs if l)
            if any(l.get("workplaceType") == "REMOTE" for l in locs if l):
                place += " (Remote)"
            out.append({"title": j.get("name"), "location": place, "url": j.get("url")})
        if page + 1 >= (d.get("totalPages") or 1):
            break
    return out
