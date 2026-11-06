"""UKG / UltiPro Recruiting adapter (stdlib): public JSON used by recruiting.ultipro.com job boards.
POST https://recruiting.ultipro.com/<TENANT>/JobBoard/<board-guid>/JobBoardView/LoadSearchResults  (no key).
Tenant+guid pairs must be discovered (URL of the employer's board)."""
import json, time, urllib.request
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
BOARDS = {"YEL1000YLINC/0c14f090-cf70-4b25-b2fd-17f8267dcc0b": "YLINC (YEL1000, mostly stale 2023-24 postings)",
          "LSP1000LSPH/049cae3f-8230-40cd-a608-33646f459518": "Legacy Service Partners",
          "LBF1000LBFC/6abb5bbf-0835-4248-89f6-e1dc1ac46bff": "L.B. Foster"}

def fetch_board(key, name, query="", page=50, max_pages=10):
    t, g = key.split("/")
    base = f"https://recruiting.ultipro.com/{t}/JobBoard/{g}"
    out = []
    for i in range(max_pages):
        body = {"opportunitySearch": {"Top": page, "Skip": i * page, "QueryString": query,
                "OrderBy": [{"Value": "postedDateDesc", "PropertyName": "PostedDate", "Ascending": False}], "Filters": []},
                "matchCriteria": {"PreferredJobs": [], "Educations": [], "LicenseAndCertifications": [], "Skills": [], "hasNoLicenses": False, "SkippedSkills": []}}
        req = urllib.request.Request(f"{base}/JobBoardView/LoadSearchResults", data=json.dumps(body).encode(), method="POST",
              headers={"User-Agent": UA, "Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        for o in d.get("opportunities", []):
            locs = []
            for l in o.get("Locations", []):
                a = l.get("Address") or {}
                locs.append(f'{a.get("City") or l.get("LocalizedDescription")}, {(a.get("State") or {}).get("Code","")}')
            out.append({"title": o["Title"], "company": name, "location": "; ".join(locs),
                        "url": f'{base}/OpportunityDetail?opportunityId={o["Id"]}', "posted": (o.get("PostedDate") or "")[:10]})
        time.sleep(0.6)
        if len(d.get("opportunities", [])) < page: break
    return out

def fetch_jobs(slug, query=""):
    """slug = "<TENANT>/<board-guid>", e.g. "LSP1000LSPH/049cae3f-8230-40cd-a608-33646f459518"."""
    return fetch_board(slug, BOARDS.get(slug, slug.split("/")[0]), query)

if __name__ == "__main__":
    for k in BOARDS:
        js = fetch_jobs(k); print(k, len(js)); [print(j) for j in js[:2]]
