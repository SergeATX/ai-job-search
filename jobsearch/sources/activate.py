"""Activate career sites (the "Activate" platform: jobs.mdanderson.org), urllib only. slug = the site's host.

- /jobs-site.xml (the sitemap) lists every open job's page in one request.
- The search page loads its results from /search/searchresultslist?page=N: JSON {"jobsHtml", "paginationHtml"}, 12 job
  cards a page (title, "City, ST", link) and "Showing 1-12 of 418". The order isn't stable between requests (ties), so
  paging misses about one job in ten; those are read from their own pages.
- Each job page carries JobPosting data (written type="application/ld&#x2B;json") with the date ("11/6/2026") and the
  description; the catalog's backfill reads it for the jobs the cards gave.
Job links are the sitemap's (what a card's link redirects to), so a job keeps one URL whichever way it was read.
"""
import html as H
import json
import re
import sys
import time

from . import get_text

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
CARD = re.compile(r'<li class="job-item"[^>]*>(.*?)</li>', re.S)
TOTAL = re.compile(r"Showing\s+[\d,]+\s*-\s*[\d,]+\s+of\s+([\d,]+)")
LOC = re.compile(r"<loc>\s*(https?://[^<\s]+/search/jobdetails/[^<\s]+)\s*</loc>")
GUID = re.compile(r"/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/?$", re.I)
LD = re.compile(r'<script[^>]*application/ld(?:\+|&#x2B;|&#43;)json[^>]*>(.*?)</script>', re.S | re.I)
PAUSE = 0.5  # seconds between requests: one site, read one page at a time
MAX_DETAILS = 200  # job pages read for jobs the cards missed


def _strip(x):
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", x or "")).split())


def _guid(url):
    m = GUID.search(url)
    return m[1].lower() if m else url


def mdy(v):
    """'11/6/2026' -> '2026-11-06'; other forms pass through."""
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", v or "")
    return f"{m[3]}-{int(m[1]):02d}-{int(m[2]):02d}" if m else v


def parse(host, d):
    """One searchresultslist answer -> (jobs, total listed or None)."""
    out = []
    for card in CARD.findall(d.get("jobsHtml") or ""):
        href = re.search(r'href="(/search/jobdetails/[^"]+)"', card)
        title = re.search(r'class="job-title"[^>]*>(.*?)</h\d>', card, re.S)
        place = re.search(r"<dt>\s*City, State\s*</dt>\s*<dd>(.*?)</dd>", card, re.S)
        if not (href and title):
            continue
        places = [_strip(p) for p in re.findall(r"<span[^>]*>(.*?)</span>", place[1], re.S)] if place else []
        out.append({"title": _strip(title[1]), "company": host, "location": "; ".join(p for p in places if p) or _strip(place and place[1]),
                    "url": f"https://{host}{H.unescape(href[1])}", "posted": None})
    m = TOTAL.search(d.get("paginationHtml") or "")
    return out, int(m[1].replace(",", "")) if m else None


def parse_job_page(host, url, page):
    """A job page's JobPosting data -> a job dict, or None."""
    for block in LD.findall(page):
        try:
            d = json.loads(block)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("@type") != "JobPosting" or not d.get("title"):
            continue
        places = []
        for p in d.get("jobLocation") or []:
            a = (p or {}).get("address") or {}
            places.append(", ".join(x for x in (a.get("addressLocality"), a.get("addressRegion")) if x))
        return {"title": _strip(d["title"]), "company": host, "location": "; ".join(p for p in places if p), "url": url,
                "posted": mdy(d.get("datePosted")), "description_html": d.get("description")}
    return None


def fetch_jobs(host, max_jobs=3000):
    get = lambda url, accept: get_text(url, {"User-Agent": UA, "Accept": accept}, timeout=30)
    try:
        listed = {_guid(u): H.unescape(u) for u in LOC.findall(get(f"https://{host}/jobs-site.xml", "application/xml"))}
    except Exception:  # no sitemap: the cards alone
        listed = {}
    found, page, total, per_page = {}, 1, None, None
    while len(found) < max_jobs:
        time.sleep(PAUSE if page > 1 else 0)
        url = f"https://{host}/search/searchresultslist" + (f"?page={page}" if page > 1 else "")
        jobs, total = parse(host, json.loads(get(url, "application/json")))
        if not jobs:
            break
        for j in jobs:
            g = _guid(j["url"])
            j["url"] = listed.get(g, j["url"])
            found.setdefault(g, j)
        per_page = per_page or len(jobs)
        if total is None or page * per_page >= total:  # the last page
            break
        page += 1
    missed = [g for g in listed if g not in found][:MAX_DETAILS]
    for g in missed:
        time.sleep(PAUSE)
        try:
            j = parse_job_page(host, listed[g], get(listed[g], "text/html"))
        except Exception:
            j = None  # gone since the sitemap was made, or one bad page: the next scan reads it
        if j:
            found[g] = j
    return list(found.values())[:max_jobs]


if __name__ == "__main__":
    for s in sys.argv[1:] or ["jobs.mdanderson.org"]:
        js = fetch_jobs(s)
        print(s, len(js))
        for j in js[:3]:
            print(j)
