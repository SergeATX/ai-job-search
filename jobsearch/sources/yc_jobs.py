"""YC Work at a Startup jobs via ycombinator.com/jobs SSR pages (public, no login). The page embeds Inertia `data-page` JSON with
jobPostings (~30/page, no pagination): title, url, location, minExperience ("Any (new grads ok)", "1+ years", ...), visa, type.
We slice role x location (Austin/Dallas/Houston/San Antonio/Remote) and keep jobs whose minExperience <= 2 years or "new grads ok"."""
import html, json, re, sys, time, urllib.request
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE = "https://www.ycombinator.com"
ROLES = ["software-engineer", "science"]
LOCS = ["austin", "dallas", "houston", "san-antonio", "remote"]
EASY = re.compile(r"^(any|0|1\+|2\+|new)", re.I)

def _page(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    try:
        t = urllib.request.urlopen(req, timeout=30).read().decode()
    except Exception as e:
        print(f"yc {path}: {e}", file=sys.stderr); return []
    m = re.search(r'data-page="([^"]*)"', t)
    return json.loads(html.unescape(m.group(1)))["props"].get("jobPostings", []) if m else []

def fetch_jobs(roles=ROLES, locs=LOCS, entry_only=True, delay=0.8):
    out, seen = [], set()
    slices = [f"/jobs/role/{r}/{l}" for r in roles for l in locs]
    for s in slices:
        for j in _page(s):
            u = BASE + j["url"]
            if u in seen: continue
            exp = j.get("minExperience") or ""
            if entry_only and not EASY.match(exp): continue
            seen.add(u)
            out.append({"title": j["title"], "company": j.get("companyName"), "location": j.get("location"), "url": u,
                        "posted": None, "level": f"{exp} {j.get('type') or ''}".strip(), "visa": j.get("visa")})
        time.sleep(delay)
    return out

if __name__ == "__main__":
    r = fetch_jobs()
    assert r and all(x["url"] and x["title"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
