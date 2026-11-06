"""PeopleAdmin adapter (stdlib): public Atom feed https://<tenant>.peopleadmin.com/postings/all_jobs (no key).
slug = tenant (e.g. "uta") or a full custom host (e.g. "jobs.utdallas.edu").
Feed has title/published/link/author(=department); no location (use TENANTS default). An empty tenant returns a
single 'No Positions Currently Open' placeholder entry which is dropped. Unknown tenant -> DNS error (raises)."""
import html, urllib.request
import xml.etree.ElementTree as ET
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
TENANTS = {"jobs.utdallas.edu": ("University of Texas at Dallas", "Richardson, TX"),
           "careers.utrgv.edu": ("UT Rio Grande Valley", "Edinburg, TX"),
           "uta": ("University of Texas at Arlington", "Arlington, TX"),
           "shsu": ("Sam Houston State University", "Huntsville, TX"),
           "txwes": ("Texas Wesleyan University", "Fort Worth, TX")}
NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch_jobs(slug):
    name, loc = TENANTS.get(slug, (slug, "TX"))
    req = urllib.request.Request(f"https://{slug if '.' in slug else slug + '.peopleadmin.com'}/postings/all_jobs", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for e in root.findall("a:entry", NS):
        l = e.find("a:link", NS)
        url = l.get("href") if l is not None else ""
        if url.endswith("/postings/search"):
            continue
        out.append({"title": html.unescape((e.findtext("a:title", "", NS) or "").strip()),
                    "company": name, "location": loc, "url": url,
                    "posted": (e.findtext("a:published", "", NS) or "")[:10]})
    return out


if __name__ == "__main__":
    import re
    for s in TENANTS:
        js = fetch_jobs(s); print(s, len(js))
        print([j["title"] for j in js if re.search(r"software|developer|data|programmer|analyst", j["title"], re.I)][:4])
