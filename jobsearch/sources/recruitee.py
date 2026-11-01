"""Recruitee public offers API (no key)."""
import json
import urllib.request


def fetch_jobs(sub):
    req = urllib.request.Request(f"https://{sub}.recruitee.com/api/offers/", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        offers = json.loads(r.read()).get("offers", [])
    out = []
    for j in offers:
        if j.get("status") not in (None, "published"):
            continue
        place = j.get("location") or ", ".join(x for x in (j.get("city"), j.get("country")) if x)
        if j.get("remote"):
            place += " (Remote)"
        out.append({"title": j.get("title"), "company": j.get("company_name"), "location": place,
                    "url": j.get("careers_url") or f"https://{sub}.recruitee.com/o/{j.get('slug')}", "posted": j.get("published_at")})
    return out
