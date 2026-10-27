import argparse
import json
from pathlib import Path

import shutil

from .profile import PROFILES_DIR, REGISTRY_FILE, ROOT, TEMPLATE_FILES, Profile, find_root, load_registry, save_registry
from .store import Store


def main():
    ap = argparse.ArgumentParser(prog="jobsearch")
    ap.add_argument("--profiles-dir", help="where profiles/databases/outputs live (default: $JOBSEARCH_PROFILES, else ./profiles in the repo)")
    ap.add_argument("--root", help="profile root folder (overrides the registry and the current-directory lookup)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="scrape all configured sources for a profile and write a shortlist")
    r.add_argument("--profile", help="profile name (default: registry lookup from the current directory, then the registry default)")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--workers", type=int, default=12, help="parallel fetches (default 12; higher triggers Workday 429s)")
    r.add_argument("--sources", help="comma-separated subset of the profile's sources to scan this time (e.g. builtin,muse,capps)")
    s = sub.add_parser("seed", help="mark every URL in an existing tracker file as already seen")
    s.add_argument("--profile", help="profile name (default: registry lookup from the current directory, then the registry default)")
    s.add_argument("file")
    rec = sub.add_parser("record", help="load fit-check verdicts (fitcheck.json) into the profile database")
    rec.add_argument("--profile", help="profile name (default: registry lookup from the current directory, then the registry default)")
    rec.add_argument("file", nargs="?")
    rec.add_argument("--skills-only", action="store_true", help="backfill missing_skills/resume from an old file without changing verdicts or statuses")
    ps = sub.add_parser("prescreen", help="fetch candidate postings and auto-reject explicit years/clearance/grad-degree gates")
    ps.add_argument("--profile", help="profile name (default: registry lookup from the current directory, then the registry default)")
    ps.add_argument("--limit", type=int)
    ps.add_argument("--max-queue", type=int, default=250, help="cap on postings handed to the fit-check agent")
    gp = sub.add_parser("gaps", help="skill-gap analysis over GOOD/WEAK jobs; --write saves skills-gap-report.md in the profile root")
    gp.add_argument("--profile", help="profile name (default: registry lookup from the current directory, then the registry default)")
    gp.add_argument("--write", action="store_true")
    gp.add_argument("--top", type=int, default=15)
    eb = sub.add_parser("email-body", help="print the email text for the latest recorded batch (jobs + gap analysis)")
    eb.add_argument("--profile", help="profile name (default: registry lookup from the current directory, then the registry default)")
    st = sub.add_parser("status", help="counts by status")
    st.add_argument("--profile", help="profile name (default: registry lookup from the current directory, then the registry default)")
    d = sub.add_parser("discover", help="grow the employer registry from posting URLs (probes each new board live)")
    d.add_argument("--from", dest="src", nargs="+", default=["simplify-all"],
                   help="URL lists to mine: simplify-all simplify-internships speedyapply vanshb03 (or 'all')")
    d.add_argument("--dry-run", action="store_true")
    d.add_argument("--yc", action="store_true", help="also probe slugs of YC companies that are hiring (yc-oss API)")
    d.add_argument("--names-file", help="text file, one company name per line, to probe by slug (keep personal lists local)")
    sub.add_parser("profiles", help="list registered and legacy profiles")
    w = sub.add_parser("where", help="print the profile root folder (use --assist for its assistant/ data folder)")
    w.add_argument("--profile")
    w.add_argument("--assist", action="store_true")
    rg = sub.add_parser("register", help="add a profile folder to the registry")
    rg.add_argument("name")
    rg.add_argument("path")
    rg.add_argument("--default", action="store_true")
    ai = sub.add_parser("assist-init", help="copy the repo templates into <root>/assistant/ (never overwrites)")
    ai.add_argument("--profile")
    a = ap.parse_args()

    def open_profile():
        """Registry/cwd lookup first; falls back to the legacy profiles/<name> layout."""
        found = find_root(a.profile, a.root)
        if found:
            return Profile(found[0], root=found[1])
        if a.profile:
            return Profile(a.profile, a.profiles_dir)
        raise SystemExit("No profile found: pass --profile NAME, run inside a profile folder, or `jobsearch register NAME PATH --default`.")

    if a.cmd == "profiles":
        reg, default = load_registry()
        for k, v in sorted(reg.items()):
            print(f"{k}\t{v}{'  (default)' if k == default else ''}")
        base = Path(a.profiles_dir).expanduser() if a.profiles_dir else PROFILES_DIR
        for d in sorted(base.glob("*/profile.yml")):
            if d.parent.name not in reg:
                print(f"{d.parent.name}\t{d.parent}  (legacy)")
        return
    if a.cmd == "register":
        reg, default = load_registry()
        path = Path(a.path).expanduser().resolve()
        if not path.is_dir():
            raise SystemExit(f"{path} is not a folder")
        reg[a.name] = path
        save_registry(reg, a.name if a.default else default)
        print(f"registered {a.name} -> {path} in {REGISTRY_FILE}")
        return
    if a.cmd in ("where", "assist-init"):
        found = find_root(a.profile, a.root)
        if not found:
            raise SystemExit("No profile found: pass --profile NAME, run inside a profile folder, or register one.")
        assist = found[1] / "assistant"
        if a.cmd == "where":
            print(assist if a.assist else found[1])
            return
        assist.mkdir(parents=True, exist_ok=True)
        for rel in TEMPLATE_FILES:
            dest = assist / Path(rel).name
            if rel == "CLAUDE.md":
                dest = assist / "CLAUDE.profile.md"
            if not dest.exists():
                shutil.copy(ROOT / rel, dest)
                print(f"created {dest}")
        return
    if a.cmd == "discover":
        from .discover import discover
        from . import lists
        urls = []
        for name in (lists.ALL if a.src == ["all"] else a.src):
            urls += lists.urls(name)
        print(discover(urls, save=not a.dry_run))
        if a.yc or a.names_file:
            from .discover import discover_names
            entries = []
            if a.yc:
                from .lists import _get
                import json as _j
                entries += [(x["name"], x.get("website")) for x in _j.loads(_get("https://yc-oss.github.io/api/companies/all.json"))
                            if x.get("isHiring") in (True, "True")]
            if a.names_file:
                entries += [(l.strip(), None) for l in Path(a.names_file).expanduser().read_text().splitlines() if l.strip()]
            print(discover_names(entries, save=not a.dry_run))
        return
    p = open_profile()
    if a.cmd == "run":
        from .runner import run
        if a.sources:
            p.cfg["sources"] = [x.strip() for x in a.sources.split(",")]
        run(p, dry_run=a.dry_run, workers=a.workers)
        if not a.dry_run:
            print(f"shortlist: {p.out_dir / 'shortlist.md'}\nfit-check prompt: {p.out_dir / 'fitcheck-prompt.md'}")
    elif a.cmd == "prescreen":
        from .prescreen import run as pre
        from .runner import write_shortlist
        s = Store(p.db_path)
        print(pre(p, s, limit=a.limit))
        pend = [dict(zip(("company", "title", "location", "source", "url"), r)) for r in s.candidates()]
        write_shortlist(p, pend)
        from .prescreen import export_queue
        total, queued = export_queue(p, s, a.max_queue)
        print(f"{len(pend)} candidates remain ({total} distinct); {queued} queued for the fit-check agent in {p.out_dir / 'fitcheck-queue.json'}")
    elif a.cmd == "seed":
        n = Store(p.db_path).seed_urls(Path(a.file).read_text())
        print(f"seeded {n} urls")
    elif a.cmd == "record":
        f = Path(a.file) if a.file else p.out_dir / "fitcheck.json"
        s = Store(p.db_path)
        rows = json.loads(f.read_text())
        if a.skills_only:
            n = sum(s.record_skills(r["url"], r["missing_skills"], r.get("resume")) for r in rows if r.get("missing_skills") is not None)
            print(f"backfilled skills on {n} jobs")
            return
        for r in rows:
            s.record(r["url"], r["verdict"], r.get("reason", ""), r.get("missing_skills"), r.get("resume"))
        print(f"recorded {len(rows)} verdicts")
        import shutil, time
        (p.out_dir / "history").mkdir(exist_ok=True)
        shutil.copy(f, p.out_dir / "history" / f"fitcheck-{time.strftime('%Y%m%d-%H%M%S')}.json")  # the next batch overwrites fitcheck.json
        (p.out_dir / "last-batch.json").write_text(json.dumps([r["url"] for r in rows]))
        if any(r["verdict"].upper() != "SKIP" and r.get("missing_skills") is None for r in rows):
            print("warning: some GOOD/WEAK rows have no missing_skills; the fit-check agent should always include it")
    elif a.cmd == "gaps":
        from .gaps import report_text
        s = Store(p.db_path)
        text, counter, n = report_text(s, p.cfg.get("skill_aliases"), a.top)
        print(text)
        if a.write and p.root:
            import time
            lines = [f"# Skill gap report ({time.strftime('%Y-%m-%d')})", "",
                     f"Generated by `jobsearch gaps --write` from {n} GOOD/WEAK jobs (each posting counted once). Overwritten on every run.", "",
                     "| Missing skill | Jobs | Share |", "|---|---|---|"]
            lines += [f"| {k} | {v} | {round(100 * v / n)}% |" for k, v in counter.most_common(40)] if n else []
            (p.root / "skills-gap-report.md").write_text("\n".join(lines) + "\n")
            print(f"wrote {p.root / 'skills-gap-report.md'}")
    elif a.cmd == "email-body":
        from .gaps import email_body
        lb = p.out_dir / "last-batch.json"
        if not lb.exists():
            raise SystemExit("No recorded batch yet: run `jobsearch record` first.")
        text, k = email_body(Store(p.db_path), json.loads(lb.read_text()), p.cfg.get("skill_aliases"))
        print(text)
        print(f"({k} jobs)", file=__import__("sys").stderr)
    elif a.cmd == "status":
        for k, v in Store(p.db_path).counts():
            print(f"{k}: {v}")
