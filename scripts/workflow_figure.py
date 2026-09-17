"""The workflow figure for 8.1.1, docs/figures/fig0_workflow.svg, drawn as SVG by hand.

A 2 x 2 grid (Lars, 17 Sep 2026). Rows: the geological model on top, the modification given
the DHI below. Columns: the chance (is there an accumulation?) on the left, the contact given
success (where does the column stop?) on the right. The DHI's two channels are two short
vertical arrows, evidence strength from P(G) to P(G | strength) and contact geometry from
HCWC | G to HCWC | G, evidence, so nothing crosses a box. The rows join on the right in the
chance against depth, read at the assessment minimum and at the well; the chance reaches the
join along the outer rail of its row, the contact along the inner. The benchmarks sit dashed
between the two contact distributions, compared with both and never joined.

Vector, not raster, so it is crisp at any zoom in the app, the report and the paper. Run from
the repository root::

    python scripts/workflow_figure.py
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "figures" / "fig0_workflow.svg"

INK, MUTED, GEO, DHI, JOIN = "#333333", "#7d8794", "#4C72B0", "#C44E52", "#2F6B3F"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"

W, H = 1340, 480


def text(x, y, s, size=11, colour=INK, anchor="middle", weight=None):
    bold = f" font-weight='{weight}'" if weight else ""
    return (f"<text x='{x}' y='{y}' text-anchor='{anchor}' font-size='{size}' fill='{colour}'"
            f"{bold} {FONT}>{s}</text>")


def box(x, y, w, h, title, lines, colour, dashed=False):
    """A rounded box with a bold title and one line beneath it; ``lines`` may hold two or three
    for the join boxes, the last one muted when it is a tab reference."""
    dash = " stroke-dasharray='6 4'" if dashed else ""
    lines = [lines] if isinstance(lines, str) else list(lines)
    out = (f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='8' ry='8' fill='white' "
           f"stroke='{colour}' stroke-width='1.8'{dash}/>"
           + text(x + w / 2, y + 24, title, 14, colour, weight=600))
    for k, line in enumerate(lines):
        muted = line.startswith("tab ")
        out += text(x + w / 2, y + 44 + 18 * k, line, 11, MUTED if muted else INK)
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


def main() -> None:
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

    # ---- the two rows -------------------------------------------------------------------------
    parts.append(f"<rect x='20' y='20' width='1050' height='160' rx='10' ry='10' "
                 f"fill='#F4F5F7'/>")
    parts.append(text(34, 42, "GEOLOGICAL  ·  the model, tabs 2.0 to 4.0", 12.5, INK, "start",
                      600))
    parts.append(lane(30, 58, 370, 112, "chance  ·  is there an accumulation?", GEO, "#EEF3FA"))
    parts.append(lane(420, 58, 640, 112, "contact, given success  ·  where does the column stop?",
                      GEO, "#EEF3FA"))

    parts.append(f"<rect x='20' y='284' width='1050' height='176' rx='10' ry='10' "
                 f"fill='#F4F5F7'/>")
    parts.append(text(34, 306, "GIVEN THE DHI  ·  the modification, tab 5.0", 12.5, INK, "start",
                      600))
    parts.append(lane(30, 322, 370, 112, "evidence strength  ·  updates the chance", DHI,
                      "#FBEFEF"))
    parts.append(lane(420, 322, 640, 112, "contact geometry  ·  reweights the contact", DHI,
                      "#FBEFEF"))

    # ---- geological row ------------------------------------------------------------------------
    parts.append(box(40, 100, 160, 60, "Element chances", "play × conditional, tab 2.0", GEO))
    parts.append(box(230, 100, 160, 60, "P(G)", "product of the four", GEO))
    parts.append(arrow(200, 130, 230, 130, GEO))
    parts.append(box(440, 100, 185, 60, "Geological limits", "P(active) and a depth, tab 3.0",
                     GEO))
    parts.append(box(655, 100, 185, 60, "Competition", "shallowest active limit wins", GEO))
    parts.append(box(870, 100, 185, 60, "HCWC | G", "F(h) and the controller, tab 4.1", GEO))
    parts.append(arrow(625, 130, 655, 130, GEO))
    parts.append(arrow(840, 130, 870, 130, GEO))

    # ---- DHI row -------------------------------------------------------------------------------
    parts.append(box(40, 364, 160, 60, "DHI evidence strength", "likelihood ratio R, tab 5.1",
                     DHI))
    parts.append(box(230, 364, 160, 60, "P(G | strength)", "two-state update, capped 10 : 1",
                     DHI))
    parts.append(arrow(200, 394, 230, 394, DHI))
    parts.append(box(440, 364, 185, 60, "DHI geometry", "picked contact, c, D(h), tab 5.1", DHI))
    parts.append(box(870, 364, 185, 60, "HCWC | G, evidence", "reweighted realisations, tab 5.2",
                     DHI))
    parts.append(arrow(625, 394, 870, 394, DHI))

    # ---- the two channels: one short vertical arrow each, nothing crossed ----------------------
    parts.append(arrow(310, 160, 310, 364, DHI))
    parts.append(text(320, 254, "updated by", 11.5, DHI, "start"))
    parts.append(text(320, 270, "the strength", 11.5, DHI, "start"))
    parts.append(arrow(962, 160, 962, 364, DHI))
    parts.append(text(972, 254, "reweighted by", 11.5, DHI, "start"))
    parts.append(text(972, 270, "the geometry", 11.5, DHI, "start"))

    # ---- the benchmarks, between the two contact distributions, compared and never joined -----
    parts.append(box(648, 206, 200, 52, "Benchmarks, tab 6.0", "compared with both, never joined",
                     MUTED, dashed=True))
    parts.append(arrow(848, 218, 878, 164, MUTED, dashed=True))
    parts.append(arrow(848, 246, 878, 360, MUTED, dashed=True))

    # ---- the join: the chance against depth, one box per row ----------------------------------
    parts.append(f"<rect x='1080' y='20' width='240' height='440' rx='10' ry='10' "
                 f"fill='#EEF5EF' stroke='none'/>")
    parts.append(text(1200, 236, "CHANCE AGAINST DEPTH", 12.5, JOIN, weight=600))
    parts.append(text(1200, 254, "read at h_min, and at z_entry", 11, JOIN))
    parts.append(text(1200, 270, "for the well", 11, JOIN))
    parts.append(box(1090, 66, 220, 94, "Geological",
                     ["POS(h) = P(G) × F(h)", "the chance of a column to h",
                      "tab 4.1.3 and 4.1.4"], JOIN))
    parts.append(box(1090, 330, 220, 94, "Given the DHI",
                     ["POS(h) = P(G | strength) × F_post(h)", "same readings, same realisations",
                      "tab 5.2.3 and 5.2.4"], JOIN))

    # the chance along the outer rail of its row, the contact along the inner
    parts.append(rail([(310, 100), (310, 46), (1200, 46), (1200, 66)], GEO))
    parts.append(arrow(1055, 130, 1090, 130, GEO))
    parts.append(rail([(310, 424), (310, 446), (1200, 446), (1200, 424)], DHI))
    parts.append(arrow(1055, 394, 1090, 394, DHI))

    parts.append("</svg>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
