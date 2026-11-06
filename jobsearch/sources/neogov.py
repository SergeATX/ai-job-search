"""NEOGOV adapter (stdlib): per-agency listing, no key/login.
GET https://www.governmentjobs.com/careers/<slug>?page=N&pagetype=jobOpportunitiesJobs  (header X-Requested-With: XMLHttpRequest)
returns server-rendered <li class="list-item"> fragments (10/page). Invalid slug -> 302 to home (-> ValueError).
Education agencies also live on schooljobs.com (same paths) - pass slug as "schooljobs:<slug>".
'posted' is derived from the relative text ("Posted 6 days ago"); ">30 days" -> None-ish approximate date 30d ago.
"""
import re, time, html, datetime, urllib.request, urllib.error

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
_ITEM = re.compile(r'<li class="list-item" data-job-id="(\d+)">(.*?)(?=<li class="list-item" data-job-id=|</ul>\s*</div>\s*$|\Z)', re.S)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _get(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"})
            with _opener.open(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (301, 302):
                raise ValueError("unknown agency slug")
            if e.code == 429:
                time.sleep(5 * (i + 1)); continue
            raise
    return ""


def _posted(txt):
    m = re.search(r"Posted (more than )?(\d+) (hour|day|week|month)s? ago|Posted (today|yesterday)", txt or "")
    if not m:
        return None
    d = datetime.date.today()
    if m.group(4) == "yesterday":
        d -= datetime.timedelta(days=1)
    elif m.group(2):
        n = int(m.group(2)); u = m.group(3)
        d -= datetime.timedelta(days={"hour": 0, "day": n, "week": 7 * n, "month": 30 * n}[u] if u != "hour" else 0)
    return d.isoformat()


def fetch_jobs(slug, max_pages=30):
    host = "www.governmentjobs.com"
    if slug.startswith("schooljobs:"):
        host, slug = "www.schooljobs.com", slug.split(":", 1)[1]
    seen, jobs, name = set(), [], None
    for p in range(1, max_pages + 1):
        page = _get(f"https://{host}/careers/{slug}?page={p}&pagetype=jobOpportunitiesJobs")
        items = _ITEM.findall(page)
        new = 0
        for jid, b in items:
            if jid in seen:
                continue
            seen.add(jid); new += 1
            t = re.search(r'class="item-details-link"[^>]*href="([^"]+)"[^>]*>([^<]+)<', b)
            if not t:
                continue
            first = re.search(r'<ul class="list-meta">\s*<li>([^<]*)</li>', b)
            loc = first if first and not re.search(r"\$|Full|Part|Temporary|Regular|Seasonal|Hourly|Annually|Category|Department", first.group(1), re.I) else None
            dep = re.search(r"Department:\s*([^<\n]+)", b)
            jobs.append({"title": html.unescape(t.group(2).strip()),
                         "company": slug,
                         "location": html.unescape(loc.group(1).strip()) if loc else "",
                         "url": f"https://{host}{t.group(1)}", "posted": _posted(b)})
        time.sleep(0.5)
        if not new:
            break
    return jobs


if __name__ == "__main__":
    import sys
    js = fetch_jobs(sys.argv[1] if len(sys.argv) > 1 else "harriscountytx")
    print(len(js))
    for j in js[:5]: print(j)
