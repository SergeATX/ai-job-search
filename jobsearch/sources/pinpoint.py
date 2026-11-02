"""Pinpoint HQ public postings feed (no key): https://{slug}.pinpointhq.com/postings.json"""
import json
import urllib.request


def fetch_jobs(slug):
    req = urllib.request.Request(f"https://{slug}.pinpointhq.com/postings.json", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read()
    try:
        res = json.loads(body)
    except ValueError:
        return []
    out = []
    for j in (res.get("data") or []) if isinstance(res, dict) else []:
        loc = j.get("location") or {}
        place = ", ".join(x for x in (loc.get("name") or loc.get("city"), loc.get("province")) if x)
        if j.get("workplace_type") == "remote":
            place += " (Remote)"
        out.append({"title": j.get("title"), "company": slug, "location": place,
                    "url": j.get("url"), "posted": None})
    return out
