import json
import re
import sqlite3
import time

SCHEMA = """CREATE TABLE IF NOT EXISTS jobs(
 url TEXT PRIMARY KEY, company TEXT, title TEXT, location TEXT, source TEXT,
 first_seen TEXT, status TEXT DEFAULT 'candidate', verdict TEXT, reason TEXT)"""
EXTRA_COLUMNS = ("jd", "prescreen", "missing_skills", "resume", "recorded_at")  # added in place so old databases keep working


def norm(u):
    return (u or "").split("?")[0].split("#")[0].rstrip("/")


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute(SCHEMA)
        have = {r[1] for r in self.db.execute("PRAGMA table_info(jobs)")}
        for c in EXTRA_COLUMNS:
            if c not in have:
                self.db.execute(f"ALTER TABLE jobs ADD COLUMN {c} TEXT")

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

    def record(self, url, verdict, reason, missing_skills=None, resume=None):
        status = {"SKIP": "skipped"}.get(verdict.upper(), "new")
        self.db.execute("UPDATE jobs SET verdict=?, reason=?, status=?, missing_skills=?, resume=?, recorded_at=? WHERE url=?",
                        (verdict.upper(), reason, status, json.dumps(missing_skills) if missing_skills is not None else None,
                         resume, time.strftime("%Y-%m-%d %H:%M:%S"), norm(url)))
        self.db.commit()

    def record_skills(self, url, missing_skills, resume=None):
        """Backfill skills/resume on an already-recorded job without touching its verdict or status."""
        cur = self.db.execute("UPDATE jobs SET missing_skills=?, resume=COALESCE(?, resume) WHERE url=?",
                              (json.dumps(missing_skills), resume, norm(url)))
        self.db.commit()
        return cur.rowcount

    def gap_rows(self):
        """GOOD/WEAK jobs that carry a skills list: (company, title, location, url, verdict, missing_skills[list], resume)."""
        rows = self.db.execute("SELECT company,title,location,url,verdict,missing_skills,resume FROM jobs "
                               "WHERE verdict IN ('GOOD','WEAK') AND missing_skills IS NOT NULL").fetchall()
        return [(*r[:5], json.loads(r[5]), r[6]) for r in rows]

    def candidates(self):
        return self.db.execute("SELECT company,title,location,source,url FROM jobs WHERE status='candidate' ORDER BY company,title").fetchall()

    def counts(self):
        return self.db.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
