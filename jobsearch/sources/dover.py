"""Dover careers public API (no key). slug = client UUID (first path segment of app.dover.com/apply/<uuid>/<job>)."""
import json
import urllib.request

BASE = "https://app.dover.com/api/v1/careers-page/"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def fetch_jobs(uuid):
    company = uuid
    try:
        company = _get(BASE + uuid).get("name") or uuid
    except Exception:
        pass
    out, url = [], f"{BASE}{uuid}/jobs?limit=100"
    while url:
        res = _get(url)
        for j in res.get("results") or []:
            if not j.get("is_published", True) or j.get("is_sample"):
                continue
            locs = "; ".join(l.get("name") or "" for l in j.get("locations") or [])
            if (j.get("workplace_type") or "").upper() == "REMOTE":
                locs += " (Remote)"
            out.append({"title": j.get("title"), "company": company, "location": locs,
                        "url": f"https://app.dover.com/apply/{uuid}/{j.get('id')}", "posted": None})
        url = res.get("next")
    return out
