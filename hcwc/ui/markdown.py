"""Markdown with relative image links, rendered section by section (from app.py, 18 Sep 2026)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from hcwc.ui.numbering import Numbering


def render_with_figures(text: str, base: Path, demote: int = 0,
                         numbering: Numbering | None = None) -> None:
    """Render Markdown that carries relative image links.

    ``demote`` pushes every Markdown heading down that many levels (``##`` with ``demote=3``
    renders as ``#####``), capped at six, and leaves fenced code alone. A document rendered
    under a numbered sub-heading of its own must not carry headings larger than it: the theory
    notes' ``##`` sections rendered as h2 under an h4 "8.1.3", so "The construction" was larger
    than the number it sat under.

    ``st.markdown`` resolves nothing relative to the file the text came from, so
    ``![](figures/x.png)`` renders as a *broken image* rather than as an error -- the
    failure mode where the article silently loses its five figures and nobody notices.
    The document is therefore split on its own image lines and those handed to
    ``st.image``, which does take a path. Everything else passes through untouched,
    including the blockquote caption after each figure: The rule is that
    a caption is never folded or separated from what it captions.

    Split on whole lines rather than by regular expression: an image line in this document is
    always alone on its line, and a pattern with four escaped brackets in it is the kind of thing
    that survives review and then quietly matches nothing.

    **It also breaks at every top-level heading, which is damage control rather than layout.**
    A ``$...$`` or ``$$...$$`` that opens on one line and closes on the next is an unterminated
    expression to a Markdown renderer, and it swallows everything after it until the next ``$``.
    That happened: one wrapped equation in section 2 turned the rest of
    that section and all of section 3 into red LaTeX source. The wrapping is fixed and
    `TestThePaperAgreesWithTheAppItDescribes` now refuses a document that reintroduces it, but
    rendering section by section means the next one costs a section rather than the paper.
    """
    buffer: list[str] = []

    def flush() -> None:
        chunk = "\n".join(buffer).strip()
        buffer.clear()
        if chunk:
            st.markdown(chunk)

    in_fence = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if demote and not in_fence and stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            if 0 < hashes <= 6 and stripped[hashes:hashes + 1] == " ":
                line = "#" * min(6, hashes + demote) + stripped[hashes:]
                stripped = line
        if stripped.startswith("![") and stripped.endswith(")") and "](" in stripped:
            flush()
            src = stripped[stripped.index("](") + 2:-1].strip()
            alt = stripped[2:stripped.index("](")].strip()
            target = base / src
            if not target.exists():
                st.caption(f"`{src}` not found — run `scripts/post_images.py`.")
            elif numbering is not None:
                # Numbered and captioned like any exhibit, with the image's alt text as the
                # caption, so 8.1.2's workflow figure carries a number.
                numbering.image(target, alt)
            else:
                st.image(str(target), width="stretch")
            continue
        # A section boundary is a heading at the document's own top level, wherever the demotion
        # has put it: `## ` in the source, so `## ` plus `demote` hashes here.
        if not in_fence and stripped.startswith("#" * (2 + demote) + " "):
            flush()
        buffer.append(line)
    flush()
