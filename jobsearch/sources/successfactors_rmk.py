"""SuccessFactors Recruiting Marketing (RMK) career-site adapter via the public /sitemap.xml job feed. slug = career-site host
e.g. "careers.skyworksinc.com", "jobs.halliburton.com". No posted date in the feed (posted=None; expiration is ~30d out).
Some sites' sitemap.xml is a plain list of page URLs instead (careers.phillips66.com); those are read from the site's
search pages (/search/?startrow=N, title and place per row, a second apart)."""
import re, sys, time, urllib.request, html, xml.etree.ElementTree as ET
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
G = "{http://base.google.com/ns/1.0}"
ROW = re.compile(r'<tr class="data-row">(.*?)</tr>', re.S)
TOTAL = re.compile(r'class="paginationLabel"[^>]*>.*?of <b>([\d,]+)</b>', re.S)


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90).read()


def _search(slug, max_pages=100):
    out, start = {}, 0
    for _ in range(max_pages):
        page = _get(f"https://{slug}/search/?q=&sortColumn=referencedate&sortDirection=desc&startrow={start}").decode("utf-8", "replace")
        rows = ROW.findall(page)
        for r in rows:
            a = re.search(r'<a[^>]*href="(/job/[^"]+)"[^>]*class="jobTitle-link"[^>]*>(.*?)</a>', r, re.S) \
                or re.search(r'<a[^>]*class="jobTitle-link"[^>]*href="(/job/[^"]+)"[^>]*>(.*?)</a>', r, re.S)
            if not a:
                continue
            loc = re.search(r'<span class="jobLocation">\s*(.*?)\s*</span>', r, re.S)
            url = f"https://{slug}{html.unescape(a[1])}"
            out.setdefault(url, {"title": html.unescape(re.sub(r"\s+", " ", a[2])).strip(), "company": slug,
                                 "location": html.unescape(re.sub(r"\s+", " ", loc[1])).strip() if loc else "",
                                 "url": url, "posted": None})
        m = TOTAL.search(page)
        start += len(rows)
        if not rows or not m or start >= int(m[1].replace(",", "")):
            break
        time.sleep(1)
    return list(out.values())


def fetch_jobs(slug):
    xml = _get(f"https://{slug}/sitemap.xml")
    root = ET.fromstring(xml)
    if root.tag.endswith("urlset"):
        return _search(slug)
    out = []
    for it in root.iter("item"):
        g = lambda t: (it.findtext(t) or "").strip()
        out.append({"title": html.unescape(g("title")), "company": g(G + "employer") or slug, "location": g(G + "location"),
                    "url": g("link"), "posted": None})
    return out


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["careers.skyworksinc.com"]):
        js = fetch_jobs(s); print(s, len(js), "jobs;", sum('TX' in j['location'] or 'Texas' in j['location'] for j in js), "TX-ish"); print(js[0])
