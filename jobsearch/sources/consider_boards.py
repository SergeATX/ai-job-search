"""Consider-powered VC boards (Sequoia, GV, LSVP, BCV, ...): GET homepage for CSRF token + board id, then POST /api-boards/search-jobs
(paged via meta.sequence cursor; the API has no server-side keyword/location filter, so we page the whole board ~100/req and filter
client-side to TX / remote-US and junior-ish seniority). urllib only. Boards overlap heavily (same portfolio companies) -> dedup by url."""
import http.cookiejar, json, re, sys, time, urllib.request
UA = "Mozilla/5.0"
BOARDS = ["jobs.sequoiacap.com", "jobs.gv.com", "jobs.lsvp.com", "jobs.bcv.com", "jobs.firstround.com", "jobs.felicis.com",
          "jobs.battery.com", "jobs.bvp.com", "jobs.usv.com"]
TX = re.compile(r"\b(austin|dallas|houston|san antonio|texas|plano|irving|frisco|fort worth|richardson|round rock|the woodlands)\b|,\s*TX\b", re.I)
NONUS = re.compile(r"\b(canada|uk|united kingdom|london|india|germany|berlin|europe|emea|apac|brazil|mexico|australia|singapore|israel|ireland|france|paris|toronto)\b", re.I)
SENIOR_IDS = {"senior", "manager", "director", "vp", "executive", "c_level", "head", "lead", "principal", "staff"}

def _board(dom, max_pages, delay):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    h = op.open(urllib.request.Request("https://" + dom, headers={"User-Agent": UA}), timeout=20).read().decode()
    tok = re.search(r'csrfToken":"([^"]*)', h).group(1); board = json.loads(re.search(r'"board":(\{[^}]*\})', h).group(1))
    jobs, seq = [], None
    for _ in range(max_pages):
        meta = {"size": 100}
        if seq: meta["sequence"] = seq
        body = json.dumps({"meta": meta, "board": board, "query": {"promoteFeatured": True}}).encode()
        d = json.load(op.open(urllib.request.Request(f"https://{dom}/api-boards/search-jobs", body, {"content-type": "application/json", "csrf-token": tok, "User-Agent": UA}), timeout=40))
        jobs += d["jobs"]; seq = d["meta"].get("sequence")
        if not d["jobs"] or not seq or len(jobs) >= d["total"]: break
        time.sleep(delay)
    return jobs

def fetch_jobs(boards=BOARDS, max_pages=200, delay=0.4):
    out, seen = [], set()
    for dom in boards:
        try: js = _board(dom, max_pages, delay)
        except Exception as e:
            print(f"consider {dom}: {e}", file=sys.stderr); continue
        for j in js:
            u = j.get("applyUrl") or j.get("url")
            if not u or u in seen: continue
            locs = j.get("locations") or []
            loc = "; ".join(locs)
            ids = set(j.get("jobSeniorityIds") or [])
            if ids & SENIOR_IDS and "junior" not in ids: continue
            us_remote = j.get("remote") and not (NONUS.search(loc) and not re.search(r"United States|\bUS\b|USA", loc))
            if not (TX.search(loc) or us_remote): continue
            seen.add(u)
            out.append({"title": j.get("title"), "company": j.get("companyName"), "location": loc + (" (Remote)" if j.get("remote") else ""),
                        "url": u, "posted": j.get("timeStamp"), "level": "junior" if "junior" in ids else "", "board": dom})
    return out

if __name__ == "__main__":
    r = fetch_jobs(BOARDS[:2], max_pages=30)
    assert r and all(x["url"] and x["title"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
