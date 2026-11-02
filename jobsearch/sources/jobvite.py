"""Jobvite public career-site HTML (no key): https://jobs.jobvite.com/{slug}/jobs"""
import html
import re
import urllib.request


def fetch_jobs(slug):
    req = urllib.request.Request(f"https://jobs.jobvite.com/{slug}/jobs", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        if "/support/" in r.geturl() or "jobs.jobvite.com" not in r.geturl():
            return []  # unknown slug redirects to marketing site
        h = r.read().decode("utf-8", "replace")
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    company = html.unescape(m.group(1)).replace("Careers", "").strip() if m else slug
    out = []
    for row in re.findall(r'<tr>(.*?)</tr>', h, re.S):
        a = re.search(r'jv-job-list-name">\s*<a href="(/[^"]+/job/[^"]+)"[^>]*>(.*?)</a>', row, re.S)
        if not a:
            continue
        l = re.search(r'jv-job-list-location">(.*?)</td>', row, re.S)
        loc = ""
        if l:
            t = re.sub(r"<span>,</span>", ",", l.group(1))
            t = html.unescape(re.sub(r"<[^>]+>", " ", t))
            loc = re.sub(r"\s+", " ", t).strip().rstrip(",")
        out.append({"title": html.unescape(a.group(2)).strip(), "company": company, "location": loc,
                    "url": "https://jobs.jobvite.com" + a.group(1), "posted": None})
    return out
