"""Where the repository's files are, for the modules that read them (18 Sep 2026)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PAPER = ROOT / "paper"
REFERENCE = ROOT / "reference"
