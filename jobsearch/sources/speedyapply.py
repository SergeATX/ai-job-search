"""speedyapply GitHub college-jobs markdown tables (NEW_GRAD_USA.md for SWE and AI/data repos). Public raw GitHub.
Row: | <a company> | title | location | salary | <a href=apply url> | age |   (the README.md files of these repos are INTERN lists: opt-in only).  urllib only."""
import html, re, urllib.request
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
FILES = ["2026-SWE-College-Jobs/main/NEW_GRAD_USA.md", "2026-AI-College-Jobs/main/NEW_GRAD_USA.md"]
INTERN_FILES = ["2026-SWE-College-Jobs/main/README.md", "2026-AI-College-Jobs/main/README.md"]

def fetch_jobs(files=FILES, geo_only=True):
    out, seen = [], set()
    for f in files:
        try:
            t = urllib.request.urlopen(urllib.request.Request("https://raw.githubusercontent.com/speedyapply/" + f, headers={"User-Agent": UA}), timeout=60).read().decode()
        except Exception as e:
            print(f"speedyapply {f}: {e}"); continue
        for row in t.splitlines():
            if not row.startswith("| <a"): continue
            c = [x.strip() for x in row.strip("|").split("|")]
            if len(c) < 5: continue
            u = re.search(r'href="([^"]+)"', c[4]); name = re.sub(r"<[^>]+>", "", c[0])
            loc = html.unescape(c[2])
            if not u or u.group(1) in seen or (geo_only and not geo_ok(loc)): continue
            seen.add(u.group(1))
            out.append({"title": html.unescape(re.sub(r"<[^>]+>", "", c[1])), "company": html.unescape(name).strip(), "location": loc,
                        "url": u.group(1), "posted": c[-1], "level": "new grad"})
    return out

if __name__ == "__main__":
    r = fetch_jobs()
    assert r and all(x["url"] and x["title"] and x["company"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
