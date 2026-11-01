"""Teamtailor public RSS job feed (no key)."""
import urllib.request
import xml.etree.ElementTree as ET

TT = "{https://teamtailor.com/locations}"


def fetch_jobs(sub):
    req = urllib.request.Request(f"https://{sub}.teamtailor.com/jobs.rss", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())  # unknown subdomain serves HTML -> ParseError -> probe counts 0
    company = root.findtext("channel/title")
    out = []
    for it in root.iter("item"):
        locs = [", ".join(x for x in (l.findtext(TT + "city"), l.findtext(TT + "country")) if x) for l in it.iter(TT + "location")]
        place = "; ".join(x for x in locs if x)
        if it.findtext("remoteStatus") in ("fully", "remote"):
            place += " (Remote)"
        out.append({"title": it.findtext("title"), "company": company, "location": place,
                    "url": it.findtext("link"), "posted": it.findtext("pubDate")})
    return out
