"""
Workday public job-board API client. Workday powers most large/legacy employers'
career sites (vs. the startup-oriented Greenhouse/Lever/Ashby) — this is the piece
that lets the watchlist reach companies like RTX, Adobe, USAA, AT&T, NVIDIA, Visa,
General Motors.

Every Workday career site is backed by a POST JSON endpoint:
    https://<subdomain>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs
<subdomain> is usually "<company>.wd1" or "<company>.wd5" etc (the wdN number
varies by company/datacenter — find it from the public careers URL, not by
guessing). <tenant> and <site> also must be read off a real careers URL or found
via WebSearch ("<company> careers myworkdayjobs.com") — guessing site slugs like
"External"/"Careers" has a low hit rate; always verify with one working query
before saving a new company to workday_sites.json.

Usage:
    python3 workday_api.py --company rtx --location-filter "Texas" "Austin" "Dallas" "Houston" "San Antonio" "Remote"
    python3 workday_api.py --probe nvidia --subdomain nvidia.wd5 --tenant nvidia --site NVIDIAExternalCareerSite
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
SITES_PATH = Path(__file__).resolve().parent.parent / "registry" / "workday_sites.json"


def load_sites():
    if SITES_PATH.exists():
        with open(SITES_PATH) as f:
            return json.load(f)
    return {}


def save_sites(data):
    with open(SITES_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _post(subdomain, tenant, site, search_text="", limit=20, offset=0):
    url = f"https://{subdomain}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    body = json.dumps({"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": search_text}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def fetch_all_jobs(subdomain, tenant, site, search_text="", max_results=200):
    jobs = []
    offset = 0
    page_size = 20
    while len(jobs) < max_results:
        data = _post(subdomain, tenant, site, search_text=search_text, limit=page_size, offset=offset)
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for p in postings:
            jobs.append({
                "title": p.get("title"),
                "location": p.get("locationsText"),
                "url": f"https://{subdomain}.myworkdayjobs.com{site and '/' + site or ''}{p.get('externalPath','')}",
                "posted": p.get("postedOn"),
                "remote_type": p.get("remoteType"),
            })
        total = data.get("total", 0)
        offset += page_size
        if offset >= total:
            break
    return jobs


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--company", help="saved company key in workday_sites.json")
    group.add_argument("--probe", help="try a new company inline without saving (pass --subdomain/--tenant/--site too)")
    ap.add_argument("--subdomain", help="e.g. nvidia.wd5 (required with --probe)")
    ap.add_argument("--tenant", help="e.g. nvidia (required with --probe)")
    ap.add_argument("--site", help="e.g. NVIDIAExternalCareerSite (required with --probe)")
    ap.add_argument("--save", action="store_true", help="with --probe: save to workday_sites.json if it works")
    ap.add_argument("--search-text", default="", help="Workday's own search box text, e.g. 'software engineer'")
    ap.add_argument("--location-filter", nargs="+", default=None)
    ap.add_argument("--max-results", type=int, default=200)
    args = ap.parse_args()

    if args.company:
        sites = load_sites()
        if args.company not in sites:
            print(f"{args.company} not in workday_sites.json — use --probe first", file=sys.stderr)
            sys.exit(1)
        cfg = sites[args.company]
        subdomain, tenant, site = cfg["subdomain"], cfg["tenant"], cfg["site"]
    else:
        if not (args.subdomain and args.tenant and args.site):
            print("--probe requires --subdomain --tenant --site", file=sys.stderr)
            sys.exit(1)
        subdomain, tenant, site = args.subdomain, args.tenant, args.site

    try:
        jobs = fetch_all_jobs(subdomain, tenant, site, search_text=args.search_text, max_results=args.max_results)
    except Exception as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.probe and args.save:
        sites = load_sites()
        sites[args.probe] = {"subdomain": subdomain, "tenant": tenant, "site": site}
        save_sites(sites)
        print(f"Saved {args.probe} to workday_sites.json", file=sys.stderr)

    if args.location_filter:
        needles = [n.lower() for n in args.location_filter]
        jobs = [j for j in jobs if j["location"] and any(n in j["location"].lower() for n in needles)]

    print(json.dumps(jobs, indent=2))
    print(f"\n--- {len(jobs)} job(s) after filtering ---", file=sys.stderr)


if __name__ == "__main__":
    main()
