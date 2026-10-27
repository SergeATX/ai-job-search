"""
Built In job scraper — headless-browser crawler that behaves like a normal visitor
(real user agent, renders JS, natural page-load waits) and extracts structured
job listings for a given city + category, filtered to junior/entry/internship.

Usage:
    python3 builtin_scraper.py --city austin --category dev-engineering --max-pages 3

City maps to a Built In subdomain: austin -> builtinaustin.com, dallas -> builtin.com/dallas,
houston -> builtin.com/houston (Built In's URL scheme differs by market).
"""
import argparse
import json
import sys
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

BUILTIN_ROOT = "https://builtin.com"

# austin has its own subdomain; other TX markets are path-based under builtin.com/jobs/<slug>
CITY_JOBS_URL = {
    "austin": "https://builtinaustin.com/jobs",
    "dallas": "https://builtin.com/jobs/dallas-fort-worth",
    "fort-worth": "https://builtin.com/jobs/dallas-fort-worth",  # no separate Built In market; Dallas-Fort Worth is combined
    "houston": "https://builtin.com/jobs/houston",
    "san-antonio": "https://builtin.com/jobs/san-antonio",
    "remote": "https://builtin.com/jobs/remote",
}

CITY_LINK_BASE = {
    "austin": "https://builtinaustin.com",
    "dallas": BUILTIN_ROOT,
    "fort-worth": BUILTIN_ROOT,
    "houston": BUILTIN_ROOT,
    "san-antonio": BUILTIN_ROOT,
    "remote": BUILTIN_ROOT,
}

ALLOWED_SENIORITY = {"junior", "entry level", "internship"}


def extract_jobs_from_html(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    for card in soup.select('[data-id="job-card"]'):
        company_el = card.select_one('[data-id="company-title"] span')
        title_el = card.select_one('[data-id="job-card-title"]')
        if not title_el:
            continue

        def icon_text(icon_class):
            icon = card.select_one(f"i.{icon_class}")
            if not icon:
                return None
            # Two layouts occur: icon+text share a parent span (e.g. "posted"),
            # or the icon sits alone in a wrapper div with the label in a sibling
            # span one level up (e.g. work_type/location/salary/seniority).
            direct = icon.parent.get_text(strip=True)
            if direct:
                return direct
            container = icon.find_parent("div", class_="align-items-start")
            if container:
                text = container.get_text(strip=True)
                return text or None
            return None

        posted = icon_text("fa-clock")
        work_type = icon_text("fa-house-building")
        location = icon_text("fa-location-dot")
        salary = icon_text("fa-sack-dollar")
        seniority = icon_text("fa-trophy")

        href = title_el.get("href", "")
        full_url = href if href.startswith("http") else base_url.rstrip("/") + href

        jobs.append({
            "company": company_el.get_text(strip=True) if company_el else None,
            "title": title_el.get_text(strip=True),
            "url": full_url,
            "posted": posted,
            "work_type": work_type,
            "location": location,
            "salary": salary,
            "seniority": seniority,
        })
    return jobs


def scrape(city, category, max_pages=3, headless=True, delay_seconds=2.0):
    jobs_url = CITY_JOBS_URL[city]
    link_base = CITY_LINK_BASE[city]
    all_jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(user_agent=USER_AGENT)
        for page_num in range(1, max_pages + 1):
            url = f"{jobs_url}/{category}"
            if page_num > 1:
                url += f"?page={page_num}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)  # let Alpine.js hydrate the cards
            html = page.content()
            jobs = extract_jobs_from_html(html, link_base)
            if not jobs:
                break
            all_jobs.extend(jobs)
            time.sleep(delay_seconds)  # human-like pacing between page loads
        browser.close()
    return all_jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, choices=list(CITY_JOBS_URL.keys()))
    ap.add_argument("--category", required=True,
                    help="Built In category slug, e.g. dev-engineering, data-science, it-internet-security")
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--all-seniority", action="store_true",
                    help="Don't filter to junior/entry/internship — return everything")
    args = ap.parse_args()

    jobs = scrape(args.city, args.category, max_pages=args.max_pages)

    if not args.all_seniority:
        jobs = [j for j in jobs if (j["seniority"] or "").strip().lower() in ALLOWED_SENIORITY]

    print(json.dumps(jobs, indent=2))
    print(f"\n--- {len(jobs)} job(s) matched ---", file=sys.stderr)


if __name__ == "__main__":
    main()


DEFAULT_CITIES = ["austin", "dallas", "houston", "san-antonio", "remote"]
DEFAULT_CATEGORIES = ["dev-engineering", "data-analytics"]
KEEP_SENIORITY = {"junior", "entry level"}


def fetch_jobs(cities=None, categories=None, max_pages=3):
    """Runner adapter: junior/entry-level cards for each city x category (one browser session per call)."""
    out = []
    for city in cities or DEFAULT_CITIES:
        for cat in categories or DEFAULT_CATEGORIES:
            for j in scrape(city, cat, max_pages=max_pages):
                if (j["seniority"] or "").strip().lower() in KEEP_SENIORITY:
                    out.append({"title": j["title"], "company": j["company"], "url": j["url"], "location": j["location"]})
    return out
