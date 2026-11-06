"""Phenom People career-site adapter (urllib only).
slug = "<host>[|<locale path>]" e.g. "careers.teksystems.com|us/en". Uses the public /widgets refineSearch endpoint."""
import json, re, sys, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def _post(host, body, ref):
    req = urllib.request.Request(f"https://{host}/widgets", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": UA, "Referer": ref,
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _boot(host, loc):
    """Read locale/country/pageId/ddo hints from the search page when available."""
    try:
        req = urllib.request.Request(f"https://{host}/{loc}/search-results", headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf8", "ignore")
    except Exception:
        return {}
    out = {}
    m = re.search(r'"pageId"\s*:\s*"([^"]+)"', html)
    if m: out["pageId"] = m.group(1)
    return out


def fetch_jobs(slug, max_jobs=2000, size=50):
    host, _, loc = slug.partition("|")
    loc = loc or "us/en"
    country, lang = (loc.split("/") + ["en"])[:2]
    lang_code = f"{lang}_{country}"
    base = f"https://{host}/{loc}"
    hints = _boot(host, loc)
    out, frm, total = [], 0, None
    while frm < (max_jobs if total is None else min(total, max_jobs)):
        body = {"lang": lang_code, "deviceType": "desktop", "country": country, "pageName": "search-results",
                "ddoKey": "refineSearch", "sortBy": "", "subsearch": "", "from": frm, "jobs": True, "counts": True,
                "all_fields": ["category", "country", "state", "city", "type"], "size": size, "clearAll": False,
                "jdsource": "facets", "isSliderEnable": False, "pageId": hints.get("pageId", "page11"),
                "siteType": "external", "location": "", "keywords": "", "global": True, "selected_fields": {},
                "sort": {"order": "desc", "field": "postedDate"}, "locationData": {}}
        d = _post(host, body, base + "/search-results")
        rs = (d.get("refineSearch") or {})
        total = rs.get("totalHits", 0)
        jobs = (rs.get("data") or {}).get("jobs") or []
        for j in jobs:
            loc_s = j.get("location") or ", ".join(x for x in (j.get("city"), j.get("state"), j.get("country")) if x)
            jid = j.get("jobSeqNo") or j.get("jobId") or j.get("reqId")
            url = f"{base}/job/{jid}/{re.sub(r'[^A-Za-z0-9]+','-',j.get('title') or '').strip('-')}"
            out.append({"title": j.get("title"), "company": j.get("company") or host, "location": loc_s,
                        "url": url, "posted": j.get("postedDate") or j.get("dateCreated")})
        if not jobs:
            break
        frm += size
    return out


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else "careers.teksystems.com|us/en"
    js = fetch_jobs(slug, max_jobs=120)
    print(len(js), "jobs")
    for j in js[:5]: print(j)
