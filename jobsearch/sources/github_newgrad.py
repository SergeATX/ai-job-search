"""SimplifyJobs-format listings.json mirrors (public GitHub): vanshb03/New-Grad-2026 (cvrve) and SimplifyJobs/New-Grad-Positions.
Fields: company_name,title,locations[],url,active,is_visible,date_posted(epoch),sponsorship. (SimplifyJobs is already a repo source = simplify.py;
vanshb03 is mostly the same data but adds some rows.) Returns active rows with a TX location or remote-US.   urllib only."""
import json, re, urllib.request
UA = "Mozilla/5.0"
LISTS = {"vanshb03": "https://raw.githubusercontent.com/vanshb03/New-Grad-2026/dev/.github/scripts/listings.json",
         "simplify": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"}
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

def fetch_jobs(lists=("vanshb03",), geo_only=True):
    out, seen = [], set()
    for name in lists:
        data = json.load(urllib.request.urlopen(urllib.request.Request(LISTS[name], headers={"User-Agent": UA}), timeout=90))
        for x in data:
            if not x.get("active") or not x.get("is_visible", True) or not x.get("url") or x["url"] in seen: continue
            loc = "; ".join(x.get("locations") or [])
            if geo_only and not geo_ok(loc): continue
            seen.add(x["url"])
            out.append({"title": x.get("title"), "company": x.get("company_name"), "location": loc, "url": x["url"],
                        "posted": x.get("date_posted"), "level": "new grad", "src": name})
    return out

if __name__ == "__main__":
    r = fetch_jobs()
    assert r and all(x["url"] and x["title"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
