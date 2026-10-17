"""BambooHR public careers list (no key)."""
import json
import urllib.request


def fetch_jobs(sub):
    req = urllib.request.Request(f"https://{sub}.bamboohr.com/careers/list", headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read()).get("result", [])
    out = []
    for j in res:
        loc = j.get("location") or {}
        place = ", ".join(x for x in (loc.get("city"), loc.get("state")) if x)
        if j.get("isRemote") or j.get("locationType") == "1":
            place += " (Remote)"
        out.append({"title": j.get("jobOpeningName"), "location": place, "url": f"https://{sub}.bamboohr.com/careers/{j.get('id')}"})
    return out
