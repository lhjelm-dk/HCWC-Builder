"""The workflow figure, drawn as SVG by hand, in two versions from one layout.

* ``docs/figures/fig0_workflow.svg`` -- the conceptual version for 8.1.1 and the article: the
  model as symbols and one-line concepts, no tab references.
* ``docs/figures/fig0_workflow_guide.svg`` -- the guide version for tab 1.0: the same boxes,
  each line naming the tab it lives on and what is entered or read there, so the figure is a
  map of the app (Lars, 17 Sep 2026).

Both are also rasterised to PNG beside the SVG through kaleido's Chromium, for the article and
the post, where SVG is not accepted; the PNG is the SVG as a browser draws it.

The layout is a 2 x 2 grid. Rows: the geological model, the prior, on top; the DHI evidence,
the update, below. Columns: the chance (is there an accumulation?) on the left, the contact given success
(where does the column stop?) on the right. The DHI's two channels are two short vertical
arrows, evidence strength from P(G) to P(G | strength) and contact geometry from HCWC | G to
HCWC | G, evidence, so nothing crosses a box. The rows join on the right in the chance against
depth, read at the assessment minimum and at the well; the chance reaches the join along the
outer rail of its row, the contact along the inner. The benchmarks sit dashed between the two
contact distributions, compared with both and never joined.

Vector, not raster, so it is crisp at any zoom in the app, the report and the paper. Run from
the repository root::

    python scripts/workflow_figure.py
"""
from __future__ import annotations

import base64
from pathlib import Path

FIGURES = Path(__file__).resolve().parent.parent / "docs" / "figures"

INK, MUTED, GEO, DHI, JOIN = "#333333", "#7d8794", "#4C72B0", "#C44E52", "#2F6B3F"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"

W, H = 1340, 480

#: The words that differ between the two versions. Every value is one line under a box title,
#: at most 32 characters at the 11 px the boxes use (24 in the three narrow evidence boxes),
#: or a row, lane or join title. Wording after Lars's alignment of 18 Sep 2026: the geological
#: model is the prior, the DHI is evidence; the evidence index is a relative scale, its
#: likelihood ratio updates P(G); the contact geometry updates HCWC | G; the join is the
#: probability of meeting the threshold.
CONCEPT = dict(
    file="fig0_workflow",
    row_geo="GEOLOGICAL MODEL  ·  the prior",
    row_dhi="DHI EVIDENCE  ·  the update",
    lane_chance="is an accumulation present?",
    lane_contact="given an accumulation: where does the column stop?",
    lane_strength="evidence index  ·  updates P(G)",
    lane_geometry="contact geometry  ·  updates HCWC | G",
    elements="play × conditional, per element",
    p_g="geological accumulation chance",
    limits="P(active) and a depth each",
    competition="shallowest active limit wins",
    hcwc="contact distribution, given G",
    index="relative scale, 0 neutral",
    lr="f(s|HC) / f(s|NoHC)",
    p_g_evidence="two-state update",
    geometry="pick, attribution c, D(h)",
    hcwc_post="same realisations, reweighted",
    bench_title="Empirical benchmarks",
    bench="compared with both, never joined",
    join_mid=("MEETS THE THRESHOLD?", "read at h_min, the assessment", "minimum, and at z_well"),
    join_geo=("POS(h) = P(G) × F(h)", "F(h) = P(H ≥ h | G)", "the prior chance against depth"),
    join_dhi=("P(G | evidence)", "× P(H ≥ h | G, evidence)", "the posterior POS(h)"),
)
GUIDE = dict(
    file="fig0_workflow_guide",
    row_geo="GEOLOGICAL MODEL  ·  tabs 2.0 to 4.0",
    row_dhi="DHI EVIDENCE  ·  tab 5.0",
    lane_chance="is an accumulation present?",
    lane_contact="given an accumulation: where does the column stop?",
    lane_strength="evidence index  ·  updates P(G)",
    lane_geometry="contact geometry  ·  updates HCWC | G",
    elements="2.0: element chances entered",
    p_g="2.0: accumulation chance, read",
    limits="3.0: P(active) and depth entered",
    competition="4.1.1: the draws, shown",
    hcwc="4.1: percentiles, controller read",
    index="5.1.2: entered",
    lr="5.1.2: LR(s), read",
    p_g_evidence="5.1.2: read",
    geometry="5.1.3: pick, c and D(h) entered",
    hcwc_post="5.2: contact and shares read",
    bench_title="Benchmarks  ·  6.0",
    bench="beside 4.1 and 5.2, never joined",
    join_mid=("MEETS THE THRESHOLD?", "read at h_min (2.0) and at", "the well's depth; 7.0 exports"),
    join_geo=("POS(h) = P(G) × F(h)", "F(h) = P(H ≥ h | G)", "4.1.3, 4.1.4: read; 4.2: by element"),
    join_dhi=("P(G | evidence)", "× P(H ≥ h | G, evidence)", "5.2.3, 5.2.4: read; 5.3: by element"),
)


def text(x, y, s, size=11, colour=INK, anchor="middle", weight=None):
    bold = f" font-weight='{weight}'" if weight else ""
    return (f"<text x='{x}' y='{y}' text-anchor='{anchor}' font-size='{size}' fill='{colour}'"
            f"{bold} {FONT}>{s}</text>")


def box(x, y, w, h, title, lines, colour, dashed=False, muted_from=99):
    """A rounded box with a bold title and one line beneath it; the join boxes carry two or
    three lines, those from ``muted_from`` on in grey."""
    dash = " stroke-dasharray='6 4'" if dashed else ""
    lines = [lines] if isinstance(lines, str) else list(lines)
    out = (f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='8' ry='8' fill='white' "
           f"stroke='{colour}' stroke-width='1.8'{dash}/>"
           + text(x + w / 2, y + 24, title, 14, colour, weight=600))
    for k, line in enumerate(lines):
        out += text(x + w / 2, y + 44 + 18 * k, line, 11, MUTED if k >= muted_from else INK)
    return out


def arrow(x1, y1, x2, y2, colour, dashed=False):
    dash = " stroke-dasharray='6 4'" if dashed else ""
    marker = {GEO: "geo", DHI: "dhi", MUTED: "muted"}.get(colour, "join")
    return (f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{colour}' "
            f"stroke-width='1.8'{dash} marker-end='url(#arrow-{marker})'/>")


def rail(points, colour):
    """An elbowed arrow along the outside of a row, from a box edge to the join column."""
    marker = {GEO: "geo", DHI: "dhi"}[colour]
    d = " ".join(f"{'M' if k == 0 else 'L'} {x} {y}" for k, (x, y) in enumerate(points))
    return (f"<path d='{d}' fill='none' stroke='{colour}' stroke-width='1.8' "
            f"marker-end='url(#arrow-{marker})'/>")


def lane(x, y, w, h, title, colour, fill):
    return (f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='10' ry='10' fill='{fill}' "
            f"stroke='none'/>" + text(x + 14, y + 20, title, 12, colour, "start", 600))


def draw(t: dict) -> str:
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' width='{W}' "
        f"height='{H}'>",
        "<defs>"
        + "".join(
            f"<marker id='arrow-{name}' viewBox='0 0 10 10' refX='9' refY='5' "
            f"markerWidth='8' markerHeight='8' orient='auto-start-reverse'>"
            f"<path d='M 0 0 L 10 5 L 0 10 z' fill='{c}'/></marker>"
            for name, c in (("geo", GEO), ("dhi", DHI), ("join", JOIN), ("muted", MUTED)))
        + "</defs>",
        f"<rect width='{W}' height='{H}' fill='white'/>",
    ]

    # ---- the two rows: the chance column is wider now, it holds three evidence boxes ---------
    parts.append("<rect x='20' y='20' width='1050' height='160' rx='10' ry='10' fill='#F4F5F7'/>")
    parts.append(text(34, 42, t["row_geo"], 12.5, INK, "start", 600))
    parts.append(lane(30, 58, 440, 112, t["lane_chance"], GEO, "#EEF3FA"))
    parts.append(lane(490, 58, 570, 112, t["lane_contact"], GEO, "#EEF3FA"))

    parts.append("<rect x='20' y='284' width='1050' height='176' rx='10' ry='10' fill='#F4F5F7'/>")
    parts.append(text(34, 306, t["row_dhi"], 12.5, INK, "start", 600))
    parts.append(lane(30, 322, 440, 112, t["lane_strength"], DHI, "#FBEFEF"))
    parts.append(lane(490, 322, 570, 112, t["lane_geometry"], DHI, "#FBEFEF"))

    # ---- geological row ------------------------------------------------------------------------
    parts.append(box(40, 100, 200, 60, "Element chances", t["elements"], GEO))
    parts.append(box(290, 100, 170, 60, "P(G)", t["p_g"], GEO))
    parts.append(arrow(240, 130, 290, 130, GEO))
    parts.append(box(500, 100, 170, 60, "Geological limits", t["limits"], GEO))
    parts.append(box(700, 100, 170, 60, "Competition", t["competition"], GEO))
    parts.append(box(890, 100, 170, 60, "HCWC | G", t["hcwc"], GEO))
    parts.append(arrow(670, 130, 700, 130, GEO))
    parts.append(arrow(870, 130, 890, 130, GEO))

    # ---- DHI row: index -> likelihood ratio -> P(G | evidence); geometry -> HCWC | G, evidence
    parts.append(box(40, 364, 130, 60, "Evidence index", t["index"], DHI))
    parts.append(box(190, 364, 130, 60, "Likelihood ratio", t["lr"], DHI))
    parts.append(box(340, 364, 120, 60, "P(G | evidence)", t["p_g_evidence"], DHI))
    parts.append(arrow(170, 394, 190, 394, DHI))
    parts.append(arrow(320, 394, 340, 394, DHI))
    parts.append(box(500, 364, 170, 60, "Contact geometry", t["geometry"], DHI))
    parts.append(box(890, 364, 170, 60, "HCWC | G, evidence", t["hcwc_post"], DHI))
    parts.append(arrow(670, 394, 890, 394, DHI))

    # ---- the two channels: the prior enters each update once ----------------------------------
    parts.append(rail([(375, 160), (375, 262), (400, 262), (400, 364)], DHI))
    parts.append(text(410, 254, "P(G) is the prior", 11.5, DHI, "start"))
    parts.append(text(410, 270, "the evidence updates", 11.5, DHI, "start"))
    parts.append(arrow(975, 160, 975, 364, DHI))
    parts.append(text(985, 254, "reweighted by", 11.5, DHI, "start"))
    parts.append(text(985, 270, "the geometry", 11.5, DHI, "start"))

    # ---- the benchmarks, between the two contact distributions, compared and never joined -----
    parts.append(box(680, 206, 180, 52, t["bench_title"], t["bench"], MUTED, dashed=True))
    parts.append(arrow(860, 218, 895, 164, MUTED, dashed=True))
    parts.append(arrow(860, 246, 895, 360, MUTED, dashed=True))

    # ---- the join: does the column reach the threshold? one box per row -----------------------
    parts.append("<rect x='1080' y='20' width='240' height='440' rx='10' ry='10' "
                 "fill='#EEF5EF' stroke='none'/>")
    mid_title, mid_1, mid_2 = t["join_mid"]
    parts.append(text(1200, 236, mid_title, 12.5, JOIN, weight=600))
    parts.append(text(1200, 254, mid_1, 11, JOIN))
    parts.append(text(1200, 270, mid_2, 11, JOIN))
    parts.append(box(1090, 66, 220, 94, "Prior POS(h)", t["join_geo"], JOIN, muted_from=2))
    parts.append(box(1090, 330, 220, 94, "Posterior POS(h)", t["join_dhi"], JOIN, muted_from=2))

    # the chance along the outer rail of its row, the contact along the inner
    parts.append(rail([(375, 100), (375, 46), (1200, 46), (1200, 66)], GEO))
    parts.append(arrow(1060, 130, 1090, 130, GEO))
    parts.append(rail([(400, 424), (400, 446), (1200, 446), (1200, 424)], DHI))
    parts.append(arrow(1060, 394, 1090, 394, DHI))

    parts.append("</svg>")
    return "\n".join(parts)


def rasterise(svg_path: Path, png_path: Path) -> None:
    """The SVG as Chromium draws it, through kaleido, so the PNG matches the app's rendering."""
    import plotly.graph_objects as go
    import plotly.io as pio

    uri = "data:image/svg+xml;base64," + base64.b64encode(svg_path.read_bytes()).decode()
    fig = go.Figure()
    fig.update_layout(
        width=W, height=H, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="white",
        plot_bgcolor="white", xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[0, 1]),
        images=[dict(source=uri, xref="paper", yref="paper", x=0, y=1, sizex=1, sizey=1,
                     xanchor="left", yanchor="top", sizing="stretch", layer="above")])
    pio.write_image(fig, str(png_path), width=W, height=H, scale=2)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for texts in (CONCEPT, GUIDE):
        svg = FIGURES / f"{texts['file']}.svg"
        svg.write_text(draw(texts), encoding="utf-8")
        print(svg)
        png = svg.with_suffix(".png")
        rasterise(svg, png)
        print(png)


if __name__ == "__main__":
    main()
