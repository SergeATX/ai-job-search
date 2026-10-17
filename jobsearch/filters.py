import re

INTERN = re.compile(r"\b(intern(ship)?|co-?op)\b", re.I)


def keep(job, p):
    """Cheap, deterministic pre-filter so the LLM only sees plausible candidates."""
    title = job.get("title") or ""
    if not p.title_inc.search(title):
        return False
    if p.title_exc and p.title_exc.search(title):
        return False
    if p.exclude_internships and INTERN.search(title):
        return False
    loc = job.get("location") or ""
    if not loc:
        return bool(p.keep_unknown_location)
    return bool(p.loc_re.search(loc))
