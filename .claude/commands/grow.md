Grow the scanner's reach (new employers or new sources) for a profile: `/grow [profile]`. This is NOT a batch.

> **Profile data:** personal files are not stored in this repo. Run `jobsearch where` to find the profile folder. Never write personal data into this repo.

Rule: expand, test, commit, push - then stop. Do not run a scan, fit-check or email a batch as part of this command. Run `/batch` separately when the user asks.

1. **Look at the yield first.** `jobsearch yield` shows which sources/employers produce GOOD/WEAK jobs. Grow what works (curated lists, boards that hit), not what doesn't.
2. **Add employers.** `jobsearch discover --dry-run` first (uses the profile's `discovery:` settings: `lists`, `yc`, `names_file`), then `jobsearch discover`. A region/company names file stays in the profile folder, never in this repo.
3. **Add a source** (only if it has a stable public API or scraper): add `jobsearch/sources/<name>.py` with `fetch_jobs(**opts)` returning `[{title, company, url, location}]`, wire it in `runner._tasks`, then test it alone with `jobsearch run --dry-run --sources <name>` and check the title-pass rate.
4. **Review** `git diff --stat` (registry files are company lists only), commit, and `git push` (the pre-push privacy scan must pass; never `--no-verify`).
5. Report how many employers/sources were added and stop.

Aggregators reachable only through the assistant's own tools (Indeed, Dice, ZipRecruiter) are not scanner sources; use them for ad hoc searches and say so.
