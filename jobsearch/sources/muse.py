"""
The Muse public job API client. Unlike builtin_scraper.py this is a real documented
REST API (https://www.themuse.com/api/public/jobs) — no DOM scraping, no bot-detection
risk. Requires a browser-like User-Agent header (CloudFront blocks the default
urllib/curl UA with a 403, but doesn't otherwise rate-limit aggressively).

Confirmed-valid `category` values (exact match, case-sensitive):
    Software Engineering, Data and Analytics, Computer and IT,
    Accounting and Finance, Science and Engineering, Data Science (niche, few results)
Unconfirmed/invalid so far: Business, Security, Quality Assurance,
    Project and Product Management, Engineering (alone)

Confirmed-valid `level` values: Internship, Entry Level, Mid Level, Senior Level

Usage:
    python3 muse_api.py --category "Software Engineering" --location "Austin, TX" --level "Entry Level" "Internship"
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.parse

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE_URL = "https://www.themuse.com/api/public/jobs"


def query_page(category, location, levels, page, delay_seconds=1.5):
    params = [("category", category), ("location", location), ("page", page)]
    for lvl in levels:
        params.append(("level", lvl))
    qs = urllib.parse.urlencode(params)
    url = f"{BASE_URL}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    time.sleep(delay_seconds)  # don't hammer the API
    return data


def extract_job(item):
    desc = item
    return {
        "title": desc.get("name"),
        "company": (desc.get("company") or {}).get("name"),
        "locations": [l.get("name") for l in desc.get("locations", [])],
        "levels": [l.get("name") for l in desc.get("levels", [])],
        "categories": [c.get("name") for c in desc.get("categories", [])],
        "url": desc.get("refs", {}).get("landing_page"),
        "publication_date": desc.get("publication_date"),
    }


def search(category, location, levels, max_pages=3):
    all_jobs = []
    first = query_page(category, location, levels, 0)
    total = first.get("total", 0)
    page_count = first.get("page_count", 1)
    all_jobs.extend(extract_job(r) for r in first.get("results", []))
    for page in range(1, min(max_pages, page_count)):
        d = query_page(category, location, levels, page)
        all_jobs.extend(extract_job(r) for r in d.get("results", []))
    return all_jobs, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", required=True)
    ap.add_argument("--location", required=True, help='e.g. "Austin, TX"')
    ap.add_argument("--level", nargs="+", default=["Entry Level", "Internship"])
    ap.add_argument("--max-pages", type=int, default=2)
    args = ap.parse_args()

    jobs, total = search(args.category, args.location, args.level, max_pages=args.max_pages)
    print(json.dumps(jobs, indent=2))
    print(f"\n--- {len(jobs)} job(s) returned (API reports {total} total matching before pagination cap) ---", file=sys.stderr)


if __name__ == "__main__":
    main()
