"""Per-ATS fetchers for boards listed as slug -> ats in the watchlists. Vendors not listed here fall back to ats.py
(greenhouse/lever/ashby)."""
from . import (applitrack, bamboohr, breezy, dover, eightfold, gem, jazzhr, jobvite, neogov, pageup, paylocity,
               peopleadmin, personio, phenom, pinpoint, recruitee, rippling, smartrecruiters, successfactors_rmk,
               taleo, talentbrew, teamtailor, workable)

FETCHERS = {"rippling": rippling.fetch_jobs, "smartrecruiters": smartrecruiters.fetch_jobs, "workable": workable.fetch_jobs,
            "bamboohr": bamboohr.fetch_jobs, "recruitee": recruitee.fetch_jobs, "breezy": breezy.fetch_jobs,
            "personio": personio.fetch_jobs, "teamtailor": teamtailor.fetch_jobs, "gem": gem.fetch_jobs,
            "pinpoint": pinpoint.fetch_jobs, "jobvite": jobvite.fetch_jobs, "jazzhr": jazzhr.fetch_jobs,
            "paylocity": paylocity.fetch_jobs, "dover": dover.fetch_jobs,
            # slug formats: phenom/talentbrew "host|locale", eightfold "subdomain|domain", taleo "host|section",
            # sfrmk "host", neogov "agency" (or "schooljobs:agency"), peopleadmin "tenant-or-host", pageup "id", applitrack "district"
            "phenom": phenom.fetch_jobs, "eightfold": eightfold.fetch_jobs, "taleo": taleo.fetch_jobs,
            "talentbrew": talentbrew.fetch_jobs, "sfrmk": successfactors_rmk.fetch_jobs, "neogov": neogov.fetch_jobs,
            "peopleadmin": peopleadmin.fetch_jobs, "pageup": pageup.fetch_jobs, "applitrack": applitrack.fetch_jobs}


def fetch(slug, kind):
    fn = FETCHERS.get(kind)
    if fn:
        return fn(slug)
    from . import ats
    return ats.fetch_jobs(slug, kind)
