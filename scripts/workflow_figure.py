"""The workflow figure for 8.1.1, docs/figures/fig0_workflow.svg, drawn as SVG by hand.

Two tracks, each with a geological main lane and an evidence sub-lane (Lars, 17 Sep 2026):

* the chance track: P(G) from the element chances, updated by the DHI's evidence strength;
* the contact track, given success: the competition of limits and the HCWC | G it produces,
  reweighted by the DHI's geometry on the same realisations;

joined on the right in the chance against depth, read at the assessment minimum and at the
well. The benchmarks sit beside the geological contact lane, compared and never joined.

Vector, not raster, so it is crisp at any zoom in the app, the report and the paper. Run from
the repository root::

    python scripts/workflow_figure.py
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "figures" / "fig0_workflow.svg"

INK, MUTED, GEO, DHI, JOIN = "#333333", "#7d8794", "#4C72B0", "#C44E52", "#2F6B3F"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"

W, H = 1180, 620


def box(x, y, w, h, title, line, colour, dashed=False):
    dash = " stroke-dasharray='6 4'" if dashed else ""
    return (
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='8' ry='8' fill='white' "
        f"stroke='{colour}' stroke-width='1.8'{dash}/>"
        f"<text x='{x + w / 2}' y='{y + 24}' text-anchor='middle' font-size='14' "
        f"font-weight='600' fill='{colour}' {FONT}>{title}</text>"
        f"<text x='{x + w / 2}' y='{y + 44}' text-anchor='middle' font-size='12' "
        f"fill='{INK}' {FONT}>{line}</text>"
    )


def arrow(x1, y1, x2, y2, colour, label=None, dashed=False, lx=None, ly=None, anchor="middle"):
    dash = " stroke-dasharray='6 4'" if dashed else ""
    marker = {GEO: "geo", DHI: "dhi", MUTED: "muted"}.get(colour, "join")
    out = (f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{colour}' "
           f"stroke-width='1.8'{dash} marker-end='url(#arrow-{marker})'/>")
    if label:
        lx = (x1 + x2) / 2 if lx is None else lx
        ly = (y1 + y2) / 2 - 6 if ly is None else ly
        out += (f"<text x='{lx}' y='{ly}' text-anchor='{anchor}' font-size='11.5' "
                f"fill='{colour}' {FONT}>{label}</text>")
    return out


def lane(x, y, w, h, title, colour, fill):
    return (
        f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='10' ry='10' fill='{fill}' "
        f"stroke='none'/>"
        f"<text x='{x + 14}' y='{y + 20}' font-size='12.5' font-weight='600' fill='{colour}' "
        f"{FONT}>{title}</text>"
    )


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

    # ---- the two tracks, each with a geological lane and an evidence lane -------------------
    parts.append(lane(20, 20, 830, 250, "CHANCE  ·  is there an accumulation?", INK, "#F4F5F7"))
    parts.append(lane(30, 48, 810, 100, "geological", GEO, "#EEF3FA"))
    parts.append(lane(30, 158, 810, 100, "given the DHI  ·  evidence strength", DHI, "#FBEFEF"))

    parts.append(lane(20, 300, 830, 300, "CONTACT, GIVEN SUCCESS  ·  where does the column stop?",
                      INK, "#F4F5F7"))
    parts.append(lane(30, 328, 810, 150, "geological", GEO, "#EEF3FA"))
    parts.append(lane(30, 488, 810, 100, "given the DHI  ·  contact geometry", DHI, "#FBEFEF"))

    # ---- chance track ------------------------------------------------------------------------
    parts.append(box(60, 76, 250, 60, "Element chances", "play × conditional, tab 2.0", GEO))
    parts.append(box(520, 76, 250, 60, "P(G)", "the product of the four", GEO))
    parts.append(arrow(310, 106, 520, 106, GEO))
    parts.append(box(60, 186, 250, 60, "DHI evidence strength",
                     "likelihood ratio R, tab 5.1", DHI))
    parts.append(box(520, 186, 250, 60, "P(G | strength)", "two-state update, capped 10 : 1",
                     DHI))
    parts.append(arrow(310, 216, 520, 216, DHI))
    parts.append(arrow(645, 136, 645, 186, DHI, "updated by the strength", lx=655, ly=166,
                       anchor="start"))

    # ---- contact track -----------------------------------------------------------------------
    parts.append(box(60, 366, 220, 60, "Geological limits",
                     "P(active) and a depth each, tab 3.0", GEO))
    parts.append(box(320, 366, 220, 60, "Competition", "shallowest active limit wins", GEO))
    parts.append(box(580, 366, 250, 60, "HCWC | G", "F(h), controller, percentiles, tab 4.1",
                     GEO))
    parts.append(arrow(280, 396, 320, 396, GEO))
    parts.append(arrow(540, 396, 580, 396, GEO))
    parts.append(box(60, 516, 250, 60, "DHI geometry",
                     "picked contact, c, detection D(h), tab 5.1", DHI))
    parts.append(box(580, 516, 250, 60, "HCWC | G, evidence",
                     "same realisations, reweighted, tab 5.2", DHI))
    parts.append(arrow(310, 546, 580, 546, DHI))
    parts.append(arrow(705, 426, 705, 516, DHI, "reweighted by the geometry", lx=715, ly=478,
                       anchor="start"))

    # ---- the benchmarks, compared and never joined --------------------------------------------
    parts.append(box(330, 430, 240, 52, "Benchmarks, tab 6.0", "compared beside F(h), never joined",
                     MUTED, dashed=True))
    parts.append(arrow(570, 452, 590, 428, MUTED, dashed=True))

    # ---- joined on the right: the chance against depth -------------------------------------
    parts.append(f"<rect x='880' y='48' width='280' height='540' rx='10' ry='10' fill='#EEF5EF' "
                 f"stroke='none'/>")
    parts.append(f"<text x='894' y='68' font-size='12.5' font-weight='600' fill='{JOIN}' "
                 f"{FONT}>CHANCE AGAINST DEPTH</text>")
    parts.append(box(900, 96, 240, 96, "Geological", "", JOIN))
    parts.append(f"<text x='1020' y='140' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>POS(h) = P(G) × F(h)</text>")
    parts.append(f"<text x='1020' y='158' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>read at h_min, and at z_entry for the well</text>")
    parts.append(f"<text x='1020' y='176' text-anchor='middle' font-size='11.5' fill='{MUTED}' "
                 f"{FONT}>tab 4.1.3 and 4.1.4</text>")
    parts.append(box(900, 236, 240, 96, "Given the DHI", "", JOIN))
    parts.append(f"<text x='1020' y='280' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>POS(h) = P(G | strength) × F_post(h)</text>")
    parts.append(f"<text x='1020' y='298' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>same readings, same realisations</text>")
    parts.append(f"<text x='1020' y='316' text-anchor='middle' font-size='11.5' fill='{MUTED}' "
                 f"{FONT}>tab 5.2.3 and 5.2.4</text>")
    parts.append(f"<text x='1020' y='372' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>One weighted sample reads</text>")
    parts.append(f"<text x='1020' y='390' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>the histogram, the percentiles,</text>")
    parts.append(f"<text x='1020' y='408' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>F(h) and the chance; nothing</text>")
    parts.append(f"<text x='1020' y='426' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>is re-simulated or rescaled.</text>")
    parts.append(f"<text x='1020' y='466' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>Strength moves the chance and</text>")
    parts.append(f"<text x='1020' y='484' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>never the contact; geometry moves</text>")
    parts.append(f"<text x='1020' y='502' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>the contact and never the chance's</text>")
    parts.append(f"<text x='1020' y='520' text-anchor='middle' font-size='12' fill='{INK}' "
                 f"{FONT}>first factor. Each enters once.</text>")

    # geological P(G) and F(h) into the geological product; the updated pair into the updated one
    parts.append(arrow(770, 106, 900, 130, GEO))
    parts.append(arrow(830, 396, 900, 160, GEO))
    parts.append(arrow(770, 216, 900, 270, DHI))
    parts.append(arrow(830, 546, 900, 300, DHI))

    parts.append("</svg>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
