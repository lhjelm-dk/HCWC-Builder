"""Regenerate the five figures in docs/ARTICLE.md from the app's own default prospect.

Run:  python scripts/paper_figures.py

Nothing here is drawn by hand.

**The prospect is taken from the running app, not from the core fixture.** They are not the same
thing -- ``limits.reference_prospect()`` is the tests' fixture, while the app opens on *Tiramisu-C4*
built by ``hcwc.ui.limiters_tab.SPECS``, with charge and top-seal capacity computed rather than
typed. A figure drawn from the fixture would disagree with the app a reader opens to reproduce it,
which is exactly the failure this script exists to prevent. So it starts an ``AppTest``, lifts the
resolved limit set and element chances out of session state, and re-runs the engine at the app's
own 10 000 realisations -- the count a reader would reproduce, not a smoother one. The prospect is
written beside the figures as ``docs/figures/prospect.json`` so the inputs travel with the outputs.

Matplotlib rather than the app's Plotly, deliberately: these are print figures for a paper, not
screen figures for a tab, and the two want different defaults. The *data* is identical -- the app
and this script call the same functions in ``hcwc.core``.
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

from hcwc.core import dhi as dhi_core
from hcwc.core import engine
from hcwc.core.limits import DepthDistribution, Group, Limit, LimitSet

OUT = ROOT / "docs" / "figures"

#: The assessment minimum the article states. Everything is read at this column height.
HMIN = 120.0
#: The picked flat-event depth the article's DHI section uses, m TVDSS.
PICK_M = 2250.0
#: `P(the picked event is the contact | G, contact attributes)`, the app's own default. This
#: *is* `p_valid`: conditional on hydrocarbons, because the realisations it weights are. The
#: chance of hydrocarbons enters once, through `P(G)` updated by the amplitude, and never here.
CONTACT_GIVEN_HC = 0.36
#: The app's own default. Figures are drawn at the count a reader would
#: reproduce, not at a smoother one.
N = 10_000
SEED = 20260825

#: One colour per limit, stable across every figure so a mechanism keeps its colour. Keyed by the
#: app's names, which are not the core fixture's -- see the module docstring.
COLOURS = {
    "Charge": "#B45309",
    "Closure / spill point": "#1D4ED8",
    "Fault geometry 1": "#60A5FA",
    "Fault geometry 2": "#93C5FD",
    "Wedge geometry": "#BFDBFE",
    "Fault leakage 1": "#7C3AED",
    "Fault leakage 2": "#A78BFA",
    "Top seal (capillary)": "#065F46",
    "Base seal (capillary)": "#34D399",
    "Top seal (continuity)": "#6EE7B7",
    "Base seal (continuity)": "#A7F3D0",
    "Preservation / tilt": "#94A3B8",
    "Top seal (fracture)": "#CBD5E1",
}
PRIOR_C, POST_C = "#334155", "#B91C1C"
SPILL = "Closure / spill point"

plt.rcParams.update({
    "font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 9.5,
    "legend.fontsize": 7.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "figure.dpi": 200, "savefig.dpi": 200, "savefig.bbox": "tight",
})


def from_the_app() -> tuple[LimitSet, float]:
    """The limit set and element product the app opens on, at the article's assessment minimum."""
    warnings.filterwarnings("ignore")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=900)
    at.session_state["min_column_input"] = HMIN
    with contextlib.redirect_stderr(_io.StringIO()):
        at.run()
    limit_set = at.session_state["dhi_posterior"].result.limit_set
    p_g = 1.0
    for chance in at.session_state["element_pos"].values():
        p_g *= float(chance)
    return limit_set, p_g


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  {path.relative_to(ROOT)}")


def _live(result: engine.EngineResult, floor: float = 0.0005) -> list[str]:
    """Limits that actually control something, commonest first. The rest are noise on a legend."""
    ls = result.limit_set
    pairs = [(n, float((result.controller == ls.names.index(n)).mean())) for n in ls.names]
    return [n for n, s in sorted(pairs, key=lambda p: -p[1]) if s > floor]


# --------------------------------------------------------------------------- 1
def figure_1_competing_limits(result: engine.EngineResult) -> None:
    """What the engine does to one realisation, and what forty of them look like.

    The left panel is the construction itself: every active limit's sampled depth as a dot, the
    controlling one ringed. The right panel is the distribution those minima make.
    """
    ls = result.limit_set
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.5), width_ratios=[1.6, 1])

    n_show = 40
    rng = np.random.default_rng(11)
    pick = np.sort(rng.choice(result.n, n_show, replace=False))
    apex = result.apex_m[pick]

    for name in _live(result):
        j = ls.names.index(name)
        depth = apex + result.sampled_m[pick, j]
        on = result.active[pick, j]
        if on.any():
            ax.scatter(np.arange(n_show)[on], depth[on], s=9, alpha=0.6,
                       color=COLOURS.get(name, "#999"), linewidths=0, zorder=2, label=name)

    won = apex + result.column_m[pick]
    ax.scatter(np.arange(n_show), won, s=46, facecolors="none", edgecolors="#111",
               linewidths=0.9, zorder=4, label="the minimum — controls this realisation")
    ax.plot(np.arange(n_show), won, color="#111", lw=0.7, alpha=0.35, zorder=3)

    # A capillary capacity sampled from the tail can sit 800 m below anything else on the
    # plot, and left alone it sets the axis and squeezes the construction into a band. The
    # clip is cosmetic and stated: those realisations are in the model, just off this panel.
    shown = np.concatenate([(apex + result.sampled_m[pick, ls.names.index(n)])[
        result.active[pick, ls.names.index(n)]] for n in _live(result)])
    ax.set_xlabel("realisation")
    ax.set_ylabel("depth (m TVDSS)")
    ax.set_title("(a) every active limit is sampled; the shallowest wins", loc="left")
    ax.set_ylim(float(np.percentile(shown, 0.5)) - 15, float(np.percentile(shown, 97)) + 15)
    ax.invert_yaxis()
    ax.legend(loc="upper center", bbox_to_anchor=(0.72, -0.14), ncol=3, frameon=False,
              handletextpad=0.3, columnspacing=1.2, fontsize=7.2)

    contact = result.contact_m
    ax2.hist(contact, bins=70, orientation="horizontal", color="#CBD5E1", edgecolor="none")
    top = ax2.get_xlim()[1]
    for q, style, tag in ((90, ":", "P90"), (50, "-", "P50"), (10, ":", "P10")):
        y = float(np.percentile(contact, 100 - q))
        ax2.plot([0, top], [y, y], color="#111", lw=0.8, ls=style)
        ax2.annotate(f"{tag}  {y:,.0f} m", (top, y), xytext=(-2, 2),
                     textcoords="offset points", ha="right", va="bottom", fontsize=7)
    ax2.axhline(float(np.median(result.apex_m)) + HMIN, color="#B91C1C", lw=1.0, ls="--")
    ax2.annotate("assessment minimum", (0.04, float(np.median(result.apex_m)) + HMIN),
                 xycoords=("axes fraction", "data"), xytext=(0, 4),
                 textcoords="offset points", fontsize=7, color="#B91C1C", va="bottom")
    ax2.set_xlabel("realisations")
    ax2.set_title("(b) the HCWC distribution they make", loc="left")
    ax2.invert_yaxis()
    ax2.set_ylim(ax.get_ylim())
    ax2.tick_params(labelleft=False)
    save(fig, "fig1_competing_limits.png")


# --------------------------------------------------------------------------- 2
def figure_2_controlling_mechanism(result: engine.EngineResult) -> None:
    """Which mechanism controlled the contact, overall and as a function of depth.

    The right panel is the one that is hard to get any other way: the controlling share is not
    constant down the structure, and that is the argument for keeping the argmin.
    """
    ls = result.limit_set
    names = _live(result)
    shares = [float((result.controller == ls.names.index(n)).mean()) for n in names]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.3), width_ratios=[1, 1.1])

    ax.barh(range(len(names)), shares,
            color=[COLOURS.get(n, "#999") for n in names], height=0.68)
    for i, s in enumerate(shares):
        ax.annotate(f"{s:.1%}", (s, i), xytext=(3, 0), textcoords="offset points",
                    va="center", fontsize=7.5)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("share of realisations")
    ax.set_xlim(0, max(shares) * 1.3)
    ax.set_title("(a) which limit controlled the contact", loc="left")
    ax.grid(axis="y", visible=False)

    contact = result.contact_m
    edges = np.linspace(np.percentile(contact, 0.5), np.percentile(contact, 99.5), 26)
    centres = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(contact, edges) - 1, 0, len(centres) - 1)
    bottom = np.zeros(len(centres))
    for name in names:
        j = ls.names.index(name)
        share = np.array([
            float((result.controller[idx == b] == j).mean()) if (idx == b).any() else 0.0
            for b in range(len(centres))])
        ax2.barh(centres, share, left=bottom, height=float(np.diff(edges).mean()) * 0.95,
                 color=COLOURS.get(name, "#999"), edgecolor="none", label=name)
        bottom += share
    ax2.axhline(float(np.median(result.apex_m)) + HMIN, color="#111", lw=1.1, ls="--")
    ax2.annotate("assessment minimum", (0.03, float(np.median(result.apex_m)) + HMIN),
                 xycoords=("axes fraction", "data"), xytext=(0, 3),
                 textcoords="offset points", fontsize=7)
    ax2.set_xlim(0, 1)
    ax2.set_xlabel("share of realisations in that depth bin")
    ax2.set_ylabel("HCWC depth (m TVDSS)")
    ax2.invert_yaxis()
    ax2.set_title("(b) and how that changes with depth", loc="left")
    ax2.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    save(fig, "fig2_controlling_mechanism.png")


# --------------------------------------------------------------------------- 3
def figure_3_survival(result: engine.EngineResult, p_g: float) -> None:
    """One curve, read in four places. The figure behind POS = P(G) x F(h_min)."""
    grid = np.linspace(0, float(np.percentile(result.column_m, 99.8)), 500)
    f = np.array([float((result.column_m >= h).mean()) for h in grid])

    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    ax.plot(grid, f, color=PRIOR_C, lw=1.9, label="$F(h)=P(H \\geq h \\mid G)$, conditional")
    ax.plot(grid, f * p_g, color="#B45309", lw=1.9, ls="--",
            label=f"$P(G)\\,F(h)$ = prospect POS   ($P(G) = {p_g:.3f}$)")

    apex = float(np.median(result.apex_m))
    spill = float(np.median(result.sampled_m[:, result.limit_set.names.index(SPILL)]))
    readings = [(HMIN, f"assessment minimum, {HMIN:.0f} m", 10, 9),
                (PICK_M - apex, f"DHI pick, {PICK_M:,.0f} m TVDSS", 10, 9),
                (spill, f"median spill, {spill:.0f} m", -6, 12)]
    for h, label, dx, dy in readings:
        if h > grid[-1]:
            continue
        y = float((result.column_m >= h).mean())
        ax.plot([h, h], [0, y], color="#94A3B8", lw=0.7, ls=":", zorder=1)
        ax.scatter([h, h], [y, y * p_g], s=24, color=[PRIOR_C, "#B45309"], zorder=5)
        ax.annotate(f"{label}\n$F$ = {y:.1%}   POS = {y * p_g:.1%}", (h, y),
                    xytext=(dx, dy), textcoords="offset points", fontsize=7, color="#333",
                    ha="right" if dx < 0 else "left")

    ax.set_xlabel("column height $h$ (m below the apex)")
    ax.set_ylabel("probability the column reaches $h$")
    ax.set_ylim(0, 1.04)
    ax.set_xlim(0, grid[-1])
    ax.legend(loc="upper right", frameon=False)
    ax.set_title("Every POS in the workflow is this one curve, read somewhere", loc="left")
    save(fig, "fig3_survival_curve.png")


# --------------------------------------------------------------------------- 4
def _p_valid(p_g: float, r_strength: float) -> float:
    """`c`, the contact-attribute judgement, and nothing else.

    Until 14 Sep 2026 this multiplied `c` by `P(G)` updated by the amplitude. The engine's
    realisations are conditional on G, so that put the chance of hydrocarbons inside a term that
    already assumed it, and the strength reached the geometry posterior twice. The arguments are
    kept so the ladder below reads as before; neither is used.
    """
    return float(np.clip(CONTACT_GIVEN_HC, 0.01, 0.99))


def figure_4_dhi_update(result: engine.EngineResult, p_g: float) -> None:
    """Prior against posterior, with the effective sample size as the honest accounting.

    The app's chain, not a shortcut: the *character* channel updates the element chance through
    E-POS's two-state model, and the *geometry* channel reweights the realisations by the pick
    and the detection function. The chance is their product, `dhi_core.prospect_pos`, and the
    depth curve is `P(G | amplitude) × F_post(h)`, which reads the headline at the assessment
    minimum by identity -- exactly as ``hcwc/ui/dhi_tab.py`` builds ``pos_curve``.
    """
    detection = dhi_core.DetectionFunction()
    strengths = dhi_core.StrengthModel()
    apex = float(np.median(result.apex_m))
    grid = np.linspace(0, float(np.percentile(result.column_m, 99.5)), 400)

    prior_f = np.array([float((result.column_m >= h).mean()) for h in grid])
    at_min = float((result.column_m >= HMIN).mean())
    prior_pos = p_g * at_min

    def curve(post: dhi_core.DhiPosterior, r_strength: float) -> tuple[np.ndarray, float]:
        return (dhi_core.prospect_pos_curve(p_g, r_strength, post, grid),
                dhi_core.prospect_pos(p_g, r_strength, post))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.5), width_ratios=[1.35, 1])
    ax.plot(grid + apex, p_g * prior_f, color=PRIOR_C, lw=2.0, zorder=5)
    # Direct labelling at the left edge, where the curves are furthest apart. A legend here
    # has nowhere to sit that is not on top of a curve.
    tags = [(p_g * prior_f[0], f"geological — {prior_pos:.1%}", PRIOR_C)]

    ladder = [(5.0, 15.0, "mild"), (20.0, 10.0, "moderate"), (40.0, 5.0, "strong")]
    esses, labels = [], []
    for k, (strength, sigma, tag) in enumerate(ladder):
        r_strength = strengths.r_at(strength)
        post = dhi_core.update(result, detection, dhi_core.DhiObservation(
            seen=True, contact_m=PICK_M, pick_sigma_m=sigma,
            p_valid=_p_valid(p_g, r_strength)))
        y, pos = curve(post, r_strength)
        ax.plot(grid + apex, y, color=POST_C, lw=1.5, alpha=0.42 + 0.29 * k, zorder=4)
        tags.append((y[0], f"{tag} — {pos:.0%}   "
                     f"(strength {strength:.0f}, $\\sigma$ {sigma:.0f} m)", POST_C))
        esses.append(float(post.effective_sample_size))
        labels.append(f"{tag}\n{strength:.0f} / {sigma:.0f} m")

    # An absent anomaly carries no character to grade; the chance is updated by the absence
    # ratio instead, P(absent | G) / P(absent | not G), through the same `applied_ratio` the
    # app uses. Within G the weights are flat on this prospect (every column sits on the
    # detection ceiling), so the curve is the geological one scaled by P(G | absent) / P(G).
    absent_obs = dhi_core.DhiObservation(seen=False)
    absent_post = dhi_core.update(result, detection, absent_obs)
    y, pos = curve(absent_post, dhi_core.applied_ratio(result, detection, absent_obs, 1.0))
    ax.plot(grid + apex, y, color="#0369A1", lw=1.6, ls="-.", zorder=4)
    tags.append((y[0], f"absent — {pos:.1%}   (f {detection.false_positive:.1f})", "#0369A1", "top"))
    for y0, text, colour, *va in tags:
        below = va and va[0] == "top"
        ax.annotate(text, (grid[0] + apex, y0), xytext=(6, -4 if below else 4),
                    textcoords="offset points", fontsize=6.8, color=colour,
                    va="top" if below else "bottom")

    ax.axvline(apex + HMIN, color="#111", lw=0.9, ls="--", zorder=1)
    ax.annotate("assessment\nminimum", (apex + HMIN, 0.37), xytext=(-5, 0), rotation=90,
                textcoords="offset points", fontsize=7, va="top", ha="right")
    ax.axvline(PICK_M, color="#B45309", lw=0.9, ls=":", zorder=1)
    ax.annotate("DHI pick", (PICK_M, 0.30), xytext=(4, 0), textcoords="offset points",
                fontsize=7, color="#B45309", va="bottom")
    ax.set_xlabel("HCWC depth (m TVDSS)")
    ax.set_ylabel("prospect POS at that depth")
    ax.set_ylim(0, 1.06)
    ax.set_title("(a) evidence reshapes the curve; it does not scale it", loc="left")

    heights = [float(result.n)] + esses + [float(absent_post.effective_sample_size)]
    ax2.bar(range(len(heights)), heights,
            color=[PRIOR_C] + [POST_C] * len(esses) + ["#0369A1"], width=0.64)
    for i, v in enumerate(heights):
        ax2.annotate(f"{v:,.0f}\n{v / result.n:.0%}", (i, v), xytext=(0, 3),
                     textcoords="offset points", ha="center", fontsize=7)
    ax2.set_xticks(range(len(heights)))
    ax2.set_xticklabels(["geological\nprior"] + labels + ["absent"], fontsize=6.6)
    ax2.set_yscale("log")
    ax2.set_ylim(100, result.n * 6)
    ax2.set_ylabel("effective sample size")
    ax2.set_title("(b) how much geology is left underneath", loc="left")
    ax2.grid(axis="x", visible=False)
    save(fig, "fig4_dhi_update.png")


# --------------------------------------------------------------------------- 5
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


# --------------------------------------------------------------------------- 6
def figure_6_paper(result: engine.EngineResult, p_g: float) -> None:
    """The one figure the short paper carries, four panels in the order of its argument.

    (a) the competition in forty realisations; (b) which mechanism controls, and how that
    changes with depth; (c) the hero: the geological HCWC against the DHI-updated one, with the
    pick and its uncertainty; (d) the chance against depth, geological and updated, read at the
    assessment minimum and at a well's entry depth. Every number is the app's own chain.
    """
    ls = result.limit_set
    apex = float(np.median(result.apex_m))
    names = _live(result)
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 8.4))
    (ax_a, ax_b), (ax_c, ax_d) = axes

    # (a) --------------------------------------------------------------- competing limits
    n_show = 40
    rng = np.random.default_rng(11)
    pick = np.sort(rng.choice(result.n, n_show, replace=False))
    apx = result.apex_m[pick]
    shown = []
    for name in names:
        j = ls.names.index(name)
        depth = apx + result.sampled_m[pick, j]
        on = result.active[pick, j]
        if on.any():
            ax_a.scatter(np.arange(n_show)[on], depth[on], s=9, alpha=0.65,
                         color=COLOURS.get(name, "#999"), linewidths=0, zorder=2, label=name)
            shown.append(depth[on])
    won = apx + result.column_m[pick]
    ax_a.scatter(np.arange(n_show), won, s=44, facecolors="none", edgecolors="#111",
                 linewidths=0.9, zorder=4, label="shallowest active limit = HCWC")
    ax_a.plot(np.arange(n_show), won, color="#111", lw=0.7, alpha=0.35, zorder=3)
    shown = np.concatenate(shown)
    ax_a.set_ylim(float(np.percentile(shown, 0.5)) - 15, float(np.percentile(shown, 97)) + 15)
    ax_a.invert_yaxis()
    ax_a.set_xlabel("realisation")
    ax_a.set_ylabel("depth (m TVDSS)")
    ax_a.set_title("(a) competing limits: the shallowest active one wins", loc="left")
    ax_a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=6.4, frameon=False,
                ncol=3, handletextpad=0.3, columnspacing=1.0)

    # (b) --------------------------------------------------------------- controlling mechanism
    contact = result.contact_m
    edges = np.linspace(np.percentile(contact, 0.5), np.percentile(contact, 99.5), 26)
    centres = 0.5 * (edges[:-1] + edges[1:])
    idx = np.clip(np.digitize(contact, edges) - 1, 0, len(centres) - 1)
    bottom = np.zeros(len(centres))
    for name in names:
        j = ls.names.index(name)
        share = np.array([
            float((result.controller[idx == b] == j).mean()) if (idx == b).any() else 0.0
            for b in range(len(centres))])
        overall = float((result.controller == j).mean())
        ax_b.barh(centres, share, left=bottom, height=float(np.diff(edges).mean()) * 0.95,
                  color=COLOURS.get(name, "#999"), edgecolor="none",
                  label=f"{name}  {overall:.0%}")
        bottom += share
    ax_b.axhline(apex + HMIN, color="#111", lw=1.0, ls="--")
    ax_b.annotate("assessment minimum", (0.03, apex + HMIN), xycoords=("axes fraction", "data"),
                  xytext=(0, 3), textcoords="offset points", fontsize=7)
    ax_b.set_xlim(0, 1)
    ax_b.invert_yaxis()
    ax_b.set_xlabel("share of realisations in that depth bin")
    ax_b.set_ylabel("HCWC depth (m TVDSS)")
    ax_b.set_title("(b) which limit controls, and how that changes with depth", loc="left")
    ax_b.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=6.4, frameon=False,
                ncol=3, title="overall share", title_fontsize=6.5, handletextpad=0.3,
                columnspacing=1.0)

    # (c) --------------------------------------------------------------- the DHI update (hero)
    detection = dhi_core.DetectionFunction()
    strength, sigma = 20.0, 10.0
    r_strength = dhi_core.StrengthModel().r_at(strength)
    obs = dhi_core.DhiObservation(seen=True, contact_m=PICK_M, pick_sigma_m=sigma,
                                  p_valid=_p_valid(p_g, r_strength))
    post = dhi_core.update(result, detection, obs)
    w = post.weights / post.weights.sum()
    bins = np.linspace(np.percentile(contact, 0.5), np.percentile(contact, 99.5), 70)
    ax_c.hist(contact, bins=bins, orientation="horizontal", color="#CBD5E1", edgecolor="none",
              density=True, label="geological HCWC, the competing limits")
    ax_c.hist(contact, bins=bins, weights=w, orientation="horizontal", color=POST_C,
              alpha=0.45, edgecolor="none", density=True, label="DHI-updated HCWC")
    ax_c.axhspan(PICK_M - sigma, PICK_M + sigma, color="#B45309", alpha=0.12, lw=0)
    ax_c.axhline(PICK_M, color="#B45309", lw=1.0, ls=":")
    ax_c.annotate(f"picked contact {PICK_M:,.0f} m, σ {sigma:.0f} m", (0.98, PICK_M - sigma),
                  xycoords=("axes fraction", "data"), xytext=(0, 3), textcoords="offset points",
                  fontsize=7, color="#B45309", ha="right", va="bottom")
    keep = result.above_minimum
    spread_b = float(np.diff(engine.weighted_percentiles(contact[keep], None,
                                                          np.array([90.0, 10.0])))[0])
    spread_a = float(np.diff(engine.weighted_percentiles(contact[keep], post.weights[keep],
                                                          np.array([90.0, 10.0])))[0])
    ax_c.text(0.98, 0.03,
              f"P90–P10: {spread_b:.0f} m before, {spread_a:.0f} m after\n"
              f"effective sample size {post.effective_sample_size:,.0f} of {result.n:,}\n"
              f"c = {CONTACT_GIVEN_HC:.2f}, strength {strength:.0f}",
              transform=ax_c.transAxes, fontsize=7, va="bottom", ha="right")
    ax_c.invert_yaxis()
    ax_c.set_xlabel("density")
    ax_c.set_ylabel("HCWC depth (m TVDSS)")
    ax_c.set_title("(c) the DHI updates the distribution; it does not replace it", loc="left")
    ax_c.legend(loc="upper right", fontsize=6.6, frameon=False)
    ax_c.tick_params(labelbottom=False)

    # (d) --------------------------------------------------------------- chance against depth
    grid = np.linspace(0, float(np.percentile(result.column_m, 99.5)), 400)
    prior_f = np.array([float((result.column_m >= h).mean()) for h in grid])
    updated = dhi_core.prospect_pos_curve(p_g, r_strength, post, grid)
    p_g_upd = dhi_core.p_g_given_strength(p_g, r_strength)
    ax_d.plot(p_g * prior_f, grid + apex, color=PRIOR_C, lw=2.0,
              label=f"geological, P(G) = {p_g:.2f}")
    ax_d.plot(updated, grid + apex, color=POST_C, lw=2.0,
              label=f"DHI-updated, P(G | strength) = {p_g_upd:.2f}")
    pos_b = p_g * float((result.column_m >= HMIN).mean())
    pos_a = dhi_core.prospect_pos(p_g, r_strength, post)
    ax_d.axhline(apex + HMIN, color="#111", lw=0.9, ls="--")
    ax_d.annotate(f"assessment minimum: POS {pos_b:.0%} before, {pos_a:.0%} after",
                  (0.02, apex + HMIN), xycoords=("axes fraction", "data"), xytext=(0, 4),
                  textcoords="offset points", fontsize=7, ha="left", va="bottom")
    z_well = 2230.0
    r_b = float((result.contact_m >= z_well).mean())
    r_a = float(post.exceedance(z_well - apex)[0])
    ax_d.axhline(z_well, color="#0369A1", lw=0.9, ls=":")
    ax_d.annotate(f"well entry {z_well:,.0f} m: P(well) {p_g * r_b:.0%} before, "
                  f"{p_g_upd * r_a:.0%} after",
                  (0.02, z_well), xycoords=("axes fraction", "data"), xytext=(0, -4),
                  textcoords="offset points", fontsize=7, color="#0369A1", ha="left", va="top")
    ax_d.invert_yaxis()
    ax_d.set_xlim(0, 1.0)
    ax_d.set_xlabel("prospect chance of a contact at least this deep")
    ax_d.set_ylabel("HCWC depth (m TVDSS)")
    ax_d.set_title("(d) the chance against depth, read at the minimum and at a well", loc="left")
    ax_d.legend(loc="upper left", fontsize=6.6, frameon=False)

    fig.tight_layout(h_pad=1.6, w_pad=1.2)
    save(fig, "fig6_paper.png")


def main() -> None:
    print("lifting the app's default prospect...")
    limit_set, p_g = from_the_app()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prospect.json").write_text(json.dumps(limit_set.to_dict(), indent=2),
                                       encoding="utf-8")
    result = engine.run(limit_set, n=N, seed=SEED)

    print(f"regenerating figures for {limit_set.name!r}...")
    figure_1_competing_limits(result)
    figure_2_controlling_mechanism(result)
    figure_3_survival(result, p_g)
    figure_4_dhi_update(result, p_g)
    figure_5_truncate_vs_terminate()
    figure_6_paper(result, p_g)

    f = float((result.column_m >= HMIN).mean())
    contact = result.contact_m
    print(f"\n  P(G) = {p_g:.4f}    F({HMIN:.0f} m) = {f:.4f}    prospect POS = {p_g * f:.1%}")
    print(f"  HCWC  P90 {np.percentile(contact, 10):,.0f} m   "
          f"P50 {np.percentile(contact, 50):,.0f} m   P10 {np.percentile(contact, 90):,.0f} m")
    for name in _live(result):
        j = result.limit_set.names.index(name)
        print(f"    {name:26s} {float((result.controller == j).mean()):6.1%}")


if __name__ == "__main__":
    main()
