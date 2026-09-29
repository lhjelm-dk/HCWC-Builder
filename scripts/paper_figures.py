"""The article's concept sketch (fig5) and the worked prospect's definition, paper/figures/prospect.json.

Run:  python scripts/paper_figures.py

Since 17 Sep 2026 the article's other figures are the app's own, exported by
``scripts/export_exhibits.py`` with the same look as the tabs; the matplotlib set this script drew
before is kept off-repository as ``paper_figures_mpl_2026-09-17.py``. What stays here is the
figure that has no app counterpart, the terminating-versus-truncating sketch, and the prospect
written beside the figures so the inputs travel with the outputs.

**The prospect is taken from the running app, not from the core fixture.** They are not the same
thing -- ``limits.reference_prospect()`` is the tests' fixture, while the app opens on *Tiramisu-C4*
built by ``hcwc.ui.limiters_tab.SPECS``, with charge and top-seal capacity computed rather than
typed. So the script starts an ``AppTest``, lifts the resolved limit set and element chances out
of session state, and writes them as ``paper/figures/prospect.json``.
"""
from __future__ import annotations

import contextlib
import io as _io
import json
import pathlib
import sys
import warnings

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from hcwc.core import engine
from hcwc.core.limits import DepthDistribution, Group, Limit, LimitSet

OUT = ROOT / "paper" / "figures"

# The scenario is stated once, in scripts/paper_facts.py; these names are kept for the callers.
sys.path.insert(0, str(ROOT / "scripts"))
import paper_facts as _facts  # noqa: E402

HMIN = _facts.H_MIN_M
N = _facts.N_TRIALS
SEED = _facts.SEED

plt.rcParams.update({
    "font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 9.5,
    "legend.fontsize": 7.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
})


def from_the_app() -> tuple[LimitSet, float]:
    """The limit set and P(G) of the paper scenario, read through the app (paper_facts)."""
    limit_set, _, p_g = _facts.scenario()
    return limit_set, p_g


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  {path.relative_to(ROOT)}")


def figure_5_truncate_vs_terminate() -> None:
    """Hood's (2019) warning, reproduced in this engine on a 500 m closure.

    Deliberately *not* the worked prospect: the point is a construction error, and it shows
    cleanest on the simplest trap that can carry it.
    """
    def build(seal_max: float) -> LimitSet:
        return LimitSet(
            name="x", apex=DepthDistribution("fixed", {"value": 2000.0}),
            limits=(Limit("Closure / spill", Group.CLOSURE, 1.0,
                          DepthDistribution("fixed", {"value": 500.0})),
                    Limit("Top seal", Group.RETENTION, 1.0,
                          DepthDistribution("uniform", {"minimum": 0.0, "maximum": seal_max}))))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.3))
    out = {}
    for label, mx, colour, style in (
            ("terminated — U(0, 500), linked to closure", 500.0, "#94A3B8", "--"),
            ("truncated — U(0, 1000), cut by spill", 1000.0, "#1D4ED8", "-")):
        r = engine.run(build(mx), n=N, seed=SEED)
        grid = np.linspace(0, 560, 500)
        ax.plot(grid, [float((r.column_m >= h).mean()) for h in grid],
                color=colour, lw=1.9, ls=style, label=label)
        out[label] = (float(r.column_m.mean()), float((r.column_m >= 499.9).mean()))
    ax.axvline(500.0, color="#111", lw=0.8, ls=":")
    ax.annotate("synclinal spill", (500, 0.30), xytext=(-5, 0),
                textcoords="offset points", ha="right", fontsize=7, rotation=90)
    ax.set_xlabel("column height (m)")
    ax.set_ylabel("$P(H \\geq h)$")
    ax.set_ylim(0, 1.03)
    ax.legend(loc="lower left", frameon=False, fontsize=7)
    ax.set_title("(a) the same seal, linked or truncated", loc="left")

    # Both quantities are fractions of the 500 m closure, so they share one axis. A twin
    # axis put two different scales behind adjacent bars, which is how bar charts mislead.
    keys = list(out)
    x = np.arange(2)
    means = [out[k][0] / 500.0 for k in keys]
    spills = [out[k][1] for k in keys]
    ax2.bar(x - 0.19, means, 0.36, color="#1D4ED8",
            label="mean column, as a fraction of closure")
    ax2.bar(x + 0.19, spills, 0.36, color="#B45309", label="P(filled to spill)")
    for i, k in enumerate(keys):
        ax2.annotate(f"{means[i]:.0%} ({out[k][0]:.0f} m)", (i - 0.19, means[i]),
                     xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.5)
        ax2.annotate(f"{spills[i]:.0%}", (i + 0.19, spills[i]), xytext=(0, 3),
                     textcoords="offset points", ha="center", fontsize=7.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(["terminated" + chr(10) + "(linked to closure)",
                         "truncated" + chr(10) + "(cut by spill)"])
    ax2.set_ylabel("fraction of the 500 m closure")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("(b) 125 m of mean column, 50 points of fill-to-spill", loc="left")
    ax2.grid(axis="x", visible=False)
    ax2.legend(loc="upper left", frameon=False, fontsize=7)
    save(fig, "fig5_truncate_vs_terminate.png")


def main() -> None:
    print("lifting the app's default prospect...")
    limit_set, p_g = from_the_app()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prospect.json").write_text(json.dumps(limit_set.to_dict(), indent=2),
                                       encoding="utf-8")
    print(f"  {(OUT / 'prospect.json').relative_to(ROOT)}")

    # The paper's figures are the app's own exhibits since 22 Sep 2026: run
    # `scripts/export_exhibits.py`, which writes every figure and table to `paper/figures` at the
    # browser's ratio, named by number. `figure_5_truncate_vs_terminate` and
    # `hcwc/plotting/paper/figures.py` stay here for reuse and are not run by this script; their
    # output is kept off-repository, among the superseded figures.

    result = engine.run(limit_set, n=N, seed=SEED)
    f = float((result.column_m >= HMIN).mean())
    print(f"\n  P(G) = {p_g:.4f}    F({HMIN:.0f} m) = {f:.4f}    prospect POS = {p_g * f:.1%}")
    print("  the article's numbers: python scripts/paper_facts.py")


if __name__ == "__main__":
    main()
