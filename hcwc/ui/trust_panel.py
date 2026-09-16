"""The "how much should you trust this" panel.

Rendering only. Every judgement is in :mod:`hcwc.core.trust`, so the panel on tab 4.0 and the block in
the one-page report are the same list of checks read twice — they cannot drift apart, and neither
can be quietly softened without softening the other.
"""
from __future__ import annotations

import streamlit as st

from hcwc.core import trust
from hcwc.ui import run, theme

#: One hue per level. Green is deliberately muted: a passing check should be legible without being
#: the loudest thing on the page.
COLOUR = {"ok": "#4E8C61", "watch": "#D9822B", "stop": "#C44E52"}

LEVEL_WORD = {"ok": "clear", "watch": "needs a sentence", "stop": "not ready to quote"}


def _row(check: trust.Check) -> str:
    colour = COLOUR[check.level]
    return (
        f"<div style='border-left:4px solid {colour};background:{theme.rgba(colour, 0.07)};"
        f"padding:0.5rem 0.8rem;margin:0.35rem 0;border-radius:0 4px 4px 0'>"
        f"<div style='font-weight:700;color:{theme.shade_hex(colour, -0.35)};font-size:0.92rem'>"
        f"{check.icon}&nbsp; {check.name}"
        f"<span style='float:right;font-weight:600;opacity:0.75;font-size:0.8rem'>"
        f"{LEVEL_WORD[check.level]}</span></div>"
        f"<div style='margin-top:0.25rem;font-size:0.9rem'>{_md(check.finding)}</div>"
        f"<div style='margin-top:0.15rem;font-size:0.85rem;opacity:0.8'>{_md(check.meaning)}</div>"
        f"</div>"
    )


def _md(text: str) -> str:
    """The little of Markdown these sentences use, since the rows are raw HTML.

    Bold, italic and code spans. Anything richer belongs in the caption below the panel, not inside
    a finding — a finding that needs a list is two findings.

    Code spans were added when the assessment-minimum check started writing ``P(column ≥ h | G)``
    in backticks: unhandled, a card that now stands where tab 4.0's headline number used to be was
    printing the backticks themselves.
    """
    out = []
    for i, part in enumerate(text.split("**")):
        out.append(part if i % 2 == 0 else f"<b>{part}</b>")
    text = "".join(out)
    out = []
    for i, part in enumerate(text.split("*")):
        out.append(part if i % 2 == 0 else f"<i>{part}</i>")
    text = "".join(out)
    out = []
    for i, part in enumerate(text.split("`")):
        out.append(part if i % 2 == 0
                   else f"<code style='font-size:0.92em;padding:0 0.15em'>{part}</code>")
    return "".join(out)


def stop_card(check: trust.Check) -> None:
    """One check, on its own, where a headline number would otherwise be.

    Used by tab 4.0 when the assessment minimum is still zero: the chance it would print there is
    1.0 by construction, so the check goes in its place rather than five sections below it. Same
    renderer as the panel, so the wording cannot diverge between the two places it appears.
    """
    st.markdown(_row(check), unsafe_allow_html=True)


def render(n, result, *, posterior=None, tab: int,
           heading: str = "8 · Run checks") -> list:
    """Draw the panel and return the checks, so a caller can reuse them without recomputing."""
    checks = trust.review(result, posterior=posterior, other=run.repeat_of(result))
    level, sentence = trust.headline(checks)

    theme.heading(tab, heading, sub=n.sub)
    st.markdown(
        f"<div style='background:{theme.rgba(COLOUR[level], 0.14)};border:1px solid "
        f"{theme.rgba(COLOUR[level], 0.45)};border-radius:5px;padding:0.6rem 0.9rem;"
        f"font-size:0.95rem'><b style='color:{theme.shade_hex(COLOUR[level], -0.4)}'>"
        f"{trust.ICONS[level]}&nbsp; {sentence}</b></div>",
        unsafe_allow_html=True)
    st.markdown("".join(_row(c) for c in checks), unsafe_allow_html=True)

    st.caption(
        "These checks concern the arithmetic, not the geology; the geological check is tab 6.0. "
        "A watch is not a defect: the number needs a sentence beside it when it travels. "
        "Method: see 8.1.8."
    )
    if posterior is None:
        st.caption("The DHI check is not run because no posterior has been built. It appears "
                   "once tab 5.0 has one; absent rather than passing, because a check that did "
                   "not run is not a check that passed.")
    return checks
