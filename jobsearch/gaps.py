"""Skill-gap analysis: which skills the candidate lacks across GOOD/WEAK jobs, plus per-job lines for the email."""
import json
import re
from collections import Counter

# canonical skill -> regex over a lowercased raw entry (profiles can add more via `skill_aliases:` in profile.yml)
ALIASES = {
    "CI/CD": r"ci[/ -]?cd|github actions|gitlab ci|jenkins|argo ?cd|circleci|travis",
    "Docker": r"docker|container",
    "Kubernetes": r"kubernetes|\bk8s\b|helm",
    "Terraform": r"terraform|terragrunt|pulumi|infrastructure as code|\biac\b",
    "TypeScript": r"typescript|\bts\b",
    "JavaScript": r"^javascript$|^js$",
    "Node.js": r"node(\.js|js)?$",
    "Go": r"^go(lang)?$",
    "Rust": r"^rust$",
    "C#/.NET": r"c#|\.net|asp\.net",
    "C/C++": r"^c\+\+|^c/c\+\+|^c$",
    "Java/Spring": r"spring( boot)?",
    "Linux": r"linux|unix|bash",
    "AWS": r"^aws|amazon web",
    "Azure": r"azure",
    "GCP": r"gcp|google cloud",
    "Kafka": r"kafka",
    "PostgreSQL": r"postgres",
    "MongoDB": r"mongo",
    "Redis": r"redis",
    "Spark": r"spark|databricks|hadoop|hive",
    "Snowflake/dbt": r"snowflake|\bdbt\b|bigquery|redshift",
    "Airflow": r"airflow",
    "Tableau": r"tableau",
    "Power BI": r"power ?bi",
    "Excel": r"^excel|^ms excel|^microsoft excel",
    "PyTorch/TensorFlow": r"pytorch|tensorflow|\bjax\b",
    "LLM/GenAI": r"llm|langchain|langgraph|rag\b|generative|fine-?tuning|agentic",
    "Monitoring": r"datadog|prometheus|grafana|observability|splunk",
    "Angular/Vue": r"angular|vue",
    "GraphQL/gRPC": r"graphql|grpc",
    "Selenium/Test automation": r"selenium|cypress|playwright|test automation",
}
NOISE = re.compile(r"\byears?\b|\bexperience\b|on-call|likely|\bprefer", re.I)


def _entries(raw):
    """Split a raw skill string on separators while protecting names like CI/CD and C#/.NET."""
    t = re.sub(r"ci/cd", "cicd", raw, flags=re.I)
    t = re.sub(r"c#/\.net", "c# .net", t, flags=re.I)
    return [x.strip() for x in re.split(r"[/,;]| and ", t) if x.strip()]


def normalize(raw, extra=None):
    """Raw skill string -> list of canonical skill names (noise dropped; unknown skills kept as written)."""
    rules = {**ALIASES, **(extra or {})}
    out = []
    for e in _entries(str(raw)):
        if NOISE.search(e) or len(e) > 40:
            continue
        low = e.lower()
        for canon, rx in rules.items():
            if re.search(rx, low):
                out.append(canon)
                break
        else:
            out.append(e)
    return out


def tally(rows, extra=None):
    """rows from Store.gap_rows -> (Counter of skill -> distinct postings, number of distinct postings).
    A posting is (company, title); the same role posted in several locations counts once."""
    seen, c = set(), Counter()
    for company, title, _loc, _url, _verdict, skills, _resume in rows:
        key = ((company or "").lower(), (title or "").lower())
        if key in seen:
            continue
        seen.add(key)
        c.update(set(s for raw in skills for s in normalize(raw, extra)))
    return c, len(seen)


def job_skills(skills, extra=None):
    return sorted({s for raw in skills for s in normalize(raw, extra)})


def report_text(store, extra=None, top=10):
    rows = store.gap_rows()
    c, n = tally(rows, extra)
    lines = [f"Gap analysis over {n} GOOD/WEAK jobs found so far:"]
    lines += [f"  {s}: {k} jobs ({round(100 * k / n)}%)" for s, k in c.most_common(top)] if n else ["  (no skills recorded yet)"]
    return "\n".join(lines), c, n


def skipped_for_years(store):
    row = store.db.execute("SELECT COUNT(*) FROM jobs WHERE verdict='SKIP' AND (reason LIKE '%year%' OR reason LIKE '%yr%')").fetchone()
    return row[0]


def email_body(store, urls, extra=None, top=5):
    """Plain-text email for the jobs recorded in the latest batch (urls), with the running gap analysis."""
    from .store import norm
    marks = ",".join("?" * len(urls)) or "''"
    rows = store.db.execute(
        f"SELECT company,title,location,url,verdict,reason,missing_skills,resume FROM jobs WHERE url IN ({marks}) "
        f"AND verdict IN ('GOOD','WEAK') ORDER BY verdict, company", [norm(u) for u in urls]).fetchall()
    out, good = [], [r for r in rows if r[4] == "GOOD"]
    weak = [r for r in rows if r[4] == "WEAK"]
    k = 0
    for title, group in (("GOOD FITS", good), ("WEAK (apply only if you want them)", weak)):
        if not group:
            continue
        out += [title, ""]
        for co, ti, loc, url, _v, reason, ms, resume in group:
            k += 1
            miss = job_skills(json.loads(ms), extra) if ms else []
            out.append(f"{k}. {co} - {ti} ({loc})" + (f" - {resume} resume" if resume else ""))
            out.append(f"   {reason}")
            out.append(f"   Missing: {', '.join(miss) if miss else 'nothing notable'}")
            out += [f"   {url}", ""]
    batch_rows = [(co, ti, loc, url, v, json.loads(ms), rs) for co, ti, loc, url, v, _r, ms, rs in rows if ms]
    bc, bn = tally(batch_rows, extra)
    ac, an = tally(store.gap_rows(), extra)
    out += ["GAP ANALYSIS", f"Skills most often missing across all {an} GOOD/WEAK jobs so far:"]
    out += [f"  {s}: {n} jobs ({round(100 * n / an)}%){'  <- also in this batch' if s in bc else ''}" for s, n in ac.most_common(top)]
    out.append(f"Most common blocker is still posted years of experience ({skipped_for_years(store)} jobs skipped for it), which skills alone will not fix.")
    return "\n".join(out) + "\n", k


def yield_report(store, since=None, top=15):
    """Per source and per employer: how many reviewed jobs ended GOOD/WEAK vs SKIP, so low-yield sources can be dropped."""
    where, args = "WHERE verdict IS NOT NULL", []
    if since:
        where += " AND first_seen >= ?"
        args.append(since)

    def table(col, limit=None):
        sql = (f"SELECT COALESCE({col},'?'), COUNT(*), SUM(verdict='GOOD'), SUM(verdict='WEAK'), SUM(verdict='SKIP') "
               f"FROM jobs {where} GROUP BY 1 ORDER BY SUM(verdict IN ('GOOD','WEAK')) DESC, COUNT(*) DESC")
        rows = store.db.execute(sql, args).fetchall()
        return rows[:limit] if limit else rows

    def fmt(rows):
        return [f"  {name[:28]:<28} reviewed {n:>5}  GOOD {g or 0:>3}  WEAK {w or 0:>3}  SKIP {s or 0:>5}  hit-rate {round(100 * ((g or 0) + (w or 0)) / n):>2}%"
                for name, n, g, w, s in rows]

    lines = [f"Yield{' since ' + since if since else ''} (reviewed jobs only)", "", "By source:"] + fmt(table("source"))
    lines += ["", f"Top {top} employers by GOOD+WEAK:"] + fmt(table("company", top))
    zero = [r for r in table("source") if not (r[2] or 0) + (r[3] or 0)]
    if zero:
        lines += ["", "Sources with no GOOD/WEAK yet: " + ", ".join(r[0] for r in zero)]
    return "\n".join(lines)
