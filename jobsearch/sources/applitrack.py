"""Frontline AppliTrack (K-12 ISDs) adapter (stdlib): https://www.applitrack.com/<id>/onlineapp/jobpostings/Output.asp?all=1
returns the full posting list as document.write() JS; parse title / JobID / Date Posted / Location. No key. slug = id (e.g. 'austin')."""
import re, html, datetime, urllib.request
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
_J = re.compile(r"<td id=\\?'wrapword\\?'[^>]*>(.*?)</td>.*?JobID: (\d+)(.*?)(?=<table class=\\?'title|\Z)", re.S)


def fetch_jobs(slug):
    req = urllib.request.Request(f"https://www.applitrack.com/{slug}/onlineapp/jobpostings/Output.asp?all=1", headers={"User-Agent": UA})
    t = urllib.request.urlopen(req, timeout=60).read().decode("latin1")
    out = []
    for title, jid, rest in _J.findall(t):
        d = re.search(r"Date Posted:.*?class=\\?[\"']normal\\?[\"']>([\d/]+)<", rest, re.S)
        l = re.search(r"Location:.*?class=\\?[\"']normal\\?[\"']>([^<]*)<", rest, re.S)
        posted = None
        if d:
            try: posted = datetime.datetime.strptime(d.group(1), "%m/%d/%Y").date().isoformat()
            except ValueError: pass
        out.append({"title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(), "company": slug,
                    "location": html.unescape(l.group(1)).strip() if l else "",
                    "url": f"https://www.applitrack.com/{slug}/onlineapp/default.aspx?AppliTrackJobId={jid}&AppliTrackLayoutMode=detail&AppliTrackViewPosting=1",
                    "posted": posted})
    return out


if __name__ == "__main__":
    import sys
    js = fetch_jobs(sys.argv[1] if len(sys.argv) > 1 else "austin"); print(len(js)); [print(j) for j in js[:3]]
    import re as _r; print([j["title"] for j in js if _r.search(r"software|developer|data|analyst|technology|IT ", j["title"], _r.I)][:8])
