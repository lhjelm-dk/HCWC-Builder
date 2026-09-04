"""One page, for a well proposal.

Everything this tool produces is a CSV or a screenshot, and neither travels. A well proposal needs
the inputs, the answer, the diagnostic that says which limit produced the answer, the checks that
say whether the answer is supported, and the provenance that lets someone rebuild it — on one sheet
of paper, in the order a reader will want them.

**Why the figures are hand-drawn here rather than exported from Plotly.** A screen figure is 600 px
tall with a legend below it and hover text nobody can print; the same information at report size is
a different figure, not a scaled one. Drawing them as plain SVG also removes an image-export
dependency from the one code path most likely to be run on a locked-down machine, and prints at the
printer's resolution rather than the screenshot's. The *numbers* come from the same
:class:`~hcwc.core.engine.EngineResult` as the screen, which is the guarantee that matters.

The output is a self-contained HTML file: no external stylesheet, no font download, no script. Open
it and print to PDF. It carries an ``@page`` rule for A4 and a print stylesheet that drops the page
background, so it comes out of a printer looking like a document rather than a web page.
"""
from __future__ import annotations

import base64 as _b64
import datetime as _dt
import html
from dataclasses import dataclass

import numpy as np

from hcwc.core.engine import EngineResult
from hcwc.core.limits import DEPTH

#: The basis, spelled the way it must appear on paper. A reader of a bare page cannot recover
#: whether a DHI was folded in, and the whole tool is arranged around not letting the two be
#: confused, so it is in the header band and again in the provenance line.
BASIS_LABEL = {"geological": "GEOLOGICAL", "given_dhi": "GIVEN DHI"}
BASIS_COLOUR = {"geological": "#4C72B0", "given_dhi": "#8C5FA8"}

#: Any inline HTML tag. See :func:`_markdownish`.
_TAG = __import__("re").compile(r"<[^>]+>")

LEVEL_COLOUR = {"ok": "#4E8C61", "watch": "#D9822B", "stop": "#C44E52"}

_CSS = """
@page { size: A4 portrait; margin: 14mm 13mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 9.2pt;
       line-height: 1.35; color: #1c2128; margin: 0; background: #f4f5f7; }
.sheet { width: 200mm; min-height: 287mm; margin: 6mm auto; padding: 12mm 12mm 8mm;
         background: #fff; box-shadow: 0 1px 6px rgba(0,0,0,0.18); }
h1 { font-size: 16pt; margin: 0 0 1mm; }
h2 { font-size: 10pt; margin: 5mm 0 1.5mm; text-transform: uppercase; letter-spacing: 0.06em;
     color: #55606e; border-bottom: 1px solid #d7dbe0; padding-bottom: 1mm; }
.sub { color: #55606e; font-size: 8.6pt; margin: 0; }
.chip { display: inline-block; padding: 0.4mm 2mm; border-radius: 2px; font-weight: 700;
        font-size: 8pt; letter-spacing: 0.04em; color: #fff; }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 6mm; }
.metrics { display: flex; gap: 3mm; margin: 3mm 0 0; }
.metric { flex: 1; border: 1px solid #d7dbe0; border-radius: 3px; padding: 2mm 2.5mm; }
.metric .k { font-size: 7.6pt; color: #55606e; text-transform: uppercase;
             letter-spacing: 0.04em; }
.metric .v { font-size: 14pt; font-weight: 700; line-height: 1.1; }
.metric .n { font-size: 7.4pt; color: #6b7684; }
.cols { display: flex; gap: 4mm; align-items: flex-start; }
/* `min-width:0` is what stops a flex item refusing to shrink below its content's intrinsic
   width. Without it the two SVG panels held their natural pixel width, the row grew past the
   sheet and the right margin was eaten -- which is what Lars saw. The SVGs scale by viewBox. */
.cols > div { flex: 1 1 0; min-width: 0; }
.cols svg { width: 100%; height: auto; display: block; }
table { width: 100%; border-collapse: collapse; font-size: 8.4pt; table-layout: fixed; }
td, th { overflow-wrap: anywhere; }
th { text-align: left; font-weight: 700; color: #55606e; border-bottom: 1px solid #d7dbe0;
     padding: 1mm 1.5mm; }
td { padding: 0.9mm 1.5mm; border-bottom: 1px solid #eef0f3; vertical-align: top; }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
.check { border-left: 3px solid #ccc; padding: 1mm 2mm; margin: 1.2mm 0; font-size: 8.4pt; }
.check b { display: block; }
.check span { color: #55606e; }
.note { font-size: 8pt; color: #55606e; margin-top: 2mm; }
.prov { margin-top: 5mm; border-top: 1px solid #d7dbe0; padding-top: 2mm; font-size: 7.6pt;
        color: #6b7684; }
@media print {
  body { background: #fff; }
  .sheet { box-shadow: none; margin: 0; width: auto; min-height: 0; padding: 0; }
}
"""


@dataclass(frozen=True)
class Provenance:
    """What a reader needs to rebuild this page, and nothing else.

    Kept as a value rather than read from session state so the report function is testable and so
    the same page can be produced from a saved ``.hcwc.json`` without a browser.
    """

    prospect: str
    basis: str
    trials: int
    seed: int
    tool_version: str = ""
    source_file: str = ""
    author: str = ""


def _e(text) -> str:
    return html.escape(str(text))


def _svg_exceedance(result: EngineResult, *, width: int = 380, height: int = 230) -> str:
    """The exceedance curve, at report size, on the tool's own axis convention.

    Depth downward on y, probability on x, and the assessment minimum drawn as the horizontal line
    it is — because the single most misread thing about this curve is that POS is a point on it
    rather than a number beside it.
    """
    contacts = result.contact_m[result.above_minimum]
    if contacts.size < 2:
        return "<p class='note'>Too few successful realisations to draw a curve.</p>"

    pad_l, pad_r, pad_t, pad_b = 40, 8, 8, 26
    apex = float(np.percentile(result.apex_m, 50))
    minimum_depth = apex + float(result.limit_set.min_column_m)
    y_lo = min(apex, float(np.percentile(contacts, 0.5)))
    y_hi = max(minimum_depth, float(np.percentile(contacts, 99.5)))
    if y_hi <= y_lo:
        y_hi = y_lo + 1.0

    grid = np.linspace(y_lo, y_hi, 160)
    f = result.exceedance(grid - apex)

    def px(p: float) -> float:
        return pad_l + p * (width - pad_l - pad_r)

    def py(depth: float) -> float:
        return pad_t + (depth - y_lo) / (y_hi - y_lo) * (height - pad_t - pad_b)

    path = " ".join(f"{'M' if i == 0 else 'L'}{px(float(p)):.1f},{py(float(d)):.1f}"
                    for i, (p, d) in enumerate(zip(f, grid)))

    ticks = []
    for depth in np.linspace(y_lo, y_hi, 5):
        ticks.append(
            f"<line x1='{pad_l}' y1='{py(depth):.1f}' x2='{width - pad_r}' y2='{py(depth):.1f}' "
            f"stroke='#eef0f3'/>"
            f"<text x='{pad_l - 4}' y='{py(depth) + 3:.1f}' font-size='7' fill='#6b7684' "
            f"text-anchor='end'>{depth:,.0f}</text>")
    for p in (0.0, 0.25, 0.5, 0.75, 1.0):
        ticks.append(
            f"<text x='{px(p):.1f}' y='{height - 14}' font-size='7' fill='#6b7684' "
            f"text-anchor='middle'>{p * 100:.0f}</text>")

    pos = result.pos
    marker = (
        f"<line x1='{pad_l}' y1='{py(minimum_depth):.1f}' x2='{width - pad_r}' "
        f"y2='{py(minimum_depth):.1f}' stroke='#C44E52' stroke-width='1' "
        f"stroke-dasharray='3 2'/>"
        f"<circle cx='{px(pos):.1f}' cy='{py(minimum_depth):.1f}' r='2.8' fill='#C44E52'/>"
        f"<text x='{px(pos) + 5:.1f}' y='{py(minimum_depth) - 4:.1f}' font-size='7.2' "
        f"fill='#8A2F33' font-weight='700'>{pos:.1%} conditional, at the minimum</text>")

    return (
        f"<svg viewBox='0 0 {width} {height}' preserveAspectRatio='xMidYMid meet' "
        f"xmlns='http://www.w3.org/2000/svg'>"
        f"{''.join(ticks)}"
        f"<path d='{path}' fill='none' stroke='#2F5D8C' stroke-width='1.8'/>"
        f"{marker}"
        f"<text x='{pad_l + (width - pad_l - pad_r) / 2:.0f}' y='{height - 3}' font-size='7.4' "
        f"fill='#55606e' text-anchor='middle'>P(contact at least this deep), %</text>"
        f"<text x='9' y='{pad_t + 8}' font-size='7.4' fill='#55606e'>m TVDSS</text>"
        f"</svg>")


def _svg_control(result: EngineResult, colours: dict[str, str] | None = None,
                 *, width: int = 380, height: int = 230) -> str:
    """Controlling shares as horizontal bars, successes only.

    Successes only because the reader of this page is reading a contact distribution that is itself
    conditioned on success, and putting the unconditional share beside it would be two different
    denominators on one sheet. The unconditional view stays on tab 4.0, where there is room to explain
    the difference.
    """
    shares = result.controlling_shares(successes_only=True)
    rows = sorted(shares.items(), key=lambda kv: -kv[1])[:8]
    if not rows or rows[0][1] == 0:
        return "<p class='note'>No limit controlled a successful realisation.</p>"

    colours = colours or {}
    pad_l, pad_r, pad_t = 118, 30, 6
    step = min(22.0, (height - pad_t - 6) / len(rows))
    bar = step * 0.62
    span = width - pad_l - pad_r
    top = max(rows[0][1], 0.01)

    parts = []
    for i, (name, share) in enumerate(rows):
        y = pad_t + i * step
        w = share / top * span
        colour = colours.get(name, "#7d8794")
        label = name if len(name) <= 24 else name[:23] + "…"
        parts.append(
            f"<text x='{pad_l - 5}' y='{y + bar * 0.78:.1f}' font-size='7.4' fill='#1c2128' "
            f"text-anchor='end'>{_e(label)}</text>"
            f"<rect x='{pad_l}' y='{y:.1f}' width='{max(w, 0.6):.1f}' height='{bar:.1f}' "
            f"fill='{colour}' rx='1'/>"
            f"<text x='{pad_l + max(w, 0.6) + 4:.1f}' y='{y + bar * 0.78:.1f}' font-size='7.2' "
            f"fill='#55606e'>{share:.0%}</text>")

    return (f"<svg viewBox='0 0 {width} {height}' preserveAspectRatio='xMidYMid meet' "
            f"xmlns='http://www.w3.org/2000/svg'>{''.join(parts)}</svg>")


def _limit_rows(result: EngineResult) -> str:
    shares = result.controlling_shares(successes_only=True)
    out = []
    for i, limit in enumerate(result.limit_set.limits):
        drawn = result.sampled_m[:, i]
        active = result.active[:, i]
        if active.any():
            p90, p50, p10 = (float(np.percentile(drawn[active], p)) for p in (10, 50, 90))
            spread = f"{p90:,.0f} / {p50:,.0f} / {p10:,.0f}"
        else:
            spread = "—"
        out.append(
            f"<tr><td>{_e(limit.name)}</td><td>{_e(limit.group.value)}</td>"
            f"<td class='n'>{limit.p_active:.2f}</td>"
            f"<td>{_e(limit.distribution.kind)}"
            f"{' <i>(depth)</i>' if limit.kind == DEPTH else ''}</td>"
            f"<td class='n'>{spread}</td>"
            f"<td class='n'>{shares.get(limit.name, 0.0):.0%}</td></tr>")
    return "".join(out)


def _check_rows(checks) -> str:
    if not checks:
        return ""
    return "".join(
        f"<div class='check' style='border-left-color:{LEVEL_COLOUR[c.level]}'>"
        f"<b>{c.icon} {_e(c.name)}</b>"
        f"<span>{_e(_strip(c.finding))} {_e(_strip(c.meaning))}</span></div>"
        for c in checks)


def _strip(text: str) -> str:
    """Markdown emphasis out; the report styles its own emphasis."""
    return text.replace("**", "").replace("*", "")


def build(result: EngineResult, provenance: Provenance, *, checks=(),
          p_geological: float = 1.0, colours: dict[str, str] | None = None,
          note: str = "") -> str:
    """The whole page, as a self-contained HTML string.

    ``p_geological`` is ``P(G)``, the element product from tab 2.0 — the chance the prospect works at
    all. It has to be passed in because the engine does not know it: everything the engine returns
    is conditional on the elements having worked. It defaults to 1.0 so the function still runs
    without it, and the page then says in as many words that no element risk was supplied, rather
    than printing a conditional number under an unconditional heading. That is the mistake this
    page made on its first draft and it is the one a well proposal cannot afford.
    """
    limit_set = result.limit_set
    h_min = float(limit_set.min_column_m)
    apex = float(np.percentile(result.apex_m, 50))
    contacts = result.percentiles(np.array([90.0, 50.0, 10.0]))
    columns = contacts - apex
    basis = provenance.basis if provenance.basis in BASIS_LABEL else "geological"
    stamp = _dt.datetime.now().strftime("%d %b %Y, %H:%M")
    p_geological = float(p_geological)
    prospect_pos = p_geological * result.pos

    metrics = [
        (f"Prospect POS at h ≥ {h_min:,.0f} m", f"{prospect_pos:.1%}",
         f"P(G) {p_geological:.3f} × {result.pos:.3f}"),
        (f"P(column ≥ {h_min:,.0f} m | G)", f"{result.pos:.1%}", "conditional — limits only"),
        ("Contact P90", f"{contacts[0]:,.0f} m", f"{columns[0]:,.0f} m column"),
        ("Contact P50", f"{contacts[1]:,.0f} m", f"{columns[1]:,.0f} m column"),
        ("Contact P10", f"{contacts[2]:,.0f} m", f"{columns[2]:,.0f} m column"),
    ]
    metric_html = "".join(
        f"<div class='metric'><div class='k'>{_e(k)}</div><div class='v'>{_e(v)}</div>"
        f"<div class='n'>{_e(n)}</div></div>" for k, v, n in metrics)

    prov_bits = [f"<b>{BASIS_LABEL[basis]}</b> contact distribution",
                 f"{provenance.trials:,} realisations, seed {provenance.seed}",
                 f"apex P50 {apex:,.0f} m TVDSS",
                 f"assessment minimum {h_min:,.0f} m column",
                 f"generated {stamp}"]
    if provenance.tool_version:
        prov_bits.append(f"HCWC Distribution Builder {provenance.tool_version}")
    if provenance.source_file:
        prov_bits.append(f"from {provenance.source_file}")
    if provenance.author:
        prov_bits.append(f"by {provenance.author}")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{_e(provenance.prospect)} — HCWC one-page summary</title>
<style>{_CSS}</style></head>
<body><div class="sheet">

<div class="head">
  <div>
    <h1>{_e(provenance.prospect)}</h1>
    <p class="sub">Hydrocarbon–water contact from competing limits</p>
  </div>
  <div style="text-align:right">
    <span class="chip" style="background:{BASIS_COLOUR[basis]}">{BASIS_LABEL[basis]}</span>
    <p class="sub" style="margin-top:1.5mm">{_e(stamp)}</p>
  </div>
</div>

<div class="metrics">{metric_html}</div>
<p class="note"><b>Two chances, and they are not the same number.</b>
<code>Prospect POS = P(G) × P(column ≥ h | G)</code>.
{'<b style="color:#8A2F33">No element risk was supplied, so P(G) is 1.0 and the two figures above '
 'are the same number. The prospect chance on this page is therefore the column term only, and is '
 'an overstatement.</b> ' if p_geological >= 1.0 else
 f'<code>P(G) = {p_geological:.3f}</code> is the product of the four element chances — the chance '
 f'the prospect works at all, and the number E-POS produces. '}
The second term is everything on this page: the competing limits, <b>conditional on the elements
having worked</b>. The contact percentiles are success cases only, on the same conditioning — the
distribution is the primary object and the chance multiplies it, never the other way round.</p>

<h2>The answer, and what produced it</h2>
<div class="cols">
  <div>{_svg_exceedance(result)}</div>
  <div>{_svg_control(result, colours)}
    <p class="note" style="margin-left:2mm">Share of <i>successful</i> realisations in which each
    limit set the contact. A limit that usually kills the prospect outright is under-represented
    here, because it is the most severe.</p>
  </div>
</div>

<h2>Inputs</h2>
<table>
<thead><tr><th>Limit</th><th>Element</th><th class="n">P(active)</th><th>Form</th>
<th class="n">P90 / P50 / P10 when active</th><th class="n">Controls</th></tr></thead>
<tbody>{_limit_rows(result)}</tbody>
</table>

<h2>How much to trust this run</h2>
{_check_rows(checks)}

{f'<h2>Notes</h2><p>{_e(note)}</p>' if note.strip() else ''}

<p class="prov">{' · '.join(prov_bits)}</p>
</div></body></html>
"""


# --------------------------------------------------------------------------- the full report
#
# The one-page summary above and this are different documents for different moments, and the
# difference is worth stating rather than leaving to the filenames.
#
# The **one-pager** is the thing you hand across a table. It is deliberately one sheet, its two
# charts are hand-drawn at report size, and every number on it is one somebody will quote.
#
# **This** is the working record: every figure the app actually drew, at the size it was drawn,
# with the caption that says what it means and what it cannot tell you. Nobody reads it end to
# end. It exists so that a number quoted six months later can be traced to the figure it came
# from, and so a reviewer can disagree with a specific chart rather than with the tool.

#: Vector, not raster. An SVG of a Plotly figure is a few kilobytes, prints at the printer's
#: resolution rather than the screen's, and stays legible when someone zooms into a tail — which is
#: exactly where the arguments about a column-height distribution happen.
FIGURE_FORMAT = "svg"
FIGURE_WIDTH, FIGURE_HEIGHT = 1100, 560


def _figure_block(label: str, caption: str, payload: bytes) -> str:
    """One figure and its caption, as a page-breakable unit."""
    encoded = _b64.b64encode(payload).decode("ascii")
    return (
        f"<figure class='fig'>"
        f"<img src='data:image/svg+xml;base64,{encoded}' alt='{_e(label)}'>"
        f"<figcaption><b>{_e(label)}</b> — {_markdownish(caption)}</figcaption>"
        f"</figure>"
    )


def _table_block(label: str, payload, caption: str, hide_index: bool) -> str:
    """One table and its caption, as a page-breakable unit.

    ``payload`` is whatever the sequence was handed: a dataframe from :meth:`Numbering.table`, or
    the markdown of a hand-written one from :meth:`Numbering.markdown_table`. The second is rendered
    here rather than stored as HTML, so the registry keeps what the app actually drew.
    """
    if isinstance(payload, str):
        body = _markdown_table_to_html(payload)
    else:
        # `escape=False` because several cells carry the same inline formatting the captions do --
        # a bold verdict, a chip -- and escaping them prints their source. The content is this
        # app's own, not a user's file: an imported dataset reaches a figure, never a cell here.
        body = payload.to_html(index=not hide_index, escape=False, border=0,
                               classes="tbl", justify="left")
    return (f"<figure class='fig'>{body}"
            f"<figcaption><b>{_e(label)}</b> \u2014 {_markdownish(caption)}</figcaption>"
            f"</figure>")


def _markdown_table_to_html(body: str) -> str:
    """A pipe table, as HTML. Enough Markdown for the three hand-written tables in the app.

    Same reasoning as :func:`_markdownish`: a dependency to render one construct is a dependency to
    keep up to date. Anything that is not a pipe row is passed through as a paragraph, because these
    bodies sometimes carry a sentence above the table.
    """
    rows, out, header_done = [], [], False
    for line in body.strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if line:
                out.append(f"<p>{_markdownish(line)}</p>")
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells) and cells:
            header_done = True
            continue
        tag = "th" if not header_done and not rows else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{_markdownish(c)}</{tag}>" for c in cells) + "</tr>")
    if rows:
        out.append("<table class='tbl'>" + "".join(rows) + "</table>")
    return "".join(out)


def _markdownish(text: str) -> str:
    """The bold, italic, code and paragraph breaks these captions actually use.

    Deliberately not a Markdown library: the captions use four constructs, a dependency to render
    four constructs is a dependency to keep up to date, and anything richer belongs in prose rather
    than under a figure.

    **Inline HTML is unwrapped, not escaped.** Some captions open with the GEOLOGICAL / GIVEN THE
    DHI chip from :func:`hcwc.ui.theme.basis_tag`, which is a styled ``<span>``. Escaping it printed
    ``<span style='background:rgba(...)`` in the middle of the report; dropping it would lose the
    one thing a reader of a bare figure cannot recover, which is **which distribution it is of**.
    So the tags go and their text stays.
    """
    # Tags out, then entities in: a caption carrying `&nbsp;` between the chip and the sentence
    # would otherwise be escaped a second time and print as `&amp;nbsp;`.
    text = html.unescape(_TAG.sub("", text))
    out = html.escape(text)
    for marker, tag in (("**", "b"), ("*", "i"), ("`", "code")):
        parts = out.split(marker)
        out = "".join(part if i % 2 == 0 else f"<{tag}>{part}</{tag}>"
                      for i, part in enumerate(parts))
    return out.replace("\n\n", "</p><p>")


def build_full(result: EngineResult, provenance: Provenance, figures: dict, *,
               tables: dict | None = None, checks=(), p_geological: float = 1.0, colours=None,
               note: str = "") -> tuple[str, list[str]]:
    """The working record: the one-page summary, then every exhibit with its caption.

    Returns the HTML and a list of figures that would not render, so the caller can say which are
    missing rather than shipping a document that is quietly short.

    ``figures`` is ``{label: (plotly_figure, caption)}`` and ``tables`` is
    ``{label: (payload, caption, hide_index)}`` — :data:`hcwc.ui.numbering.FIGURES_KEY` and
    :data:`hcwc.ui.numbering.TABLES_KEY` as the app fills them during a run.

    **The two are interleaved by number, not appended.** They already share one counter per tab --
    that is the whole point of the numbering scheme, so that `2.3` names exactly one thing -- and a
    document that ran every figure and then every table would put `Table 3.2` after `Figure 6.13`
    and lose the reading order the numbers exist to carry.
    """
    from hcwc.ui.numbering import figure_order

    blocks, failed = [], []
    tables = tables or {}
    for label in sorted(set(figures) | set(tables), key=figure_order):
        if label in tables:
            payload, caption, hide_index = tables[label]
            blocks.append(_table_block(label, payload, caption, hide_index))
            continue
        figure, caption = figures[label]
        try:
            payload = figure.to_image(format=FIGURE_FORMAT,
                                      width=FIGURE_WIDTH, height=FIGURE_HEIGHT)
        except Exception as exc:                        # noqa: BLE001 — reported, not raised
            failed.append(f"{label} ({type(exc).__name__})")
            continue
        blocks.append(_figure_block(label, caption, payload))

    summary = build(result, provenance, checks=checks, p_geological=p_geological,
                    colours=colours, note=note)
    # The one-pager is a complete document; splice its body in rather than rebuilding it, so the
    # two can never disagree about a number.
    body = summary.split("<body>", 1)[1].rsplit("</body>", 1)[0]

    missing = ("" if not failed else
               "<p class='note'><b>Not every figure rendered.</b> Missing: "
               + _e(", ".join(failed)) + ". They are absent rather than substituted.</p>")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{_e(provenance.prospect)} — HCWC working record</title>
<style>{_CSS}{_FULL_CSS}</style></head>
<body>
{body}
<div class="sheet">
  <h2>Every figure drawn</h2>
  <p class="note"><b>The working record, not the summary.</b> Nobody reads this end to end. It
  exists so a number quoted six months from now can be traced to the figure it came from, and so a
  reviewer can disagree with a specific chart rather than with the tool. Each caption is the one
  shown in the app, including what the figure <i>cannot</i> tell you.</p>
  {missing}
  {''.join(blocks)}
</div>
</body></html>
""", failed


#: Layout for the figure pages. Kept apart from ``_CSS`` so the one-pager is unaffected by it.
_FULL_CSS = """
.fig { margin: 0 0 7mm; padding: 0; break-inside: avoid; page-break-inside: avoid; }
.fig img { width: 100%; height: auto; display: block; border: 1px solid #e6e9ec;
           border-radius: 3px; }
.fig figcaption { font-size: 8.4pt; color: #1c2128; margin-top: 1.5mm; line-height: 1.4; }
.fig figcaption p { margin: 1mm 0 0; }
.sheet h2:first-of-type { margin-top: 0; }
"""
