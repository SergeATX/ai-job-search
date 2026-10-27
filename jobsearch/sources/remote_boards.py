"""Public JSON APIs of remote-job boards (no key needed): RemoteOK, Remotive, Jobicy.
Each fetcher returns [{title, company, url, location}] and keeps only roles open to US-based candidates;
the profile's title/location filters and the fit-check do the rest. Quality is mixed - check `jobsearch yield`."""
import json
import re
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
US_OK = re.compile(r"\b(usa?|united states|americas?|north america|worldwide|anywhere|global)\b", re.I)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _loc(geo):
    geo = geo if isinstance(geo, str) else ", ".join(geo or [])
    return "Remote - US" if (not geo or US_OK.search(geo)) else None


def remoteok():
    out = []
    for x in _get("https://remoteok.com/api")[1:]:
        loc = _loc(x.get("location"))
        if loc and x.get("url") and x.get("position"):
            out.append({"title": x["position"], "company": x.get("company"), "url": x["url"], "location": loc})
    return out


def remotive(categories=("software-dev", "data")):
    out = []
    for cat in categories:
        for x in _get(f"https://remotive.com/api/remote-jobs?category={cat}&limit=200").get("jobs", []):
            loc = _loc(x.get("candidate_required_location"))
            if loc and x.get("url"):
                out.append({"title": x["title"], "company": x.get("company_name"), "url": x["url"], "location": loc})
    return out


def jobicy(industries=("dev", "data-science"), count=100):
    out = []
    for ind in industries:
        for x in _get(f"https://jobicy.com/api/v2/remote-jobs?count={count}&geo=usa&industry={ind}").get("jobs", []):
            level = x.get("jobLevel")
            level = " ".join(level) if isinstance(level, list) else (level or "")
            if re.search(r"senior|midweight", level, re.I) and not re.search(r"junior|any", level, re.I):
                continue
            if x.get("url"):
                out.append({"title": x["jobTitle"], "company": x.get("companyName"), "url": x["url"], "location": "Remote - US"})
    return out


def fetch_jobs(boards=("remoteok", "remotive", "jobicy")):
    out = []
    for b in boards:
        try:
            out += globals()[b]()
        except Exception:
            continue  # one flaky board must not lose the others
    return out
