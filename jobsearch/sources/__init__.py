import gzip
import urllib.request


def get_text(url, headers=None, timeout=20):
    """GET url, asking for gzip (JazzHR sends 1/15 of the bytes, Paylocity 1/5); -> the body as text."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", **(headers or {}), "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return body.decode("utf-8", "replace")
