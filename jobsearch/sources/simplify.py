"""SimplifyJobs curated new-grad list (public GitHub JSON). New-grad/entry-level focus - skip for senior profiles."""
import json
import urllib.request

URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"


def fetch_listings(url=URL):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def fetch_jobs():
    out = []
    for x in fetch_listings():
        if not x.get("active") or not x.get("is_visible", True):
            continue
        out.append({"title": x.get("title"), "company": x.get("company_name"), "url": x.get("url"),
                    "location": "; ".join(x.get("locations") or [])})
    return out
