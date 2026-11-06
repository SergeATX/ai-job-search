"""jobright-ai GitHub lists (daily, new-grad SWE / data-analysis, plus optional intern repos). README tables:
| Company (or ↳ continuation) | [Title](https://jobright.ai/jobs/info/<id>) | Location | Work model | Date |
Links point to jobright.ai job pages (NOT the employer ATS) so dedup vs catalog must use company+title.  urllib only."""
import re, urllib.request
_TX = re.compile(r"\b(austin|dallas|houston|san antonio|texas|plano|irving|frisco|fort worth|richardson|round rock|the woodlands|addison|el paso)\b|,\s*TX\b", re.I)
_NONUS = re.compile(r"\b(canada|uk|united kingdom|london|india|germany|poland|europe|emea|apac|latam|brazil|mexico|australia|singapore|israel|ireland|france|paris|toronto|bulgaria|hungary|romania|japan|china)\b", re.I)
def geo_ok(loc):
    """True for a Texas location, or a remote / nationwide-US posting (not remote-in-another-country, not a non-TX onsite city)."""
    loc = loc or ""
    if _TX.search(loc): return True
    us = re.search(r"united states|\busa\b|\bu\.?s\.?\b", loc, re.I)
    if _NONUS.search(loc) and not us: return False
    if re.search(r"remote|anywhere|nationwide", loc, re.I): return True
    rest = re.sub(r"united states|\busa\b|\bu\.?s\.?a?\b|\bon[- ]?site\b|\bhybrid\b|[()/;,+\d-]|\b(or|and)\b", " ", loc, flags=re.I).strip()
    return bool(us) and not rest
UA = "Mozilla/5.0"
REPOS = ["2026-Software-Engineer-New-Grad", "2026-Data-Analysis-New-Grad", "2026-Engineering-New-Grad"]
INTERN_REPOS = ["2026-Software-Engineer-Internship", "2026-Data-Analysis-Internship"]

def fetch_jobs(repos=REPOS, geo_only=True):
    out, seen = [], set()
    for r in repos:
        try:
            t = urllib.request.urlopen(urllib.request.Request(f"https://raw.githubusercontent.com/jobright-ai/{r}/master/README.md", headers={"User-Agent": UA}), timeout=60).read().decode()
        except Exception as e:
            print(f"jobright {r}: {e}"); continue
        comp = None
        for row in t.splitlines():
            if not row.startswith("| "): continue
            c = [x.strip() for x in row.strip("|").split("|")]
            if len(c) < 5: continue
            m = re.search(r"\[([^\]]+)\]", c[0])
            if m: comp = m.group(1)
            elif "↳" not in c[0]: continue
            tm = re.search(r"\[([^\]]+)\]\((https://jobright\.ai/jobs/info/[^)\s]+)\)", c[1])
            if not tm: continue
            url = tm.group(2).split("?")[0]
            loc = f"{c[2]} ({c[3]})"
            if url in seen or (geo_only and not geo_ok(loc)): continue
            seen.add(url)
            title = re.sub(r"\s+Job Details\s*/.*$", "", tm.group(1)).strip()
            out.append({"title": title, "company": comp, "location": loc, "url": url, "posted": c[4], "level": "new grad"})
    return out

if __name__ == "__main__":
    r = fetch_jobs()
    assert r and all(x["url"] and x["title"] and x["company"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
