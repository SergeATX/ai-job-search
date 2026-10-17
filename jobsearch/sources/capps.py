"""
CAPPS Careers (Texas state-agency jobs) scraper — headless-browser crawler against
the PeopleSoft candidate portal. No login required to browse, no bot-detection wall
encountered (unlike WorkInTexas, which is Incapsula-protected and was abandoned).

Note: PeopleSoft's job detail pages are session-based, not stable bookmarkable URLs,
so there is no direct "apply" link per job — only a Job ID Number, which a human
looks up directly on the portal's search box.

Usage:
    python3 capps_scraper.py --keyword "software engineer"
"""
import argparse
import json
import sys
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
PORTAL_URL = (
    "https://erphcmprd.cpa.texas.gov/psc/candidateportal/EMPLOYEE/HRMS/c/"
    "HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?FOCUS=Applicant"
)
SEARCH_BOX_ID = "HRS_SCH_WRK_HRS_SCH_TEXT100"

FIELD_LABELS = {
    "Job Title": "title",
    "Job ID Number": "job_id",
    "Company": "company",
    "Location": "location",
    "Department": "department",
    "Schedule": "schedule",
    "Min Annual Rate": "min_annual_rate",
    "Max Annual Rate": "max_annual_rate",
    "Posted Date": "posted_date",
    "Close Date": "close_date",
}


def extract_jobs_from_html(html):
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    for row in soup.select("li.ps_grid-row"):
        job = {}
        for box in row.select(".ps_box-edit"):
            label_el = box.select_one(".ps-label")
            value_el = box.select_one(".ps_box-value")
            if not label_el or not value_el:
                continue
            label = label_el.get_text(strip=True)
            key = FIELD_LABELS.get(label)
            if key:
                job[key] = value_el.get_text(strip=True)
        if job.get("title"):
            jobs.append(job)
    return jobs


def search(keyword, headless=True, wait_ms=4000):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        box = page.locator(f"#{SEARCH_BOX_ID}")
        box.fill(keyword)
        box.press("Enter")
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
    return extract_jobs_from_html(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True)
    args = ap.parse_args()

    jobs = search(args.keyword)
    print(json.dumps(jobs, indent=2))
    print(f"\n--- {len(jobs)} job(s) returned (page 1 only — PeopleSoft caps at ~50-100/page, no pagination wired up yet) ---", file=sys.stderr)


if __name__ == "__main__":
    main()
