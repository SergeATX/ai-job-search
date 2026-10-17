"""
Standalone web search client — a replacement for Claude Code's built-in
WebSearch tool, which is capped per-session (CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION,
default 200) and gets exhausted on long research sessions like this project's
employer-discovery work. This tool makes its own plain HTTP request to Bing's
public HTML search results page, so it draws from no quota Claude Code tracks.

DuckDuckGo's html/lite endpoints were tried first and rejected all requests
(both plain curl and a headless-browser/Playwright request got a hard anti-bot
block, even with full browser headers and real JS execution) — DDG appears to
IP-block automated/datacenter traffic outright. Bing's plain HTML results page
has no such block as of 2026-10 and returns real results to a simple GET with
a browser User-Agent.

Known caveat: queries with hyphenated acronyms (e.g. "H-E-B") get mangled by
Bing's non-JS query parsing and silently fall back to a near-empty/wrong
interpretation (e.g. "H-E-B" effectively became just "H") — write such names
without hyphens ("HEB") when searching. Also: the `site:`/quoted-phrase
operators that work on bing.com's JS-rendered page do NOT reliably filter
results from this plain HTML endpoint — treat results as loose keyword
matches, not exact/filtered ones, and don't expect this to out-perform the
WebFetch-the-company's-own-careers-page method already used throughout this
project for finding exact ATS subdomains; it's best used as a general-purpose,
quota-free fallback for broader lookups, not a precision tool.

Bing wraps every result URL in a tracking redirect
(https://www.bing.com/ck/a?...&u=a1<base64>&...) instead of the real URL —
this tool decodes that back to the real target URL so results are directly
usable (no extra network hop through Bing's redirector).

Usage:
    python3 web_search.py "Sabre Corporation careers myworkdayjobs.com"
    python3 web_search.py "Texas Instruments careers icims.com" --max-results 5
"""
import argparse
import base64
import json
import re
import sys
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _decode_bing_redirect(url):
    """Bing wraps results as https://www.bing.com/ck/a?...&u=a1<base64>&... — pull out
    and decode the real target URL. Falls back to the wrapped URL if the pattern
    doesn't match (e.g. an already-direct link)."""
    if "bing.com/ck/a" not in url:
        return url
    m = re.search(r"[?&]u=a1([A-Za-z0-9_-]+)", url)
    if not m:
        return url
    b64 = m.group(1).replace("-", "+").replace("_", "/")
    b64 += "=" * (-len(b64) % 4)
    try:
        return base64.b64decode(b64).decode("utf-8", errors="replace")
    except Exception:
        return url


def search(query, max_results=10):
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": query, "count": max_results})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    soup = BeautifulSoup(html, "lxml")
    results = []
    for li in soup.select("li.b_algo"):
        h2 = li.select_one("h2 a")
        if not h2 or not h2.get("href"):
            continue
        snippet_el = li.select_one(".b_caption p") or li.select_one(".b_lineclamp2")
        results.append({
            "title": h2.get_text(strip=True),
            "url": _decode_bing_redirect(h2["href"]),
            "snippet": snippet_el.get_text(strip=True) if snippet_el else None,
        })
        if len(results) >= max_results:
            break
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--max-results", type=int, default=10)
    args = ap.parse_args()

    try:
        results = search(args.query, max_results=args.max_results)
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(results, indent=2))
    print(f"\n--- {len(results)} result(s) ---", file=sys.stderr)


if __name__ == "__main__":
    main()
