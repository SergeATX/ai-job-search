"""IBM's own careers site (careers.ibm.com), US jobs, title + city only (#125). slug = "careers.ibm.com".

IBM's job pages sit behind a bot check, so the only read is the public search service the careers page itself calls:
POST https://www-api.ibm.com/search/api/v2 (no robots.txt for that host; www.ibm.com/robots.txt doesn't cover it).
It answers each job's title, posting date, link (careers.ibm.com/careers/JobDetail?jobId=N), a ~250-character snippet
of the description, and its cities (no state). The States are added here for the cities IBM has in the US. About 480
US jobs: 5 requests a page of 100, one second apart. A job in several cities lists them all (field_keyword_21)."""
import json
import sys
import time
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
API = "https://www-api.ibm.com/search/api/v2"
PAGE, GAP, MAX_JOBS = 100, 1.0, 3000
FIELDS = ["url", "dcdate", "title", "description", "field_keyword_19", "field_keyword_21"]
STATE = {  # IBM's US cities -> state; a city missing here is listed without one
    "Albany": "NY", "Armonk": "NY", "Austin": "TX", "Baton Rouge": "LA", "Boise": "ID", "Bentonville": "AR",
    "Bethesda": "MD", "Buffalo": "NY", "Burlingame": "CA", "Columbia": "MD", "Cambridge": "MA", "Chantilly": "VA",
    "Chicago": "IL", "Columbus": "OH", "Durham": "NC", "Dallas": "TX", "Denver": "CO", "Detroit": "MI",
    "Herndon": "VA", "Houston": "TX", "Kansas City": "MO", "Lowell": "MA", "Lansing": "MI", "Monroe": "LA",
    "Malta": "NY", "New York": "NY", "Poughkeepsie": "NY", "Plano": "TX", "Research Triangle Park": "NC",
    "Rochester": "MN", "Raleigh": "NC", "Rocket Center": "WV", "San Francisco": "CA", "San Jose": "CA",
    "Tucson": "AZ", "University Park": "TX", "Washington": "DC", "Yorktown Heights": "NY", "Charlotte": "NC",
    "Irvine": "CA", "Bellevue": "WA", "Atlanta": "GA", "Hampton": "VA", "Annapolis Junction": "MD",
    "Alexandria": "VA", "Reston": "VA", "McLean": "VA", "Catonsville": "MD", "Frederick": "MD", "Ashburn": "VA",
    "San Antonio": "TX", "Fort Worth": "TX", "Irving": "TX", "Frisco": "TX", "Richardson": "TX", "Round Rock": "TX",
    "Boulder": "CO", "Boston": "MA", "Seattle": "WA", "Los Angeles": "CA", "Minneapolis": "MN", "Philadelphia": "PA",
    "Pittsburgh": "PA", "Phoenix": "AZ", "Miami": "FL", "Tampa": "FL", "Orlando": "FL", "Cary": "NC",
    "Endicott": "NY", "Southbury": "CT", "Stamford": "CT", "Hartford": "CT", "Edison": "NJ", "Piscataway": "NJ",
    "Sacramento": "CA", "San Diego": "CA", "Salt Lake City": "UT", "Nashville": "TN", "Indianapolis": "IN",
}


def _post(body):
    req = urllib.request.Request(API, json.dumps(body).encode(), {
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA,
        "Origin": "https://www.ibm.com", "Referer": "https://www.ibm.com/"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())["hits"]


def _city(c):
    c = " ".join((c or "").replace(", US", "").split())
    c = c.title() if c.isupper() else c
    return None if not c or c.lower() in ("no city", "multiple cities") else c


def _location(s):
    cities = [c for c in map(_city, s.get("field_keyword_21") or [s.get("field_keyword_19")]) if c]
    places = [f"{c}, {STATE[c]}" if c in STATE else c for c in dict.fromkeys(cities)]
    return "; ".join(places) or "United States"


def _job(s):
    return {"title": s.get("title"), "company": "IBM", "location": _location(s), "url": s.get("url"),
            "posted": s.get("dcdate"), "description": s.get("description")}


def fetch_jobs(slug="careers.ibm.com"):
    out, frm = {}, 0
    while frm < MAX_JOBS:
        hits = _post({"appId": "careers", "scopes": ["careers2"], "size": PAGE, "from": frm, "lang": "zz",
                      "query": {"bool": {"must": [{"term": {"field_keyword_05": "United States"}}]}},
                      "sort": [{"dcdate": "desc"}], "_source": FIELDS})
        rows = hits["hits"]
        for h in rows:
            s = h["_source"]
            if s.get("url") and s.get("title"):
                out.setdefault(s["url"], _job(s))
        frm += PAGE
        if len(rows) < PAGE or frm >= hits["total"]["value"]:
            break
        time.sleep(GAP)
    return list(out.values())


if __name__ == "__main__":
    jobs = fetch_jobs()
    print(len(jobs), file=sys.stderr)
    print(json.dumps(jobs[:3], indent=1))
