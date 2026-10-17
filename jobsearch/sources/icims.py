"""
iCIMS job-board client. iCIMS is a common enterprise ATS (seen at Lennox, D.R.
Horton's older system, and many mid-size industrials) that does NOT expose a
clean JSON API like Greenhouse/Lever/Ashby/Workday — but its "noscript" iframe
URL (`?in_iframe=1`) is plain server-rendered HTML with no JS required, so a
normal HTTP GET + BeautifulSoup parse works. No Playwright needed.

Every iCIMS career site has a search/results page at:
    https://<tenant-slug>.icims.com/jobs/search?pr=<page>&in_iframe=1
<tenant-slug> must be read off the company's real careers page (it's usually
something like "globalcareers-<company>" or "<company>careers" or "careers-
<company>" — find it from a real job-posting URL, never guess).

Pagination is 20 jobs/page via the `pr` query param (0-indexed).

Usage:
    python3 icims_api.py --tenant globalcareers-lennox --search "software engineer"
    python3 icims_api.py --tenant globalcareers-lennox --max-pages 25
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
SITES_PATH = Path(__file__).resolve().parent.parent / "registry" / "icims_sites.json"


def load_sites():
    if SITES_PATH.exists():
        with open(SITES_PATH) as f:
            return json.load(f)
    return {}


def save_sites(data):
    with open(SITES_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _fetch_page(tenant, page=0):
    url = f"https://{tenant}.icims.com/jobs/search?pr={page}&in_iframe=1"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_jobs(html):
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    for row in soup.select("div.row"):
        link = row.select_one("a.iCIMS_Anchor")
        title_el = row.select_one(".col-xs-12.title h3")
        if not link or not title_el:
            continue
        loc_el = row.select_one(".col-xs-6.header.left span:last-child")
        jobs.append({
            "title": title_el.get_text(strip=True),
            "location": loc_el.get_text(strip=True) if loc_el else None,
            "url": link.get("href"),
        })
    return jobs


def _total_pages(html):
    m = re.search(r"Page\s*\d+\s*of\s*(\d+)", html)
    return int(m.group(1)) if m else 1


def fetch_all_jobs(tenant, max_pages=30):
    jobs = []
    page0_html = _fetch_page(tenant, 0)
    jobs.extend(_parse_jobs(page0_html))
    total_pages = min(_total_pages(page0_html), max_pages)
    for page in range(1, total_pages):
        time.sleep(0.5)
        html = _fetch_page(tenant, page)
        page_jobs = _parse_jobs(html)
        if not page_jobs:
            break
        jobs.extend(page_jobs)
    return jobs


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--tenant", help="saved tenant key in icims_sites.json, OR a raw slug if --save/--probe")
    ap.add_argument("--probe", action="store_true", help="treat --tenant as a new unverified slug")
    ap.add_argument("--save", action="store_true", help="with --probe: save to icims_sites.json if it works")
    ap.add_argument("--search", default=None, help="optional title keyword filter (client-side, case-insensitive)")
    ap.add_argument("--max-pages", type=int, default=30)
    args = ap.parse_args()

    tenant = args.tenant
    if not args.probe:
        sites = load_sites()
        if tenant not in sites:
            print(f"{tenant} not in icims_sites.json — use --probe first", file=sys.stderr)
            sys.exit(1)
        tenant = sites[tenant]["tenant"]

    try:
        jobs = fetch_all_jobs(tenant, max_pages=args.max_pages)
    except Exception as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        sys.exit(1)

    if args.probe and args.save and jobs:
        sites = load_sites()
        sites[args.tenant] = {"tenant": tenant}
        save_sites(sites)
        print(f"Saved {args.tenant} to icims_sites.json", file=sys.stderr)

    if args.search:
        needle = args.search.lower()
        jobs = [j for j in jobs if needle in j["title"].lower()]

    print(json.dumps(jobs, indent=2))
    print(f"\n--- {len(jobs)} job(s) ---", file=sys.stderr)


if __name__ == "__main__":
    main()
