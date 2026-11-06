"""PageUp People adapter (stdlib): server-rendered listing, no key.
https://careers.pageuppeople.com/<id>/<site>/en-us/listing/?page=N  (site code usually 'cw'; 'ci' or 'ex' on some tenants).
slug = "<id>" (tries cw, ci, ex, in, ext) or "<id>/<site>". Known TX ids: 1151 UNT System."""
import re, time, html, urllib.request, urllib.error
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
SITES = ("cw", "ci", "ex", "in", "ext")
_ROW = re.compile(r'<a class="job-link" href="([^"]+)">([^<]+)</a>.*?<span class="location">([^<]*)</span>.*?(?:<td>\s*(?:<span[^>]*>)?([^<]*?)\s*(?:</span>)?\s*</td>)?\s*</tr>', re.S)


def _get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError:
        return ""


def fetch_jobs(slug, max_pages=30):
    pid, _, site = slug.partition("/")
    for s in ([site] if site else SITES):
        if "job-link" in _get(f"https://careers.pageuppeople.com/{pid}/{s}/en-us/listing/") or s == site:
            site = s; break
    else:
        raise ValueError("no PageUp listing found for " + slug)
    seen, out = set(), []
    for p in range(1, max_pages + 1):
        t = _get(f"https://careers.pageuppeople.com/{pid}/{site}/en-us/listing/?page={p}")
        rows = _ROW.findall(t)
        new = [r for r in rows if r[0] not in seen]
        for href, title, loc, closes in new:
            seen.add(href)
            out.append({"title": html.unescape(title.strip()), "company": f"pageup:{pid}", "location": html.unescape(loc.strip()),
                        "url": "https://careers.pageuppeople.com" + href, "posted": None})
        time.sleep(0.5)
        if not new: break
    return out


if __name__ == "__main__":
    import sys
    for s in sys.argv[1:] or ["1151"]:
        js = fetch_jobs(s); print(s, len(js)); [print(j) for j in js[:3]]
