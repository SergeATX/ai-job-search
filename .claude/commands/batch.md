Run the next job-search batch for a local profile: `/batch <profile>` (e.g. `/batch alice`). Profiles live in `profiles/<name>/` and are gitignored.

1. `python3 -m jobsearch run --profile <name>` - scrapes every configured source in parallel, drops anything already in the profile database, applies the profile's title/location/seniority filters, and writes `profiles/<name>/out/shortlist.md` and `out/fitcheck-prompt.md`. Only the short summary is printed; do not paste the shortlist into chat.
2. Spawn ONE fresh subagent (never judge fit inline) and give it the contents of `out/fitcheck-prompt.md`. It reads the candidate's resume, fetches each posting, applies only the profile's hard gates, and writes `out/fitcheck.json`.
3. `python3 -m jobsearch record --profile <name>` to store the verdicts. `python3 -m jobsearch status --profile <name>` shows counts.
4. Email the profile's `email` address only the GOOD rows and clearly-caveated WEAK rows (title, company, location, URL, one-line reason). Ask before sending if the profile has no email.
5. Report counts and any source errors to the user.

First-time setup for a person: copy `profiles.example/example/` to `profiles/<name>/`, edit `profile.yml`, and if they have an existing tracker run `python3 -m jobsearch seed --profile <name> <tracker-file>` so old postings are not resurfaced.
