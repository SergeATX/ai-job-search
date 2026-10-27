Run the next job-search batch for a local profile: `/batch <profile>` (e.g. `/batch alice`). Profiles live in `profiles/<name>/` and are gitignored.

> **Profile data:** personal files are not stored in this repo. Run `jobsearch where --assist` once (if `jobsearch` is not on PATH, use `<repo>/bin/jobsearch`) and call the printed folder `<ASSIST>`; every `<ASSIST>/...` path below lives there. If it reports no profile, tell the user to run `jobsearch register NAME PATH --default` and then `jobsearch assist-init` (copies the blank templates into `<ASSIST>`). Never write personal data into this repo.


1. `python3 -m jobsearch run --profile <name>` - scrapes every configured source in parallel, drops anything already in the profile database, applies the profile's title/location/seniority filters, and writes `profiles/<name>/out/shortlist.md` and `out/fitcheck-prompt.md`. Only the short summary is printed; do not paste the shortlist into chat.
2. Spawn ONE fresh subagent (never judge fit inline) and give it the contents of `out/fitcheck-prompt.md`. It reads the candidate's resume, fetches each posting, applies only the profile's hard gates, and writes `out/fitcheck.json`.
3. `jobsearch record` stores the verdicts, each job's `missing_skills` and resume label, and archives the file under `out/history/`. `jobsearch status` shows counts.
4. `jobsearch email-body` prints the email text: the GOOD rows and caveated WEAK rows, each with its resume label and `Missing:` skills, plus a GAP ANALYSIS section (top missing skills across all GOOD/WEAK jobs so far). Email it to the profile's `email` address as-is. Ask before sending if the profile has no email. `jobsearch gaps [--write]` prints/saves the full ranking.

Fit-check rows must carry `missing_skills` (the prompt already requires it); set `resume_labels: [A, B]` in `profile.yml` to have the agent also label which resume fits.
5. Report counts and any source errors to the user.

First-time setup for a person: copy `profiles.example/example/` to `profiles/<name>/`, edit `profile.yml`, and if they have an existing tracker run `python3 -m jobsearch seed --profile <name> <tracker-file>` so old postings are not resurfaced.
