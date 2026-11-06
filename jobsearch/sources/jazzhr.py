"""JazzHR public career page HTML (no key): https://{slug}.applytojob.com/apply"""
import html
import re

from . import get_text


def fetch_jobs(slug):
    h = get_text(f"https://{slug}.applytojob.com/apply")
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    company = slug
    if m:
        company = re.sub(r"\s*-?\s*Career Page.*$", "", html.unescape(m.group(1)).strip()) or slug
    out = []
    for li in re.findall(r'<li class="list-group-item">(.*?)</li>\s*(?=<li class="list-group-item">|</ul>)', h, re.S):
        a = re.search(r'<a href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', li, re.S)
        if not a:
            continue
        loc = re.search(r"fa-map-marker'></i>\s*([^<]*)", li)
        out.append({"title": html.unescape(a.group(2)).strip(), "company": company,
                    "location": html.unescape(loc.group(1)).strip() if loc else "",
                    "url": a.group(1), "posted": None})
    return out
