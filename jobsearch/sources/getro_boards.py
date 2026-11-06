"""Getro-powered VC/community portfolio boards (public POST api.getro.com/api/v2/collections/<network_id>/search/jobs).
Needs `Accept: application/json` (else HTTP 406). Server-side filter seniority=entry_level (also tried: locations filter is
ignored by the API), so we page the entry-level slice of each network and filter TX / remote-US client-side.
Returns [{title, company, location, url, posted}]; urllib only."""
import json, re, sys, time, urllib.request
UA = "Mozilla/5.0"
NETWORKS = {  # host -> network id (from vc/boards.json probes)
 "capitalfactory": 719, "silvertonpartners": 230, "techstars": 89, "8vc": 1005, "thrivecap": 2105, "menlovc": 767, "dcvc": 514,
 "craftventures": 340, "nfx": 307, "eniac": 117, "insightpartners": 246, "trueventures": 646, "generalcatalyst": 222,
 "accel": 8672, "khoslaventures": 257, "fifthwall": 1636, "bonfirevc": 790, "lightbank": 10322, "vmgpartners": 153,
 "drivecapital": 158, "rre": 114, "revolution": 143, "upfront": 184, "venrock": 319, "maveron": 810, "glasswing": 215,
 "greycroft": 616, "longjourney": 8279, "firstmark": 45303, "s3vc": 684, "liveoakvp": 946,
}
TX = re.compile(r"\b(austin|dallas|houston|san antonio|texas|plano|irving|frisco|fort worth|richardson|round rock|the woodlands)\b|,\s*TX\b", re.I)

def _search(nid, page, query="", filters=None, size=100):
    body = json.dumps({"hitsPerPage": size, "page": page, "query": query, "filters": filters or {}}).encode()
    r = urllib.request.Request(f"https://api.getro.com/api/v2/collections/{nid}/search/jobs", body,
                               {"content-type": "application/json", "Accept": "application/json", "User-Agent": UA})
    return json.load(urllib.request.urlopen(r, timeout=30))["results"]

def _loc(j):
    locs = list(j.get("searchable_locations") or [])
    names = [d.get("name") for d in (j.get("location_details") or []) if d.get("name")]
    return names, locs

def fetch_jobs(networks=NETWORKS, max_pages=12, delay=0.4, seniority="entry_level"):
    out, seen = [], set()
    for name, nid in networks.items():
        for p in range(max_pages):
            try: d = _search(nid, p, filters={"seniority": [seniority]})
            except Exception as e:
                print(f"getro {name}: {e}", file=sys.stderr); break
            for j in d["jobs"]:
                names, locs = _loc(j)
                allloc = "; ".join(names + locs)
                remote = j.get("work_mode") == "remote"
                us = any(re.search(r"United States|USA", l) for l in locs)
                if not (TX.search(allloc) or (remote and us)): continue
                u = j.get("url")
                if u in seen: continue
                seen.add(u)
                loc = "; ".join(names) or "; ".join(locs[:2])
                if remote: loc = (loc + " Remote").strip()
                out.append({"title": j.get("title"), "company": (j.get("organization") or {}).get("name"), "location": loc,
                            "url": u, "posted": j.get("created_at"), "level": seniority.replace("_", " "), "board": name})
            time.sleep(delay)
            if (p + 1) * 100 >= d["count"]: break
    return out

if __name__ == "__main__":
    r = fetch_jobs()
    assert r and all(x["url"] and x["title"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
