"""Wellfound (ex-AngelList) public SEO pages: /location/<city> and /role/l/<role>/<city> SSR a Next.js __NEXT_DATA__ with Apollo
JobListingSearchResult objects (~30-45 curated jobs per page; the full search is GraphQL behind Cloudflare/DataDome and not usable).
Needs a desktop Chrome UA. Job page: https://wellfound.com/jobs/<id>-<slug> (apply goes via Wellfound).  urllib only."""
import json, re, sys, time, urllib.request
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
CITIES = ["austin", "dallas", "houston", "san-antonio", "texas"]
ROLES = ["software-engineer", "data-engineer", "data-scientist", "data-analyst", "machine-learning-engineer", "full-stack-developer",
         "backend-developer", "frontend-developer"]
SENIOR = re.compile(r"\b(senior|sr\.?|staff|principal|lead|director|head|manager|vp|architect)\b", re.I)

def _slices():
    for c in CITIES: yield f"/location/{c}"
    for r in ROLES:
        for c in ("austin", "dallas", "houston", "remote"): yield f"/role/l/{r}/{c}"

def _page(path):
    try:
        t = urllib.request.urlopen(urllib.request.Request("https://wellfound.com" + path, headers={"User-Agent": UA}), timeout=30).read().decode()
        m = re.search(r"__NEXT_DATA__[^>]*>(.*?)</script>", t, re.S)
        a = json.loads(m.group(1))["props"]["pageProps"].get("apolloState") or {}
        return a.get("data", a)
    except Exception as e:
        print(f"wellfound {path}: {e}", file=sys.stderr); return {}

def fetch_jobs(entry_only=True, delay=1.2, slices=None):
    out, seen = [], set()
    for s in (slices or list(_slices())):
        a = _page(s)
        company = {}
        for v in a.values():
            if isinstance(v, dict) and v.get("__typename") == "StartupResult":
                for r in v.get("highlightedJobListings") or []:
                    company[r["__ref"].split(":")[1]] = v.get("name")
        for k, v in a.items():
            if not k.startswith("JobListingSearchResult:"): continue
            jid = v.get("id")
            if jid in seen: continue
            ymin = v.get("yearsExperienceMin")
            title = v.get("title") or ""
            if entry_only and ((ymin is not None and ymin > 2) or SENIOR.search(title)): continue
            seen.add(jid)
            loc = "; ".join(v.get("locationNames") or []) + (" Remote" if v.get("remote") else "")
            if v.get("acceptedRemoteLocationNames"): loc += " (" + ", ".join(v["acceptedRemoteLocationNames"]) + ")"
            out.append({"title": title, "company": company.get(jid), "location": loc,
                        "url": f"https://wellfound.com/jobs/{jid}-{v.get('slug')}", "posted": v.get("liveStartAt"),
                        "level": "" if ymin is None else f"{ymin}+ years", "ats": v.get("atsSource")})
        time.sleep(delay)
    return out

if __name__ == "__main__":
    r = fetch_jobs()
    assert r and all(x["url"] and x["title"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
