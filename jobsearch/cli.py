import argparse
import json
from pathlib import Path

from .profile import PROFILES_DIR, Profile
from .store import Store


def main():
    ap = argparse.ArgumentParser(prog="jobsearch")
    ap.add_argument("--profiles-dir", help="where profiles/databases/outputs live (default: $JOBSEARCH_PROFILES, else ./profiles in the repo)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="scrape all configured sources for a profile and write a shortlist")
    r.add_argument("--profile", required=True)
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--workers", type=int, default=24, help="parallel fetches (default 24)")
    s = sub.add_parser("seed", help="mark every URL in an existing tracker file as already seen")
    s.add_argument("--profile", required=True)
    s.add_argument("file")
    rec = sub.add_parser("record", help="load fit-check verdicts (fitcheck.json) into the profile database")
    rec.add_argument("--profile", required=True)
    rec.add_argument("file", nargs="?")
    ps = sub.add_parser("prescreen", help="fetch candidate postings and auto-reject explicit years/clearance/grad-degree gates")
    ps.add_argument("--profile", required=True)
    ps.add_argument("--limit", type=int)
    ps.add_argument("--max-queue", type=int, default=250, help="cap on postings handed to the fit-check agent")
    st = sub.add_parser("status", help="counts by status")
    st.add_argument("--profile", required=True)
    d = sub.add_parser("discover", help="grow the employer registry from posting URLs (probes each new board live)")
    d.add_argument("--from", dest="src", nargs="+", default=["simplify-all"],
                   help="URL lists to mine: simplify-all simplify-internships speedyapply vanshb03 (or 'all')")
    d.add_argument("--dry-run", action="store_true")
    d.add_argument("--yc", action="store_true", help="also probe slugs of YC companies that are hiring (yc-oss API)")
    d.add_argument("--names-file", help="text file, one company name per line, to probe by slug (keep personal lists local)")
    sub.add_parser("profiles", help="list local profiles")
    a = ap.parse_args()

    if a.cmd == "profiles":
        base = Path(a.profiles_dir).expanduser() if a.profiles_dir else PROFILES_DIR
        for d in sorted(base.glob("*/profile.yml")):
            print(d.parent.name)
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
    p = Profile(a.profile, a.profiles_dir)
    if a.cmd == "run":
        from .runner import run
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
        for r in rows:
            s.record(r["url"], r["verdict"], r.get("reason", ""))
        print(f"recorded {len(rows)} verdicts")
    elif a.cmd == "status":
        for k, v in Store(p.db_path).counts():
            print(f"{k}: {v}")
