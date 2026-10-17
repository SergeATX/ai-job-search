"""
Jibe job-board client. Jibe is a recruitment-marketing "career site" product
(acquired by iCIMS in 2018) that many large enterprises run as a branded
front-end IN FRONT OF their real ATS backend (often classic iCIMS, sometimes
something else) — distinct from the plain iCIMS iframe `icims_api.py` handles.
Identify a Jibe site by script tags referencing `jibecdn.com` / `jibeapply.com`
on the company's careers page (view-source or a Playwright network capture).

Every Jibe career site exposes a clean JSON REST endpoint:
    https://<careers-domain>/api/jobs?page=<n>&sortBy=relevance&descending=false&internal=false
<careers-domain> must be read off the company's real careers site (e.g.
careers.heb.com) — find it from the company's own site, never guess.

Pagination: 10 jobs/page via `page` (1-indexed), `totalCount` in the response
gives the total. Free-text `q=` does NOT reliably filter server-side (seen at
H-E-B — totalCount stayed constant regardless of query) — instead, filter by
the `tags2` facet (category), whose valid values are listed under
`filter.facetList.tags2` in any response. Category names are company-specific
and must be read off a real response, not assumed (e.g. H-E-B uses "Digital
Software Engineering", "Digital Data Engineering" — a different company's
Jibe site will have its own category taxonomy).

Usage:
    python3 jibe_api.py --domain careers.heb.com --list-categories
    python3 jibe_api.py --domain careers.heb.com --category "Digital Software Engineering"
    python3 jibe_api.py --domain careers.heb.com --probe --save heb
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
SITES_PATH = Path(__file__).resolve().parent.parent / "registry" / "jibe_sites.json"


def load_sites():
    if SITES_PATH.exists():
        with open(SITES_PATH) as f:
            return json.load(f)
    return {}


def save_sites(data):
    with open(SITES_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _fetch_page(domain, page=1, category=None):
    params = {"page": page, "sortBy": "relevance", "descending": "false", "internal": "false"}
    if category:
        params["tags2"] = category
    url = f"https://{domain}/api/jobs?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def list_categories(domain):
    data = _fetch_page(domain, page=1)
    facets = data.get("filter", {}).get("facetList", {}).get("tags2", [])
    return [(f["term"], f["count"]) for f in facets]


def fetch_jobs(domain, category=None, max_pages=10):
    jobs = []
    page = 1
    while page <= max_pages:
        data = _fetch_page(domain, page=page, category=category)
        page_jobs = data.get("jobs", [])
        if not page_jobs:
            break
        for j in page_jobs:
            d = j["data"]
            jobs.append({
                "title": d.get("title"),
                "city": d.get("city"),
                "state": d.get("state"),
                "url": d.get("apply_url"),
                "posted": d.get("posted_date"),
                "category": d.get("tags2"),
            })
        total = data.get("totalCount", 0)
        if page * 10 >= total:
            break
        page += 1
        time.sleep(0.3)
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", required=True, help="careers domain, e.g. careers.heb.com")
    ap.add_argument("--list-categories", action="store_true")
    ap.add_argument("--category", help="tags2 facet value, e.g. 'Digital Software Engineering'")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--save", help="with --probe: save under this key in jibe_sites.json")
    ap.add_argument("--max-pages", type=int, default=10)
    args = ap.parse_args()

    if args.list_categories:
        try:
            cats = list_categories(args.domain)
        except Exception as e:
            print(f"Fetch failed: {e}", file=sys.stderr)
            sys.exit(1)
        for term, count in sorted(cats, key=lambda x: -x[1]):
            print(f"{count:5d}  {term}")
        return

    try:
        jobs = fetch_jobs(args.domain, category=args.category, max_pages=args.max_pages)
    except Exception as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.probe and args.save and jobs:
        sites = load_sites()
        sites[args.save] = {"domain": args.domain}
        save_sites(sites)
        print(f"Saved {args.save} to jibe_sites.json", file=sys.stderr)

    print(json.dumps(jobs, indent=2))
    print(f"\n--- {len(jobs)} job(s) ---", file=sys.stderr)


if __name__ == "__main__":
    main()
