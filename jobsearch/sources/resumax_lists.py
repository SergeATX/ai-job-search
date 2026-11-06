"""resumax/new-grad-tech-jobs (GitHub README, refreshed daily, last-30-days new-grad SWE/data/AI/security/devops roles, senior filtered out).
Unlike jobright, the Apply column links straight to the employer ATS (Ashby/Greenhouse/Lever/SmartRecruiters/...), so apply-URL dedup works.
Row: | **[Company](resumax url)** badges | Role | Location | [Apply](ats url) | Tailor | Age |    urllib only."""
import re, urllib.request
UA = "Mozilla/5.0"
URL = "https://raw.githubusercontent.com/resumax/new-grad-tech-jobs/main/README.md"
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

DEV = re.compile(r"software|developer|engineer|data|analyst|machine learning|\bml\b|\bai\b|swe|devops|sre|python|scientist|security|cloud|platform|qa\b|test", re.I)
NOT_DEV = re.compile(r"mechanical|machinist|cnc|civil|chemical|manufacturing|robotics technician|hvac|nurse", re.I)

def fetch_jobs(url=URL, geo_only=True, dev_only=True):
    t = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read().decode()
    out, seen = [], set()
    for row in t.splitlines():
        if not row.startswith("| **["): continue
        c = [x.strip() for x in row.strip().strip("|").split("|")]
        if len(c) < 6: continue
        co = re.search(r"\*\*\[([^\]]+)\]", c[0]); ap = re.search(r"\[Apply\]\(([^)\s]+)\)", c[3])
        if not co or not ap: continue
        u = ap.group(1)
        if u in seen: continue
        loc = c[2]
        if geo_only and not geo_ok(loc): continue
        if dev_only and (not DEV.search(c[1]) or NOT_DEV.search(c[1])): continue
        seen.add(u)
        out.append({"title": c[1], "company": co.group(1), "location": loc, "url": u, "posted": c[-1], "level": "new grad"})
    return out

if __name__ == "__main__":
    r = fetch_jobs()
    assert r and all(x["url"] and x["title"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
