"""TalentBrew (Radancy) career-site adapter, urllib only. slug = "<host>[|<locale>]" e.g. "careers.l3harris.com|en".
Endpoint: https://<host>/<locale>/search-jobs/results?CurrentPage=N&RecordsPerPage=100... returns JSON {"results": "<html>"}."""
import html as H, json, re, sys, urllib.request, urllib.parse
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch_jobs(slug, max_jobs=2000, location=""):
    host, _, loc = slug.partition("|")
    pre = f"https://{host}/{loc}".rstrip("/") if loc else f"https://{host}"
    out, page = [], 1
    while len(out) < max_jobs:
        q = dict(ActiveFacetID=0, CurrentPage=page, RecordsPerPage=100, Distance=50, RadiusUnitType=0, Keywords="", Location=location,
                 ShowRadius="False", IsPagination="False", CustomFacetName="", FacetTerm="", FacetType=0,
                 SearchResultsModuleName="Search Results", SearchFiltersModuleName="Search Filters", SortCriteria=0,
                 SortDirection=0, SearchType=5, PostalCode="", ResultsType=0, fc="", fl="", fcf="", afc="", afl="", afcf="", TotalContentResults="")
        req = urllib.request.Request(f"{pre}/search-jobs/results?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        h = d.get("results") or ""
        items = re.findall(r'<li[^>]*>\s*<a href="(/[^"]*?/job/[^"]+)"[^>]*>(.*?)</a>', h, re.S)
        for href, inner in items:
            t = re.search(r"<h[23][^>]*>(.*?)</h[23]>", inner, re.S)
            l = re.search(r'class="[^"]*job-location[^"]*"[^>]*>(.*?)</span>', inner, re.S)
            strip = lambda x: H.unescape(re.sub(r"<[^>]+>", "", x or "")).strip()
            out.append({"title": strip(t.group(1)) if t else None, "company": host, "location": strip(l.group(1)) if l else "",
                        "url": f"https://{host}{href}", "posted": None})
        m = re.search(r'data-total-pages="(\d+)"', h)
        if not items or not m or page >= int(m.group(1)): break
        page += 1
    return out


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["careers.l3harris.com|en"]):
        js = fetch_jobs(s, 120); print(s, len(js)); [print(j) for j in js[:3]]
