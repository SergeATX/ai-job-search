"""A profile is a person's folder (the "root"), found through a local registry.

Layout inside a root (all personal, never in this repo):
  <root>/jobsearch/profile.yml, jobs.db, out/   scraper config, state, outputs
  <root>/assistant/01-candidate-profile.md ...  data for the /apply, /setup, /scrape skills
Registry: ~/.config/ai-job-search/registry.yml  ({profiles: {name: path}, default: name}).
Legacy layout (profiles/<name>/profile.yml, --profiles-dir / $JOBSEARCH_PROFILES) still works.
"""
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
# JOBSEARCH_PROFILES lets a person keep profiles/databases next to their own files instead of inside this repo
PROFILES_DIR = Path(os.environ.get("JOBSEARCH_PROFILES", ROOT / "profiles")).expanduser()
REGISTRY = Path(__file__).resolve().parent / "registry"
REGISTRY_FILE = Path(os.environ.get("JOBSEARCH_REGISTRY", "~/.config/ai-job-search/registry.yml")).expanduser()
TEMPLATE_FILES = [
    *(f".claude/skills/job-application-assistant/{n}" for n in (
        "01-candidate-profile.md", "02-behavioral-profile.md", "03-writing-style.md", "04-job-evaluation.md",
        "05-cv-templates.md", "06-cover-letter-templates.md", "07-interview-prep.md")),
    ".claude/skills/job-scraper/search-queries.md",
    "cv/main_example.tex",
    "CLAUDE.md",
]


def load_registry():
    cfg = (yaml.safe_load(REGISTRY_FILE.read_text()) or {}) if REGISTRY_FILE.exists() else {}
    return {k: Path(v).expanduser() for k, v in (cfg.get("profiles") or {}).items()}, cfg.get("default")


def save_registry(profiles, default=None):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(yaml.safe_dump({"profiles": {k: str(v) for k, v in profiles.items()}, "default": default}, sort_keys=True))


def find_root(name=None, root=None, start=None):
    """-> (name, root) or None. Order: explicit root, registry name, walk up from cwd, registry default."""
    profiles, default = load_registry()
    if root:
        root = Path(root).expanduser().resolve()
        return next((k for k, v in profiles.items() if v.resolve() == root), root.name), root
    if name:
        return (name, profiles[name]) if name in profiles else None
    cur = Path(start or os.getcwd()).resolve()
    for d in [cur, *cur.parents]:
        if (d / "jobsearch" / "profile.yml").exists():
            return next((k for k, v in profiles.items() if v.resolve() == d), d.name), d
    return (default, profiles[default]) if default in profiles else None

DEFAULTS = {
    "email": None,
    "sources": ["ats", "workday", "icims", "jibe"],
    "companies": {"include": [], "exclude": []},
    "search_text": "",
    "titles": {"include": r"engineer|developer|programmer|software|swe", "exclude": r"\b(senior|sr\.?|staff|principal|director|vp)\b", "boost": None},
    "locations": r"remote|united states|\bus\b",
    "keep_unknown_location": False,
    "exclude_internships": True,
    "gates": [],
    "fitcheck_notes": "",
    "resume": None,
    "source_options": {},
}


class Profile:
    def __init__(self, name, profiles_dir=None, root=None):
        self.name = name
        self.root = Path(root).expanduser() if root else None
        if self.root:
            self.dir = self.root / "jobsearch"
        else:
            self.dir = Path(profiles_dir).expanduser() / name if profiles_dir else PROFILES_DIR / name
        path = self.dir / "profile.yml"
        if not path.exists():
            raise SystemExit(f"No profile at {path}. Copy profiles.example/example/ to {self.dir} and edit it.")
        cfg = yaml.safe_load(path.read_text()) or {}
        self.cfg = {**DEFAULTS, **cfg}
        self.cfg["titles"] = {**DEFAULTS["titles"], **(cfg.get("titles") or {})}
        self.cfg["companies"] = {**DEFAULTS["companies"], **(cfg.get("companies") or {})}
        if self.root and self.cfg.get("resume") and not Path(self.cfg["resume"]).expanduser().is_absolute():
            self.cfg["resume"] = str(self.root / self.cfg["resume"])
        self.db_path = self.dir / "jobs.db"
        self.out_dir = self.dir / "out"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.title_inc = re.compile(self.cfg["titles"]["include"], re.I)
        self.title_exc = re.compile(self.cfg["titles"]["exclude"], re.I) if self.cfg["titles"].get("exclude") else None
        self.loc_re = re.compile(self.cfg["locations"], re.I)

    def __getattr__(self, k):
        try:
            return self.__dict__["cfg"][k]
        except KeyError:
            raise AttributeError(k)

    def company_ok(self, name):
        inc, exc = self.cfg["companies"]["include"], self.cfg["companies"]["exclude"]
        return name not in exc and (not inc or name in inc)
