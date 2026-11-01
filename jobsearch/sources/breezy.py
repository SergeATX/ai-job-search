"""Breezy HR public company feed (no key)."""
import json
import urllib.request


def fetch_jobs(sub):
    req = urllib.request.Request(f"https://{sub}.breezy.hr/json", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read())
    if not isinstance(res, list):
        return []  # unknown subdomain serves an HTML page, not a feed
    out = []
    for j in res:
        loc = j.get("location") or {}
        place = loc.get("name") or ""
        if loc.get("is_remote"):
            place += " (Remote)"
        out.append({"title": j.get("name"), "company": (j.get("company") or {}).get("name"), "location": place,
                    "url": j.get("url"), "posted": j.get("published_date")})
    return out
