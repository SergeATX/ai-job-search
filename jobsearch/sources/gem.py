"""Gem (jobs.gem.com) public job board API (no key)."""
import json
import urllib.request


def fetch_jobs(slug):
    req = urllib.request.Request(f"https://api.gem.com/job_board/v0/{slug}/job_posts/", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read())
    if not isinstance(res, list):
        return []
    out = []
    for j in res:
        loc = (j.get("location") or {}).get("name") or ""
        if j.get("location_type") == "remote" and "remote" not in loc.lower():
            loc = (loc + " (Remote)").strip()
        out.append({"title": j.get("title"), "company": slug, "location": loc,
                    "url": j.get("absolute_url"), "posted": j.get("first_published_at") or j.get("created_at")})
    return out
