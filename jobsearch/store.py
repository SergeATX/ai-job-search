import re
import sqlite3
import time

SCHEMA = """CREATE TABLE IF NOT EXISTS jobs(
 url TEXT PRIMARY KEY, company TEXT, title TEXT, location TEXT, source TEXT,
 first_seen TEXT, status TEXT DEFAULT 'candidate', verdict TEXT, reason TEXT)"""


def norm(u):
    return (u or "").split("?")[0].split("#")[0].rstrip("/")


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute(SCHEMA)

    def seen(self, url):
        return self.db.execute("SELECT 1 FROM jobs WHERE url=?", (norm(url),)).fetchone() is not None

    def add(self, job, status="candidate"):
        self.db.execute(
            "INSERT OR IGNORE INTO jobs(url,company,title,location,source,first_seen,status) VALUES(?,?,?,?,?,?,?)",
            (norm(job["url"]), job.get("company"), job.get("title"), job.get("location"), job.get("source"),
             time.strftime("%Y-%m-%d"), status))
        self.db.commit()

    def seed_urls(self, text):
        n = 0
        for u in set(re.findall(r"https?://[^\s|)\]>]+", text)):
            cur = self.db.execute("INSERT OR IGNORE INTO jobs(url,first_seen,status) VALUES(?,?,'logged')",
                                  (norm(u), time.strftime("%Y-%m-%d")))
            n += cur.rowcount
        self.db.commit()
        return n

    def record(self, url, verdict, reason):
        status = {"SKIP": "skipped"}.get(verdict.upper(), "new")
        self.db.execute("UPDATE jobs SET verdict=?, reason=?, status=? WHERE url=?",
                        (verdict.upper(), reason, status, norm(url)))
        self.db.commit()

    def candidates(self):
        return self.db.execute("SELECT company,title,location,source,url FROM jobs WHERE status='candidate' ORDER BY company,title").fetchall()

    def counts(self):
        return self.db.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
