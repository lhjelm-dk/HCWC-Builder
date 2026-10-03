"""The one-page methodology sheet, offered on tab 1.0 and above 8.1.1.

Two formats of one thing: `paper/cheatsheet-v2.pdf` to print and
`paper/cheatsheet-v2-standalone.html` to open in a browser. The standalone is the one served
rather than `paper/cheatsheet-v2.html`, which references `paper/figures/` beside it and shows
eighteen broken images the moment it is downloaded on its own.

Both are read through a cache: together they are about nine megabytes, and a download button
holds its bytes, so reading them on every rerun of two tabs would be the most expensive thing
either tab does.
"""
from __future__ import annotations

import streamlit as st

from hcwc.paths import PAPER

PDF = PAPER / "cheatsheet-v2.pdf"
PAGE = PAPER / "cheatsheet-v2-standalone.html"

#: The sheet on GitHub, for a reader who wants to look rather than download. The PDF renders in
#: the browser there; the HTML would be served as source, so only the PDF is linked.
ON_GITHUB = "https://github.com/lhjelm-dk/HCWC-Builder/blob/main/paper/cheatsheet-v2.pdf"


@st.cache_data(show_spinner=False)
def _bytes(path_text: str, stamp: float) -> bytes:
    """One read per file, re-read if it changes on disk. `stamp` is the key, not an argument."""
    import pathlib

    return pathlib.Path(path_text).read_bytes()


def render(*, where: str, lead: str) -> None:
    """The pointer and the two buttons.

    `where` names the tab and keeps the two tabs' widgets distinct. It is deliberately not
    called `key`: `tests/test_prospect_io.py` scans the source for `key="..."` literals to find
    widget keys the prospect file must account for, and a parameter of that name reads as one.
    """
    if not (PDF.exists() and PAGE.exists()):
        return

    st.markdown(lead)
    c1, c2, c3 = st.columns([1, 1, 1.4])
    c1.download_button(
        "The sheet (PDF)", _bytes(str(PDF), PDF.stat().st_mtime),
        "HCWC_method_cheat_sheet.pdf", "application/pdf",
        key=f"cheatsheet_pdf_{where}", width="stretch",
        help="One page, 420 × 760 mm. Prints to any large format, or scales onto A3.")
    c2.download_button(
        "The sheet (HTML)", _bytes(str(PAGE), PAGE.stat().st_mtime),
        "HCWC_method_cheat_sheet.html", "text/html",
        key=f"cheatsheet_html_{where}", width="stretch",
        help="The same page with every figure inside the file, so it opens anywhere.")
    c3.markdown(f"[Or look at it on GitHub]({ON_GITHUB})")
