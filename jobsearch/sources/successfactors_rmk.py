"""SuccessFactors Recruiting Marketing (RMK) career-site adapter via the public /sitemap.xml job feed. slug = career-site host
e.g. "careers.skyworksinc.com", "jobs.halliburton.com". No posted date in the feed (posted=None; expiration is ~30d out)."""
import re, sys, urllib.request, html, xml.etree.ElementTree as ET
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
G = "{http://base.google.com/ns/1.0}"


def fetch_jobs(slug):
    xml = urllib.request.urlopen(urllib.request.Request(f"https://{slug}/sitemap.xml", headers={"User-Agent": UA}), timeout=90).read()
    root = ET.fromstring(xml)
    out = []
    for it in root.iter("item"):
        g = lambda t: (it.findtext(t) or "").strip()
        out.append({"title": html.unescape(g("title")), "company": g(G + "employer") or slug, "location": g(G + "location"),
                    "url": g("link"), "posted": None})
    return out


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["careers.skyworksinc.com"]):
        js = fetch_jobs(s); print(s, len(js), "jobs;", sum('TX' in j['location'] or 'Texas' in j['location'] for j in js), "TX-ish"); print(js[0])
