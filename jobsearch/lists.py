"""Public curated job lists whose posting URLs reveal employers' job boards (feed to discover)."""
import json
import re
import urllib.request

SIMPLIFY = "https://raw.githubusercontent.com/SimplifyJobs/%s/dev/.github/scripts/listings.json"
READMES = {
    "speedyapply": "https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/README.md",
    "vanshb03": "https://raw.githubusercontent.com/vanshb03/New-Grad-2026/main/README.md",
}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf8", "ignore")


def urls(name):
    if name == "simplify-all":      # every listing ever, active or not: employers, not openings
        return [x["url"] for x in json.loads(_get(SIMPLIFY % "New-Grad-Positions"))]
    if name == "simplify-internships":  # employers that take interns also hire new grads
        return [x["url"] for x in json.loads(_get(SIMPLIFY % "Summer2026-Internships"))]
    if name in READMES:
        return re.findall(r"https?://[^\s)\"'<>\]]+", _get(READMES[name]))
    raise SystemExit(f"unknown list {name}")


ALL = ["simplify-all", "simplify-internships", *READMES]
