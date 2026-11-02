"""Per-ATS fetchers for boards listed as slug -> ats in the watchlists. Vendors not listed here fall back to ats.py
(greenhouse/lever/ashby)."""
from . import (bamboohr, breezy, dover, gem, jazzhr, jobvite, paylocity, personio, pinpoint, recruitee, rippling,
               smartrecruiters, teamtailor, workable)

FETCHERS = {"rippling": rippling.fetch_jobs, "smartrecruiters": smartrecruiters.fetch_jobs, "workable": workable.fetch_jobs,
            "bamboohr": bamboohr.fetch_jobs, "recruitee": recruitee.fetch_jobs, "breezy": breezy.fetch_jobs,
            "personio": personio.fetch_jobs, "teamtailor": teamtailor.fetch_jobs, "gem": gem.fetch_jobs,
            "pinpoint": pinpoint.fetch_jobs, "jobvite": jobvite.fetch_jobs, "jazzhr": jazzhr.fetch_jobs,
            "paylocity": paylocity.fetch_jobs, "dover": dover.fetch_jobs}


def fetch(slug, kind):
    fn = FETCHERS.get(kind)
    if fn:
        return fn(slug)
    from . import ats
    return ats.fetch_jobs(slug, kind)
