"""Paylocity Recruiting public board (no key). slug = company GUID."""
import json
import re

from . import get_text


def fetch_jobs(guid):
    h = get_text(f"https://recruiting.paylocity.com/recruiting/jobs/All/{guid}")
    m = re.search(r"window\.pageData\s*=\s*(\{.*?\});\s*(?:\n|</script>)", h, re.S)
    if not m:
        return []  # "Job Not Found" page
    data = json.loads(m.group(1))
    out = []
    for j in data.get("Jobs") or []:
        loc = j.get("LocationName") or ""
        jl = j.get("JobLocation") or {}
        if jl.get("City") or jl.get("State"):
            loc = ", ".join(x for x in (jl.get("City") or loc, jl.get("State")) if x)
        if j.get("IsRemote"):
            loc += " (Remote)"
        out.append({"title": j.get("JobTitle"), "company": guid, "location": loc,
                    "url": f"https://recruiting.paylocity.com/Recruiting/Jobs/Details/{j.get('JobId')}",
                    "posted": j.get("PublishedDate")})
    return out
