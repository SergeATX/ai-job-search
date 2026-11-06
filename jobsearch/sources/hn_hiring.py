"""HN 'Ask HN: Who is hiring?' monthly threads via Algolia public API (hn.algolia.com; poster account `whoishiring`).
Top-level comments = postings, first line 'Company | role | location | ...'. Keeps postings whose header mentions TX or remote;
`level` is set from the whole comment when it mentions junior/new grad/entry/intern/early career (rare: ~2%)."""
import html, json, re, sys, time, urllib.request
UA = "Mozilla/5.0"
WANT = re.compile(r"\b(texas|tx|austin|dallas|houston|san antonio|remote)\b", re.I)
NONUS_ONLY = re.compile(r"remote\s*\(?\s*(eu|europe|uk|emea|canada|india|germany|latam)\b", re.I)
ENTRYHINT = re.compile(r"new[- ]grad|junior|entry[- ]level|early[- ]career|recent grad|graduate|apprentice", re.I)

def _get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=30).read())

def fetch_jobs(months=3, want=WANT):
    posts = _get("https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=12")["hits"]
    posts = [p for p in posts if "who is hiring" in p["title"].lower()][:months]
    out = []
    for p in posts:
        pg = 0
        while True:
            d = _get(f"https://hn.algolia.com/api/v1/search_by_date?tags=comment,story_{p['objectID']}&hitsPerPage=1000&page={pg}")
            for h in d["hits"]:
                if str(h.get("parent_id")) != str(p["objectID"]) or not h.get("comment_text"): continue
                txt = html.unescape(re.sub(r"<[^>]+>", " ", h["comment_text"].replace("<p>", "\n")))
                first = txt.strip().split("\n")[0]
                if not want.search(first) or NONUS_ONLY.search(first): continue
                parts = [x.strip() for x in first.split("|")]
                m = re.search(r'href="([^"]+)"', h["comment_text"])
                hint = ENTRYHINT.search(txt)
                out.append({"title": (" | ".join(parts[1:3]) if len(parts) > 2 else first[:120])[:160], "company": parts[0][:80],
                            "location": first[:200], "url": html.unescape(m.group(1)) if m else f"https://news.ycombinator.com/item?id={h['objectID']}",
                            "posted": h.get("created_at"), "level": hint.group(0).lower() if hint else "",
                            "hn": f"https://news.ycombinator.com/item?id={h['objectID']}"})
            pg += 1
            if pg >= d["nbPages"]: break
            time.sleep(0.5)
        time.sleep(0.5)
    return out

if __name__ == "__main__":
    r = fetch_jobs(1)
    assert r and all(x["url"] and x["title"] for x in r), "empty/bad"
    print(len(r), "jobs"); [print(x) for x in r[:3]]
