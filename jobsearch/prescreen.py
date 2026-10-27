"""Cheap, deterministic pre-screen: fetch each candidate's posting text and apply the profile's mechanical gates
(explicit years of experience, required clearance, required graduate degree). Survivors go to the LLM fit-check with the
posting text already on disk, so the agent neither re-fetches nor reads the obvious rejects."""
import html
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/html"}
TAG = re.compile(r"<[^>]+>")


def _get(url, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf8", "ignore")


def _text(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h or "")
    h = re.sub(r"(?i)<(br|/p|/li|/div|/h\d)[^>]*>", "\n", h)
    return re.sub(r"[ \t\r\f\v]+", " ", html.unescape(TAG.sub(" ", h))).strip()


_ashby = {}


def fetch_text(url):
    u = url.split("#")[0]
    m = re.match(r"https?://(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/([^/]+)/jobs/(\d+)", u)
    if m:
        return _text(json.loads(_get(f"https://boards-api.greenhouse.io/v1/boards/{m[1]}/jobs/{m[2]}"))["content"])
    m = re.match(r"https?://jobs\.(?:eu\.)?lever\.co/([^/]+)/([0-9a-f-]+)", u)
    if m:
        d = json.loads(_get(f"https://api.lever.co/v0/postings/{m[1]}/{m[2]}"))
        return d.get("descriptionPlain", "") + "\n" + "\n".join(
            f"{l.get('text')}: {_text(l.get('content'))}" for l in d.get("lists", []))
    m = re.match(r"https?://jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]+)", u)
    if m:
        if m[1] not in _ashby:
            _ashby[m[1]] = {j["id"]: j for j in json.loads(_get(f"https://api.ashbyhq.com/posting-api/job-board/{m[1]}")).get("jobs", [])}
        j = _ashby[m[1]].get(m[2]) or {}
        return j.get("descriptionPlain") or _text(j.get("descriptionHtml"))
    m = re.match(r"https?://([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/]+)(/job/.*)", u)
    if m:
        d = json.loads(_get(f"https://{m[1]}.{m[2]}.myworkdayjobs.com/wday/cxs/{m[1]}/{m[3]}{m[4]}"))
        return _text(d["jobPostingInfo"].get("jobDescription"))
    m = re.match(r"https?://jobs\.smartrecruiters\.com/([^/]+)/(\d+)", u)
    if m:
        d = json.loads(_get(f"https://api.smartrecruiters.com/v1/companies/{m[1]}/postings/{m[2]}"))
        return "\n".join(_text(s.get("text")) for s in (d.get("jobAd", {}).get("sections") or {}).values())
    m = re.match(r"https?://apply\.workable\.com/([^/]+)/j/([A-Z0-9]+)", u)
    if m:
        d = json.loads(_get(f"https://apply.workable.com/api/v2/accounts/{m[1]}/jobs/{m[2]}"))
        return _text(d.get("description")) + "\n" + _text(d.get("requirements"))
    m = re.match(r"https?://([a-z0-9.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[a-zA-Z_-]+/sites/([A-Za-z0-9_]+)/job/(\d+)", u)
    if m:
        d = json.loads(_get(f"https://{m[1]}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true"
                            f"&finder=ById;Id=%22{m[3]}%22,siteNumber={m[2]}"))
        it = (d.get("items") or [{}])[0]
        return _text(" ".join(str(it.get(k) or "") for k in ("ExternalDescriptionStr", "ExternalQualificationsStr", "ExternalResponsibilitiesStr")))
    return _text(_get(u))  # generic fallback: plain HTML


# ---- gates -----------------------------------------------------------------------------------------------------------
YEARS = re.compile(r"(?:minimum|at least|min\.?|requires?|required|with|of)?\s*(\d{1,2})\s*(?:\+|plus)?\s*(?:(?:-|to|–)\s*(\d{1,2}))?\s*\+?\s*"
                   r"(?:years?|yrs?)\b(?:\s+of)?[\w ,/&()'-]{0,70}?\b(?:experience|exp\b|background|working|developing|building)", re.I)
YEARS2 = re.compile(r"experience[^.\n]{0,60}?(\d{1,2})\s*\+?\s*(?:years?|yrs?)", re.I)
SOFT = re.compile(r"preferred|a plus|nice to have|bonus|desired|or equivalent|or related|in lieu|ideal|helpful", re.I)
CLEAR = re.compile(r"(?:active|current|existing)\s+(?:u\.?s\.?\s+)?(?:top secret|secret|ts/sci|ts\b|dod)[^.\n]{0,30}|"
                   r"must (?:have|hold|possess|maintain)[^.\n]{0,50}clearance|"
                   r"(?:top secret|ts/sci|secret) clearance (?:is )?(?:required|mandatory)", re.I)
CLEAR_OK = re.compile(r"(?:ability|eligib\w+|willing\w*|able|obtain|eligible)[^.\n]{0,40}(?:obtain|get|receive|clear)", re.I)
GRAD = re.compile(r"(?:master'?s|m\.s\.|phd|doctorate)[^.\n]{0,50}(?:required|is required|minimum)|requires? an? (?:master'?s|phd)", re.I)


def screen(text):
    """Return (verdict, reason): ('SKIP', why) | ('WEAK', why) | ('PASS', '')."""
    t = re.sub(r"\s+", " ", text)
    hard, soft = [], []
    for rx in (YEARS, YEARS2):
        for m in rx.finditer(t):
            n = int(m.group(1))
            ctx = t[max(0, m.start() - 80): m.end() + 80]
            if n >= 2 and n <= 15:
                (soft if SOFT.search(ctx) else hard).append(f"{n}+ years: \"{t[m.start():m.end()][:90].strip()}\"")
            elif n == 1:
                soft.append(f"1 year: \"{t[m.start():m.end()][:80].strip()}\"")
    if hard:
        return "SKIP", "explicit experience requirement - " + hard[0]
    m = CLEAR.search(t)
    if m and not CLEAR_OK.search(t[max(0, m.start() - 60): m.end() + 60]):
        return "SKIP", f"clearance required - \"{m.group(0)[:80]}\""
    m = GRAD.search(t)
    if m and "bachelor" not in t[max(0, m.start() - 80): m.end() + 80].lower():
        return "SKIP", f"graduate degree required - \"{m.group(0)[:80]}\""
    if soft:
        return "WEAK", "; ".join(soft[:2])
    return "PASS", ""


def run(p, store, workers=16, limit=None):
    import sqlite3
    db = store.db
    rows = db.execute("SELECT url,title,company FROM jobs WHERE status='candidate' AND jd IS NULL").fetchall()
    if limit:
        rows = rows[:limit]

    def work(r):
        try:
            return r, fetch_text(r[0])
        except Exception as e:
            return r, None

    stats = {"SKIP": 0, "WEAK": 0, "PASS": 0, "nofetch": 0}
    with ThreadPoolExecutor(workers) as ex:
        for (url, title, company), text in ex.map(work, rows):
            if not text or len(text) < 200:
                stats["nofetch"] += 1  # leave as candidate: the LLM agent can still try
                db.execute("UPDATE jobs SET jd='', prescreen='nofetch' WHERE url=?", (url,))
                continue
            v, why = screen(text)
            stats[v] += 1
            if v == "SKIP":
                db.execute("UPDATE jobs SET jd=?, prescreen='SKIP', verdict='SKIP', reason=?, status='skipped' WHERE url=?",
                           (text[:30000], "[prescreen] " + why, url))
            else:
                db.execute("UPDATE jobs SET jd=?, prescreen=?, reason=? WHERE url=?",
                           (text[:30000], v, ("[prescreen] " + why) if why else None, url))
        db.commit()
    return stats


STAFFING = re.compile(r"consult|staffing|solutions|systems|infotech|technolog|group|inc$|llc$", re.I)


def export_queue(p, store, max_items=250):
    """Group remaining candidates by (company,title), write the posting text to out/jd/<n>.txt and the queue to
    out/fitcheck-queue.json, ordered: entry-level-wording titles first, then PASS, then WEAK/nofetch."""
    boost = re.compile(p.cfg["titles"]["boost"], re.I) if p.cfg["titles"].get("boost") else None
    rows = store.db.execute("SELECT company,title,location,url,prescreen,reason,jd FROM jobs WHERE status='candidate'").fetchall()
    groups = {}
    for c, t, l, u, ps, why, jd in rows:
        g = groups.setdefault((c, t), {"company": c, "title": t, "locations": [], "urls": [], "prescreen": ps, "note": why, "jd": jd})
        g["locations"].append(l)
        g["urls"].append(u)
    rank = lambda g: (0 if boost and boost.search(g["title"] or "") else 1, {"PASS": 0, "WEAK": 1}.get(g["prescreen"], 2), g["company"] or "")
    queue = sorted(groups.values(), key=rank)[:max_items]
    jd_dir = p.out_dir / "jd"
    jd_dir.mkdir(exist_ok=True)
    out = []
    for n, g in enumerate(queue, 1):
        text = (g.pop("jd") or "")[:6000]
        (jd_dir / f"{n}.txt").write_text(f"{g['title']} | {g['company']} | {'; '.join(sorted(set(g['locations'])))[:200]}\n{g['urls'][0]}\n\n{text}\n")
        g["n"] = n
        g["locations"] = sorted(set(g["locations"]))[:6]
        g["urls"] = g["urls"]
        out.append(g)
    (p.out_dir / "fitcheck-queue.json").write_text(json.dumps(out, indent=1))
    return len(groups), len(out)
