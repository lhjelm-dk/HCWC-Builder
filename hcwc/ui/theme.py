"""Look and feel: an academic register, and one colour per numbered tab.

Two jobs.

**The register.** Restrained type, a measure that does not run to the window edge, no dashboard
chrome. This is a tool for geoscientists reading an argument, not a status board.

**Tab colours.** Lars asked for numbered, differently coloured tabs, and specifically for the
**tab chip's background** to carry the colour rather than its text — so the strip reads as a row of
coloured chips with ordinary dark labels, not as coloured writing. Text stays at the body ink
colour throughout, which also keeps the labels legible at every tint: coloured text on a light
background fails contrast for the paler accents, a dark label on a tinted chip does not.

The colours are not decoration: each tab owns one, and the number carries it (① in the chip,
`Figure 3.2` inside it), so a reader who has scrolled a long way still knows where they are. Tints
are kept low — roughly 18 % unselected, 50 % selected — because a saturated strip would fight the
figures, which are the part that matters.

The palette is the qualitative set already used by the figures in `hcwc/ui/empirical.py`, so a tab
and the plots inside it belong to each other. It is colour-blind-safe (Okabe–Ito adjacent) and it
survives greyscale printing, because this is a tool people will put in reports.
"""
from __future__ import annotations

import re

import streamlit as st

#: Body ink. Tab labels stay this colour at every tint — see the note above on why the
#: background carries the accent and the text does not.
INK = "#1E1B16"

#: Tab number -> (accent colour, human name). Order is the tab order.
#:
#: **Eight, because ten did not fit.** The docstring on :func:`tab_labels` has warned since the
#: strip was built that "at eight tabs the strip starts to scroll horizontally, and a tab you have
#: to scroll to find is a tab nobody uses". It reached ten, and ⑧ Theory was measurably off-screen
#: at 1478 px — the documents tab, unreachable without a horizontal scroll nobody thinks to try.
#: So the contact distribution and its depth decomposition are now sub-tabs of one Results tab
#: (they are two readings of one run), and the DHI pair is the same merge one step warmer.
#:
#: The DHI tab stays present when the prospect has no DHI. Tab numbers key the figure numbering
#: and the positional CSS, so a strip that changed length would renumber every figure on it — and
#: a tab that appears and disappears teaches the user nothing about what it is for.
TAB_COLOURS: dict[int, tuple[str, str]] = {
    1: ("#4C72B0", "Concept"),
    2: ("#DD8452", "Prospect"),
    3: ("#E8A87C", "HCWC limiters"),
    4: ("#64B5CD", "Results"),
    5: ("#3E8FA3", "Results | DHI"),
    6: ("#55A868", "Empirical"),
    7: ("#8172B2", "Export"),
    8: ("#937860", "Theory"),
}


def tab_labels() -> list[str]:
    """The numbered labels, in order.

    Numerals are glyphs rather than styled text so the number cannot wrap off, and the names are
    kept short: at eight tabs the strip starts to scroll horizontally, and a tab you have to scroll
    to find is a tab nobody uses.
    """
    # Derived, not typed. This was a literal map and the tab-merge rename walked straight
    # through it, turning tab 5's numeral into a second ④ -- the one place in the app where a
    # circled digit is an *index* rather than a cross-reference, so a blanket substitution
    # over prose corrupted it silently. Computed from the key, it cannot drift again.
    def numeral(i: int) -> str:
        return chr(0x245F + i) if 1 <= i <= 20 else str(i)

    return [f"{numeral(i)}  {name}" for i, (_, name) in sorted(TAB_COLOURS.items())]


def _tab_css() -> str:
    """Per-tab accent.

    Streamlit gives tabs no stable, documented hook, and the DOM it emits has changed shape at
    least once: older builds render ``[data-baseweb="tab-list"] > button``, current ones render
    ``[role="tablist"] > div[data-testid="stTab"][data-key="N"]`` with no baseweb attributes at all.
    Both are targeted, because guessing which one a given deployment ships is not a thing worth
    doing at runtime — the unmatched rules cost nothing.

    ``data-key`` is preferred over ``nth-child`` where it exists: it survives Streamlit inserting a
    wrapper element, which ``nth-child`` does not. Note it is **0-indexed** while the tab numbers
    here are 1-indexed.

    The failure mode is deliberately harmless. If every selector stops matching, the tabs render in
    Streamlit's default style and nothing else breaks — the numerals in the labels carry the
    ordering on their own, so the app stays usable and navigable with none of this applied.
    """
    # Scoped to the *top-level* strip only. Nested tabs — tab ③'s Charge / Closure / Retention /
    # Correlations — are also a `[role="tablist"]` with keys starting at 0, so an unscoped rule
    # painted them with the main palette by position: Charge came out Concept-blue and Closure
    # Prospect-orange, which is exactly the wrong signal on a tab organised by risk element.
    # `:has()` identifies the strip by its own length rather than by where it sits in the DOM.
    main = f'[role="tablist"]:has([data-testid="stTab"][data-key="{len(TAB_COLOURS) - 1}"])'
    rules = []
    for i, (colour, _) in sorted(TAB_COLOURS.items()):
        current = f'{main} [data-testid="stTab"][data-key="{i - 1}"]'
        legacy = f'.stTabs [data-baseweb="tab-list"] button:nth-child({i})'
        rules.append(
            f"""
      {current}, {legacy} {{
          background: {colour}2E !important;
          color: {INK} !important;
          border-bottom: 3px solid transparent;
      }}
      {current}:hover, {legacy}:hover {{
          background: {colour}4D !important;
      }}
      {current}[aria-selected="true"], {current}[data-selected="true"],
      {legacy}[aria-selected="true"] {{
          background: {colour}80 !important;
          color: {INK} !important;
          border-bottom: 3px solid {colour} !important;
      }}"""
        )
    return "\n".join(rules)


#: Tab ③'s sub-tabs, in order, and the risk element whose colour each takes. ``None`` is the
#: Correlations sub-tab, which belongs to no single element and stays neutral.
SUBTAB_ELEMENTS: tuple[str | None, ...] = ("Charge", "Closure", "Retention", None)

#: How many sub-tabs each tab has, for the tabs whose sub-strips take their parent's accent rather
#: than element colours. Their sub-tabs are *views of one thing* — the contact and its
#: decomposition, the four steps of the DHI — so they share a hue and differ only in lightness.
ACCENT_SUBTABS: dict[int, int] = {4: 2, 5: 4}


def subtab_marker(tab: int) -> str:
    """A hidden span naming which tab a sub-strip belongs to.

    Rendered inside each sub-tab's body, where `:has()` can reach it: the tablist and the panels
    are siblings under one container, so ``div:has(> [role=tabpanel] .hcwc-sub-5) > [role=tablist]``
    selects exactly that strip. Streamlit mounts only the *active* panel, which is why every
    sub-tab needs one rather than just the first.
    """
    # A zero-width space rather than nothing: the markdown renderer drops an element with no
    # content, and hiding it inline would need the same attribute the sanitiser is most likely to
    # strip. So it carries a character and the stylesheet hides it.
    return f"<span class='hcwc-sub-{tab}'>​</span>"


def _strip(tab: int) -> str:
    """The selector for one tab's sub-strip, via the marker its bodies carry."""
    return (f'div:has(> [role="tabpanel"] .hcwc-sub-{tab}) > [role="tablist"]')


def _subtab_rules(selector: str, colours: list[str]) -> list[str]:
    rules = []
    for index, colour in enumerate(colours):
        target = f'{selector} [data-testid="stTab"][data-key="{index}"]'
        rules.append(
            f"""
      {target} {{
          background: {colour}30 !important;
          color: {INK} !important;
          border-bottom: 3px solid transparent;
      }}
      {target}:hover {{background: {colour}55 !important;}}
      {target}[aria-selected="true"], {target}[data-selected="true"] {{
          background: {colour}8A !important;
          border-bottom: 3px solid {shade_hex(colour, -0.35)} !important;
      }}"""
        )
    return rules


def _subtab_css() -> str:
    """Sub-strip colours, one tab at a time, each claimed by its own marker."""
    claimed = [3, *ACCENT_SUBTABS]
    hide = ", ".join(f".hcwc-sub-{tab}" for tab in claimed)
    rules: list[str] = [f"\n      {hide} {{display: none !important;}}"]
    rules += _subtab_rules(
        _strip(3),
        [PILLAR_COLOURS[element] if element else "#B9B2A6" for element in SUBTAB_ELEMENTS])
    for tab, count in ACCENT_SUBTABS.items():
        base = TAB_COLOURS[tab][0]
        # Lightest first, so the strip reads left-to-right as the reading order does. All one hue:
        # these sub-tabs are views of one thing and should not look like four different subjects.
        steps = [0.42] if count == 1 else [0.42 - 0.52 * i / (count - 1) for i in range(count)]
        rules += _subtab_rules(_strip(tab), [shade_hex(base, step) for step in steps])
    return "\n".join(rules)


def apply() -> None:
    """Inject the stylesheet. Call once, immediately after ``st.set_page_config``."""
    st.markdown(
        f"""
    <style>
      .block-container {{padding-top: 2.2rem; max-width: 1180px;}}
      h1, h2, h3 {{font-weight: 600; letter-spacing: -0.01em;}}
      blockquote {{border-left: 3px solid #cfcfcf; color: inherit;}}

      /* Captions carry the figure and table numbers, so they need to read as
         labels rather than as afterthoughts. */
      .stCaption, [data-testid="stCaptionContainer"] {{font-size: 0.86rem;}}

      [role="tablist"], .stTabs [data-baseweb="tab-list"] {{
          gap: 0.15rem;
          border-bottom: 1px solid #e6e6e6;
      }}
      [data-testid="stTab"], .stTabs [data-baseweb="tab"] {{
          font-size: 0.93rem;
          font-weight: 600;
          padding: 0.55rem 1.05rem;
          border-radius: 6px 6px 0 0;
      }}
      /* Streamlit's own sliding underline would sit in one colour under all five. */
      .stTabs [data-baseweb="tab-highlight"],
      [role="tablist"] [data-testid="stTabHighlight"] {{background: transparent !important;}}
{_tab_css()}
{_subtab_css()}
    </style>
    """,
        unsafe_allow_html=True,
    )


def accent(tab: int) -> str:
    """The accent colour for a tab, so a heading inside it can match its own tab."""
    return TAB_COLOURS[tab][0]


#: A leading section number, in the form the tabs write it: ``"1 · Geometry"``.
_SECTION = re.compile(r"^(\d+)\s*·\s*(.*)$", re.DOTALL)


def section_label(tab: int, text: str, sub: int | None = None) -> str:
    """``"4 · How it is arranged"`` on tab ① becomes ``"1.4 How it is arranged"``.

    Split out of :func:`heading` because tab ① carries three of its sections in *expanders*, whose
    labels never went through the heading path — so they rendered as a bare "4 ·" under headings
    numbered 1.1, 1.2, 1.3, and a reader met the numbering scheme broken on the first page of the
    app. One function now, used by both.
    """
    stem = f"{tab}" if sub is None else f"{tab}.{sub}"
    match = _SECTION.match(text)
    return f"{stem}.{match.group(1)} {match.group(2)}" if match else text


def heading(tab: int, text: str, sub: int | None = None) -> None:
    """A section heading in the tab's own colour, tying the content to the tab strip.

    **The section number carries its tab, and its sub-tab where there is one.** With ``sub``, a
    heading written as ``"1 · What was observed"`` renders as **5.2.1** on tab ⑤'s second sub-tab,
    matching ``Figure 5.2.1`` beneath it — so a number says which page as well as which item.

    **The section number carries its tab.** A heading written as ``"1 · Geometry"`` renders as
    **2.1 Geometry** on tab ②, matching ``Figure 2.1`` and ``Table 2.3`` below it. Before this, a
    reader looking at "1 · Geometry" beside "Figure 2.1" had two numbering schemes on one screen
    and no way to tell that the first was a section and the second a figure.

    Composed here rather than typed into each call so the two can never disagree, and so a tab that
    moves renumbers its own sections — which is exactly what the ten-to-eight merge did to the
    depth-risk sections.
    """
    label = section_label(tab, text, sub)
    st.markdown(
        f"<h3 style='color:{accent(tab)};margin-top:1.2rem'>{label}</h3>",
        unsafe_allow_html=True,
    )


#: The two things a contact distribution can be, and the colour each carries everywhere.
#: Kept as constants rather than bare strings because they end up in filenames, in provenance
#: lines inside exported files, and in figure captions — and those three must never disagree.
GEOLOGICAL, GIVEN_DHI = "geological", "given the DHI"
BASIS_COLOUR = {GEOLOGICAL: "#4C72B0", GIVEN_DHI: "#C44E52"}


def basis_banner(basis: str, detail: str = "") -> None:
    """A strip naming which contact distribution everything below it is built from.

    Lars, 27 Aug 2026: *"I need better assurance that what I see in terms of HCWC distribution is a
    geological HCWC or a HCWC | DHI."* The honest fix is not a footnote. A tab either shows the
    geological model or the updated one, and the answer belongs at the top in a colour, before any
    figure, because a reader who has scrolled to Figure 7.2 will not scroll back to check.
    """
    colour = BASIS_COLOUR[basis]
    st.markdown(
        f"<div style='background:{rgba(colour, 0.13)};border-left:6px solid {colour};"
        f"padding:0.5rem 0.8rem;margin:0.2rem 0 1rem 0;border-radius:3px'>"
        f"<b style='color:{shade_hex(colour, -0.45)}'>Everything on this tab is the "
        f"{basis.upper()} contact distribution.</b>"
        + (f"<div style='font-size:0.88rem;opacity:0.85;margin-top:0.15rem'>{detail}</div>"
           if detail else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def basis_tag(basis: str) -> str:
    """An inline chip for a caption, where a whole banner would be noise."""
    colour = BASIS_COLOUR[basis]
    return (f"<span style='background:{rgba(colour, 0.18)};color:{shade_hex(colour, -0.45)};"
            f"padding:0.05rem 0.4rem;border-radius:3px;font-weight:700;font-size:0.8rem'>"
            f"{basis.upper()}</span>")


def element_heading(element: str, text: str, subtitle: str = "") -> None:
    """A section heading in a **risk element's** colour rather than the tab's.

    Used on tab ③, where the sections are elements rather than steps, so the same hue that labels
    Charge on tab ② labels the Charge sub-tab here. The rule Lars set on 25 Aug 2026 still holds
    one level down: the *element* gets the pure hue, and each individual limit inside it gets a
    variation of it, so the grouping is readable without the two levels competing.
    """
    colour = PILLAR_COLOURS[element]
    st.markdown(
        f"<div style='border-left:6px solid {colour};padding:0.15rem 0 0.15rem 0.7rem;"
        f"margin:0.4rem 0 0.9rem 0'>"
        f"<h3 style='color:{shade_hex(colour, -0.5)};margin:0'>{text}</h3>"
        + (f"<div style='opacity:0.75;font-size:0.9rem'>{subtitle}</div>" if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- risk-element palette
#: The four risk elements, in E-POS's own colours (`E-POS/components/colors.py::PILLAR_COLORS`).
#: Copied rather than imported: E-POS is a separate deployable app, not a library, and the two
#: repos are coupled by file contract only. If these ever drift, that file is the source of truth.
PILLAR_COLOURS: dict[str, str] = {
    "Charge": "#F69292",      # salmon
    "Closure": "#8CB7FC",     # blue
    "Reservoir": "#FFD44B",   # yellow
    "Retention": "#B5E6A2",   # green
}


def shade_hex(hex_colour: str, factor: float) -> str:
    """Lighten (``factor > 0``, towards white) or darken (``factor < 0``, towards black).

    E-POS lightens only. Darkening is needed here because a *limit* palette has to fit several
    members inside one element's hue, and the pastels are already light enough that lightening
    alone runs out of contrast after two steps.
    """
    hex_colour = hex_colour.lstrip("#")
    if len(hex_colour) != 6:
        raise ValueError(f"expected a 6-digit hex colour, got {hex_colour!r}")
    channels = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
    if factor >= 0:
        out = (int(round(c + (255 - c) * factor)) for c in channels)
    else:
        out = (int(round(c * (1.0 + factor))) for c in channels)
    return "#" + "".join(f"{max(0, min(255, c)):02X}" for c in out)


def rgba(hex_colour: str, alpha: float) -> str:
    """``#RRGGBB`` plus an alpha, as an ``rgba()`` string Plotly will accept.

    Plotly rejects 8-digit hex for ``fillcolor`` — it takes ``#RRGGBB`` but not ``#RRGGBBAA``,
    and the error names the property rather than the format, so it reads as a bad colour rather
    than a bad *encoding*. CSS takes both, which is why the mistake keeps getting made: the same
    string works in the stylesheet and fails in the figure.
    """
    hex_colour = hex_colour.lstrip("#")
    if len(hex_colour) != 6:
        raise ValueError(f"expected a 6-digit hex colour, got {hex_colour!r}")
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {max(0.0, min(1.0, alpha)):.3f})"


def element_shades(element: str, count: int) -> list[str]:
    """``count`` distinguishable variations of one element's colour.

    The rule Lars set: a limit is coloured a *variation of its element's hue* — fault leakage and
    the seals are retention mechanisms, so they are greens, but **not the retention green itself**.
    The pure pillar colour stays reserved for the element, so an element total and one of its
    limits can never be confused in a legend.

    Shades run darker to lighter across the group, skipping the base, which keeps the family
    obvious while the members stay apart.
    """
    if element not in PILLAR_COLOURS:
        raise KeyError(f"unknown risk element {element!r}; expected one of {list(PILLAR_COLOURS)}")
    if count < 1:
        return []
    base = PILLAR_COLOURS[element]
    if count == 1:
        return [shade_hex(base, -0.18)]
    lo, hi = -0.34, 0.40
    steps = [lo + (hi - lo) * i / (count - 1) for i in range(count)]
    # Nudge anything landing on the base so no limit borrows the element's own colour.
    steps = [s if abs(s) > 0.06 else (0.10 if s >= 0 else -0.10) for s in steps]
    return [shade_hex(base, s) for s in steps]
