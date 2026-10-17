"""Profiles live in profiles/<name>/profile.yml (gitignored - personal, stays local)."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT / "profiles"
REGISTRY = Path(__file__).resolve().parent / "registry"

DEFAULTS = {
    "email": None,
    "sources": ["ats", "workday", "icims", "jibe"],
    "companies": {"include": [], "exclude": []},
    "search_text": "",
    "titles": {"include": r"engineer|developer|programmer|software|swe", "exclude": r"\b(senior|sr\.?|staff|principal|director|vp)\b"},
    "locations": r"remote|united states|\bus\b",
    "keep_unknown_location": False,
    "exclude_internships": True,
    "gates": [],
    "fitcheck_notes": "",
    "resume": None,
}


class Profile:
    def __init__(self, name):
        self.name = name
        self.dir = PROFILES_DIR / name
        path = self.dir / "profile.yml"
        if not path.exists():
            raise SystemExit(f"No profile at {path}. Copy profiles.example/example/ to profiles/{name}/ and edit it.")
        cfg = yaml.safe_load(path.read_text()) or {}
        self.cfg = {**DEFAULTS, **cfg}
        self.cfg["titles"] = {**DEFAULTS["titles"], **(cfg.get("titles") or {})}
        self.cfg["companies"] = {**DEFAULTS["companies"], **(cfg.get("companies") or {})}
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
