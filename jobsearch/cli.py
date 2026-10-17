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
    s = sub.add_parser("seed", help="mark every URL in an existing tracker file as already seen")
    s.add_argument("--profile", required=True)
    s.add_argument("file")
    rec = sub.add_parser("record", help="load fit-check verdicts (fitcheck.json) into the profile database")
    rec.add_argument("--profile", required=True)
    rec.add_argument("file", nargs="?")
    st = sub.add_parser("status", help="counts by status")
    st.add_argument("--profile", required=True)
    d = sub.add_parser("discover", help="grow the employer registry from posting URLs (probes each new board live)")
    d.add_argument("--from", dest="src", choices=["simplify"], default="simplify")
    d.add_argument("--dry-run", action="store_true")
    sub.add_parser("profiles", help="list local profiles")
    a = ap.parse_args()

    if a.cmd == "profiles":
        base = Path(a.profiles_dir).expanduser() if a.profiles_dir else PROFILES_DIR
        for d in sorted(base.glob("*/profile.yml")):
            print(d.parent.name)
        return
    if a.cmd == "discover":
        from .discover import discover
        from .sources import simplify
        urls = [x.get("url") for x in simplify.fetch_listings() if x.get("active")]
        print(discover(urls, save=not a.dry_run))
        return
    p = Profile(a.profile, a.profiles_dir)
    if a.cmd == "run":
        from .runner import run
        run(p, dry_run=a.dry_run)
        if not a.dry_run:
            print(f"shortlist: {p.out_dir / 'shortlist.md'}\nfit-check prompt: {p.out_dir / 'fitcheck-prompt.md'}")
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
