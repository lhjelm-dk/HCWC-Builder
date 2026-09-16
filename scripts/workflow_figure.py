"""The one-page workflow figure for 8.1.1, docs/figures/fig0_workflow.png.

Drawn rather than photographed: boxes and arrows only, in the app's palette, so the figure says
what the model does in the order it does it and nothing else. Run from the repository root::

    python scripts/workflow_figure.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "docs" / "figures" / "fig0_workflow.png"

INK, GEO, DHI, MUTED = "#333333", "#4C72B0", "#C44E52", "#7d8794"


def box(ax, x, y, w, h, title, body, colour):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03",
                                linewidth=1.6, edgecolor=colour, facecolor="white"))
    ax.text(x + w / 2, y + h - 0.16, title, ha="center", va="top", fontsize=10.2,
            fontweight="bold", color=colour)
    ax.text(x + w / 2, y + h - 0.46, body, ha="center", va="top", fontsize=9, color=INK,
            linespacing=1.35)


def arrow(ax, a, b, colour=INK, text=None, dx=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=16, linewidth=1.4,
                                 color=colour, shrinkA=2, shrinkB=2))
    if text:
        ax.text((a[0] + b[0]) / 2 + dx, (a[1] + b[1]) / 2, text, fontsize=8.5, color=colour,
                ha="left" if dx > 0 else "center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))


def main() -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=150)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6.2)
    ax.axis("off")

    # ---- the geological chain, left to right along the top --------------------------------
    w, h, y = 2.05, 1.6, 4.3
    xs = [0.2, 2.45, 4.7, 6.95]
    box(ax, xs[0], y, w, h, "Geological limits",
        "charge, spill, fault,\nseal capacity, continuity,\nmechanical, reservoir;\n"
        "each: P(active), depth or\ncolumn distribution", GEO)
    box(ax, xs[1], y, w, h, "Competition",
        "per realisation\nH = min(active limits)\ncontrolling limit\nrecorded", GEO)
    box(ax, xs[2], y, w, h, "HCWC | G",
        "contact and column\ndistribution\nF(h) = P(H ≥ h | G)\ncontrolling shares", GEO)
    box(ax, xs[3], y, w, h, "Chance against depth",
        "POS(h) = P(G) × F(h)\nread at h_min\nP(well) at entry depth\nper-element curves", GEO)
    for a, b in zip(xs, xs[1:]):
        arrow(ax, (a + w, y + h / 2), (b, y + h / 2), GEO)

    # ---- the element chance feeding the chance, from the right ------------------------------
    box(ax, 9.3, y + 0.3, 1.55, 1.0, "P(G)", "element chances\n(tab 2.0)", GEO)
    arrow(ax, (9.3, y + 0.8), (xs[3] + w, y + 0.8), GEO)

    # ---- the two DHI channels, each straight below the quantity it updates -----------------
    y2, h2 = 0.55, 1.6
    box(ax, 3.9, y2, 3.4, h2, "DHI geometry",
        "picked contact, pick uncertainty,\ncontact attribution c, detection D(h)\n"
        "p(h | G, geometry) ∝ p(h | G) · L(h)\nlikelihood weighting within G", DHI)
    box(ax, 7.6, y2, 3.2, h2, "DHI character",
        "evidence strength → R\nP(G | strength) =\nR·P(G) / (R·P(G) + 1 − P(G))\n"
        "two-state Bayesian update", DHI)
    arrow(ax, (5.6, y2 + h2), (xs[2] + w / 2, y), DHI, "reweights HCWC | G", dx=0.12)
    arrow(ax, (9.2, y2 + h2), (10.07, y + 0.3), DHI, "updates P(G)", dx=0.12)

    ax.text(0.3, 2.05,
            "One observation, two information\nchannels. Strength moves the weight\n"
            "on hydrocarbon presence; geometry\nmoves where the contact distribution\n"
            "places its probability. Each enters\nthe chance once; nothing is re-simulated.",
            fontsize=8.5, color=MUTED, va="top")
    ax.text(0.3, 3.7,
            "Benchmarks (tab 6.0) are compared\nbeside the geological curve, never\n"
            "multiplied in; the filled-to-spill\nrecord is censored.",
            fontsize=8.5, color=MUTED, va="top")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    print(OUT)


if __name__ == "__main__":
    main()
