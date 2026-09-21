"""The exhibit registry's keys and sort key, shared by the tabs and the report (18 Sep 2026).

Neutral on purpose: ``hcwc.io.report`` reads the registry the tabs fill and must not import
the UI to do it. ``hcwc.ui.numbering`` owns the numbering and re-exports these.
"""
from __future__ import annotations

import re

#: Where every figure drawn this run is kept as ``{label: (figure, caption)}``, so the Export tab
#: can build a document without each tab having to hand its figures anywhere. Cleared at the top of
#: each run by `Numbering.__post_init__` on the first instance created -- Streamlit reruns top to
#: bottom, so "the first Numbering of the run" is a reliable moment to reset.
#:
#: **The caption travels with the figure.** A figure without one is a picture; the captions here
#: are where the finding is stated and where the caveat lives.
FIGURES_KEY = "_figures"

#: The same, for tables: ``{label: (payload, caption)}`` where the payload is a dataframe or the
#: markdown of a hand-written table.
#:
#: **The report shipped every figure and no table.** Thirty-three figures and twenty-odd tables are
#: drawn on a run, and only the figures reached the document -- so the limits as entered, the group
#: minima, the allocation comparison and the whole benchmark section were absent from "the full
#: report". *"I want the tables."* They were never registered anywhere, which is
#: why nothing noticed.
TABLES_KEY = "_tables"


def figure_order(label: str) -> tuple:
    """Sort key for an exhibit label, so ``4.1.10a`` follows ``4.1.9a`` and ``4.1.3b`` follows
    ``4.1.3a``, with an optional ``4.1.3b.1`` between ``4.1.3b`` and ``4.1.3c``.

    Lexical order would put `4.10` between `4.1` and `4.2`, which reads as a mis-numbered document
    rather than as a sorting artefact.
    """
    digits = label.replace("Figure", "").replace("Table", "").strip()
    key: list = []
    for part in digits.split("."):
        m = re.match(r"^(\d+)([a-z]*)$", part)
        if m:
            key.append(int(m.group(1)))
            key.append(m.group(2))
        else:
            key.append(0)
            key.append(part)
    return tuple(key)
