"""Eightfold AI career-site adapter (urllib only). slug = "<subdomain>|<domain>" e.g. "lockheedmartin|lockheedmartin.com".
Endpoint: https://<sub>.eightfold.ai/api/pcsx/search?domain=<domain>&query=&start=N&num=N"""
import json, sys, urllib.request, urllib.parse, datetime

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch_jobs(slug, max_jobs=2000, location=""):
    sub, _, domain = slug.partition("|")
    host = sub if "." in sub else f"{sub}.eightfold.ai"
    out, start = [], 0
    while start < max_jobs:
        q = {"domain": domain, "query": "", "start": start, "num": 10, "sort_by": "timestamp"}
        if location: q["location"] = location
        req = urllib.request.Request(f"https://{host}/api/pcsx/search?" + urllib.parse.urlencode(q),
                                     headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        pos = (d.get("data") or {}).get("positions") or []
        for p in pos:
            ts = p.get("postedTs") or p.get("creationTs")
            posted = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d") if ts else None
            out.append({"title": p.get("name"), "company": domain, "location": "; ".join(p.get("locations") or []),
                        "url": f"https://{host}{p.get('positionUrl') or '/careers/job/' + str(p.get('id'))}", "posted": posted})
        if len(pos) < 10: break
        start += len(pos)
    return out


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "lockheedmartin|lockheedmartin.com"
    js = fetch_jobs(slug, max_jobs=60)
    print(len(js), "jobs"); [print(j) for j in js[:4]]
    tx = fetch_jobs(slug, max_jobs=30, location="Texas"); print(len(tx), "with location=Texas; sample:", [j["location"] for j in tx[:3]])
