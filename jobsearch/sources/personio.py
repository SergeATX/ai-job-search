"""Personio public XML job feed (no key)."""
import urllib.request
import xml.etree.ElementTree as ET


def fetch_jobs(sub):
    req = urllib.request.Request(f"https://{sub}.jobs.personio.de/xml", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())  # unknown subdomain serves HTML -> ParseError -> probe counts 0
    out = []
    for p in root.iter("position"):
        t = lambda tag: (p.findtext(tag) or "").strip()
        out.append({"title": t("name"), "company": t("subcompany") or None, "location": t("office"),
                    "url": f"https://{sub}.jobs.personio.de/job/{t('id')}", "posted": t("createdAt")})
    return out
