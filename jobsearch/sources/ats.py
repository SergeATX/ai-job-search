"""
Generic fetcher for the three most common ATS public job-board APIs:
Greenhouse, Lever, Ashby. All three are genuine public JSON APIs (no scraping,
no bot-detection) — just needs a browser-like User-Agent for Greenhouse/Ashby.

Company slugs must be guessed/discovered per-company (usually the company name,
lowercased, no spaces/punctuation) and the correct ATS confirmed with
`detect_ats()` before fetching, since a wrong guess 404s harmlessly.

Usage:
    python3 ats_api.py --company affirm --ats greenhouse --location-filter "Texas" "Austin" "Dallas" "Houston" "San Antonio" "Remote"
    python3 ats_api.py --detect affirm stripe coreweave shieldai
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{company}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{company}",
}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def detect_ats(company):
    """Try each ATS endpoint for this company slug; return the first that responds 200."""
    for ats, template in ENDPOINTS.items():
        url = template.format(company=company)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            urllib.request.urlopen(req, timeout=10)
            return ats
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
    return None


def fetch_jobs(company, ats):
    url = ENDPOINTS[ats].format(company=company)
    data = _get(url)

    jobs = []
    if ats == "greenhouse":
        for j in data.get("jobs", []):
            jobs.append({
                "title": j.get("title"),
                "location": (j.get("location") or {}).get("name"),
                "url": j.get("absolute_url"),
                "updated_at": j.get("updated_at"),
                "department": ", ".join(d.get("name", "") for d in j.get("departments", [])),
            })
    elif ats == "lever":
        for j in data:
            jobs.append({
                "title": j.get("text"),
                "location": (j.get("categories") or {}).get("location"),
                "url": j.get("hostedUrl"),
                "updated_at": j.get("createdAt"),
                "department": (j.get("categories") or {}).get("team"),
            })
    elif ats == "ashby":
        for j in data.get("jobs", []):
            jobs.append({
                "title": j.get("title"),
                "location": j.get("location"),
                "url": j.get("jobUrl") or j.get("applyUrl"),
                "updated_at": j.get("publishedAt"),
                "department": j.get("department"),
            })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--company", help="single company slug to fetch")
    group.add_argument("--detect", nargs="+", help="list of company slugs to detect ATS for (no fetch)")
    ap.add_argument("--ats", choices=list(ENDPOINTS.keys()), help="required with --company")
    ap.add_argument("--location-filter", nargs="+", default=None,
                     help="only keep jobs whose location contains any of these substrings (case-insensitive)")
    args = ap.parse_args()

    if args.detect:
        for c in args.detect:
            ats = detect_ats(c)
            print(f"{c} -> {ats}", file=sys.stderr)
        return

    if not args.ats:
        print("--ats is required with --company", file=sys.stderr)
        sys.exit(1)

    jobs = fetch_jobs(args.company, args.ats)
    if args.location_filter:
        needles = [n.lower() for n in args.location_filter]
        jobs = [j for j in jobs if j["location"] and any(n in j["location"].lower() for n in needles)]

    print(json.dumps(jobs, indent=2))
    print(f"\n--- {len(jobs)} job(s) after filtering ---", file=sys.stderr)


if __name__ == "__main__":
    main()
