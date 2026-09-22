"""The article's figure manifest: what each file is, where it came from, and the run behind it.

Written by ``scripts/export_exhibits.py`` to ``paper/figures/MANIFEST.md`` (Phase 6 of the clean-up,
18 Sep 2026). Every paper figure is reproducible code with a stated seed and inputs; the
manifest is the place a reader finds the number, the file, the caption, the source and the date
without opening the scripts.
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import re
from typing import Iterable, NamedTuple


class Entry(NamedTuple):
    figure: str          # the article's number, "Figure 2"
    file: str            # the file in paper/figures/
    source: str          # the script and the exhibit it exports, or the drawing function
    caption: str         # the app's caption, chips stripped


def strip_chips(caption: str) -> str:
    """The app's captions carry a styled basis chip; the manifest carries words."""
    text = re.sub(r"<span[^>]*>.*?</span>\s*(&nbsp;)?\s*", "", caption)
    return " ".join(text.split())


def write(path: pathlib.Path, entries: Iterable[Entry], settings: dict[str, object],
          *, script: str = "scripts/export_exhibits.py",
          title: str = "Figures and tables: manifest") -> None:
    lines = [f"# {title}", "",
             f"Written {_dt.date.today().isoformat()} by `{script}`. Every exhibit below is drawn "
             "by the app from the prospect and settings stated; rerun the script at the same "
             "settings and the files are the same.", "",
             "## The run", "", "| setting | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in settings.items()]
    lines += ["", "## The exhibits", "", "| number | file | where in the app | caption |",
              "|---|---|---|---|"]
    for e in entries:
        lines.append(f"| {e.figure} | `{e.file}` | {e.source} | {strip_chips(e.caption)} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
