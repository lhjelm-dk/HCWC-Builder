"""The article's five figures, drawn for the page from the paper scenario.

Each figure answers one question and is drawn with matplotlib from the canonical chain, not
exported from a tab: no widget chips, no tab captions, one palette. The scenario comes from
``scripts/paper_facts.py``; ``scripts/paper_figures.py`` calls :func:`draw_all`.

    1  competing limits      the HCWC distribution is derived from competing geological limits
    2  controlling mechanism the model shows why the column stops
    3  the DHI update        the DHI reweights the geological realisations; it does not replace them
    4  chance against depth  the same posterior gives the chance a well finds hydrocarbons
    5  empirical check       the prospect beside the record, with the censoring result as an inset

No Streamlit and no ``hcwc.ui`` import: the module runs from a script.
"""
from __future__ import annotations

import pathlib

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from hcwc.core import dhi, engine, pos  # noqa: E402
from hcwc.core.engine import EngineResult  # noqa: E402
from hcwc.core.limits import Group, LimitSet  # noqa: E402

INK, MUTED, GRID = "#333333", "#7d8794", "#e6e9ee"
GEO, DHI_C, WELL = "#4C72B0", "#C44E52", "#0369A1"
#: One hue per risk element; a limit takes a shade of its element's hue.
ELEMENT_HUE = {Group.CHARGE: "#C44E52", Group.CLOSURE: "#4C72B0",
               Group.RESERVOIR: "#DD8452", Group.RETENTION: "#55A868"}

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 10, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.edgecolor": INK, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 200,
    "savefig.dpi": 200, "savefig.bbox": "tight", "savefig.facecolor": "white",
})


def _shade(hex_colour: str, k: int, n: int) -> tuple:
    """The k-th of n shades of one hue, light to full."""
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    t = 0.35 + 0.65 * (k + 1) / n if n > 1 else 1.0
    return (1 - t + t * r, 1 - t + t * g, 1 - t + t * b)


def limit_palette(limit_set: LimitSet) -> dict[str, tuple]:
    out = {}
    for group in Group:
        members = [lim.name for lim in limit_set.limits if lim.group is group]
        for k, name in enumerate(members):
            out[name] = _shade(ELEMENT_HUE[group], k, len(members))
    return out


def _depth_axis(ax, lo: float, hi: float) -> None:
    ax.set_ylim(hi, lo)
    ax.set_ylabel("HCWC depth z (m TVDSS)")
    ax.grid(axis="y", color=GRID, linewidth=0.6)


# ---------------------------------------------------------------- 1 · competing limits
def figure_competing_limits(result: EngineResult, h_min: float) -> plt.Figure:
    """Each limit's exceedance in depth, flattening at its P(active); the contact is the lower
    envelope of the active ones; beside it the contact distribution that follows."""
    ls = result.limit_set
    palette = limit_palette(ls)
    apex = float(np.median(result.apex_m))
    z = pos.depth_grid(result, 300)
    fig, (ax, axh) = plt.subplots(1, 2, figsize=(7.2, 4.2), width_ratios=[1.35, 1], sharey=True)
    shares = result.controlling_shares()
    for j, lim in enumerate(ls.limits):
        if shares.get(lim.name, 0.0) < 0.002 and lim.p_active < 0.05:
            continue
        depth_j = result.apex_m + result.sampled_m[:, j]
        # P(this limit permits a contact deeper than z): absent counts as permitting
        permits = np.where(result.active[:, j][None, :], depth_j[None, :] >= z[:, None], True)
        ax.plot(permits.mean(axis=1), z, color=palette[lim.name], linewidth=1.3,
                label=f"{lim.name} ({lim.p_active:.0%} present)")
    ax.plot(pos.depth_exceedance(result, z), z, color=INK, linewidth=2.6,
            label="the contact: shallowest active limit")
    ax.axhline(apex + h_min, color=MUTED, linestyle="--", linewidth=0.9)
    ax.text(0.02, apex + h_min, " assessment minimum (median-apex equivalent)", va="bottom",
            fontsize=7, color=MUTED)
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("P(limit permits a contact at least this deep | G)")
    _depth_axis(ax, float(z[0]), float(z[-1]))
    ax.legend(loc="lower right", frameon=False, fontsize=6.5)

    edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 50)
    counts, _ = np.histogram(result.contact_m, bins=edges)
    axh.barh(0.5 * (edges[:-1] + edges[1:]), counts / counts.sum(), height=np.diff(edges),
             color=GEO, alpha=0.6, linewidth=0)
    p90, p50, p10 = result.percentiles(np.array([90.0, 50.0, 10.0]))
    for label, v in (("P90", p90), ("P50", p50), ("P10", p10)):
        axh.axhline(v, color=INK, linewidth=0.8, linestyle=":" if label != "P50" else "-")
        axh.text(axh.get_xlim()[1] * 0.98 if axh.get_xlim()[1] > 0 else 0.03, v, f"{label} {v:,.0f} m",
                 ha="right", va="bottom", fontsize=7, color=INK)
    axh.set_xlabel("share of realisations per depth bin")
    axh.spines["left"].set_visible(False)
    axh.grid(axis="y", color=GRID, linewidth=0.6)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- 2 · controlling mechanism
def figure_controlling_mechanism(result: EngineResult, h_min: float) -> plt.Figure:
    """The contact histogram stacked by the limit that set it, and the shares over the run."""
    ls = result.limit_set
    palette = limit_palette(ls)
    edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 45)
    centres = 0.5 * (edges[:-1] + edges[1:])
    shares_by_depth = engine.controlling_share_by_depth(result, edges, within_bin=False)
    shares = result.controlling_shares(successes_only=True)
    ranked = [n for n, _ in sorted(shares.items(), key=lambda kv: -kv[1]) if shares[n] > 0.003]
    fig, (ax, axb) = plt.subplots(1, 2, figsize=(7.2, 4.2), width_ratios=[1.35, 1])
    left = np.zeros(centres.size)
    for name in ranked:
        s = np.asarray(shares_by_depth.get(name, np.zeros(centres.size)), dtype=float)
        ax.barh(centres, s, left=left, height=np.diff(edges), color=palette[name], linewidth=0,
                label=name)
        left = left + s
    apex = float(np.median(result.apex_m))
    ax.axhline(apex + h_min, color=MUTED, linestyle="--", linewidth=0.9)
    ax.set_xlabel("share of all realisations per depth bin, by controlling limit")
    _depth_axis(ax, float(edges[0]), float(edges[-1]))
    ax.legend(loc="lower right", frameon=False, fontsize=6.5)

    y = np.arange(len(ranked))[::-1]
    axb.barh(y, [shares[n] for n in ranked], color=[palette[n] for n in ranked], linewidth=0)
    for yi, n in zip(y, ranked):
        axb.text(shares[n] + 0.005, yi, f"{shares[n]:.0%}", va="center", fontsize=7.5, color=INK)
    axb.set_yticks(y, ranked, fontsize=7.5)
    axb.set_xlim(0, max(shares[n] for n in ranked) * 1.25)
    axb.set_xlabel("share of realisations, h ≥ h_min")
    axb.spines["left"].set_visible(False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- 3 · the DHI update
def figure_dhi_update(result: EngineResult, posterior: dhi.DhiPosterior, p_g: float,
                      p_g_given_s: float) -> plt.Figure:
    """Prior and posterior contact distributions on one axis, the indicated contact band shaded,
    the prior kept visible so the update reads as a reweighting."""
    obs = posterior.observation
    top, base = (float(v) for v in obs.pick_ppf(np.array([0.01, 0.99])))
    edges = np.linspace(float(result.contact_m.min()), float(result.contact_m.max()), 60)
    centres = 0.5 * (edges[:-1] + edges[1:])
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.axhspan(top, base, color=DHI_C, alpha=0.08, linewidth=0)
    ax.text(0.60, top, f"indicated contact band {top:,.0f}–{base:,.0f} m", ha="left",
            va="bottom", fontsize=7, color=DHI_C, transform=ax.get_yaxis_transform())
    for label, w, colour in (("geological, P(G) = %.2f" % p_g, None, GEO),
                             ("given the DHI, P(G | s) = %.2f" % p_g_given_s, posterior.weights, DHI_C)):
        counts, _ = np.histogram(result.contact_m, bins=edges, weights=w)
        ax.barh(centres, counts / counts.sum(), height=np.diff(edges), color=colour, alpha=0.5,
                linewidth=0, label=label)
    # P90-P10 as a bar with the P50 marked, one per basis, to the right of the histograms
    for x, w, colour in ((0.955, None, GEO), (0.975, posterior.weights, DHI_C)):
        keep = result.above_minimum
        p90, p50, p10 = engine.weighted_percentiles(result.contact_m[keep],
                                                    None if w is None else w[keep],
                                                    np.array([90.0, 50.0, 10.0]))
        ax.plot([x, x], [p90, p10], color=colour, linewidth=3, solid_capstyle="butt",
                transform=ax.get_yaxis_transform())
        ax.plot([x], [p50], marker="o", color=colour, markersize=5,
                transform=ax.get_yaxis_transform())
    ax.text(0.965, float(edges[-1]) - 4, "P90–P10, P50", ha="center", va="bottom", fontsize=6.5,
            color=MUTED, transform=ax.get_yaxis_transform())
    ax.set_xlabel("share of realisations per depth bin")
    ax.set_xlim(0, ax.get_xlim()[1] * 1.45)
    _depth_axis(ax, float(edges[0]), float(edges[-1]))
    ax.legend(loc="lower right", frameon=False)
    ess = posterior.effective_sample_size
    ax.text(0.99, 0.98, f"effective sample size {ess:,.0f} of {result.n:,}", ha="right",
            va="top", fontsize=7.5, color=MUTED, transform=ax.transAxes)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- 4 · chance against depth
def figure_chance_against_depth(result: EngineResult, posterior: dhi.DhiPosterior, p_g: float,
                                p_g_given_s: float, h_min: float, z_well: float) -> plt.Figure:
    """P(well) against entry depth, geological and given the DHI, on the exact depth-space
    exceedance; the well and the assessment minimum marked."""
    z = pos.depth_grid(result, 400)
    geo = p_g * pos.depth_exceedance(result, z)
    upd = p_g_given_s * pos.depth_exceedance(result, z, posterior.weights)
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.plot(geo, z, color=GEO, linewidth=2.2, label="geological: P(G) × P(z_HCWC ≥ z | G)")
    ax.plot(upd, z, color=DHI_C, linewidth=2.6,
            label="given the DHI: P(G | s) × P(z_HCWC ≥ z | G, geometry)")
    r_geo = float(pos.depth_exceedance(result, z_well)[0])
    r_upd = float(pos.depth_exceedance(result, z_well, posterior.weights)[0])
    ax.axhline(z_well, color=WELL, linestyle=":", linewidth=1.2)
    ax.text(0.01, z_well, f" well entry {z_well:,.0f} m: {p_g * r_geo:.0%} → {p_g_given_s * r_upd:.0%}",
            va="bottom", fontsize=7.5, color=WELL, transform=ax.get_yaxis_transform())
    apex = float(np.median(result.apex_m))
    ax.axhline(apex + h_min, color=MUTED, linestyle="--", linewidth=0.9)
    ax.text(0.99, apex + h_min, "assessment minimum (median-apex equivalent) ", ha="right",
            va="bottom", fontsize=7, color=MUTED, transform=ax.get_yaxis_transform())
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("chance a well entering at z_well finds hydrocarbons")
    _depth_axis(ax, float(z[0]), float(z[-1]))
    ax.set_ylabel("well entry depth z_well (m TVDSS)")
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- 5 · the empirical check
def figure_empirical_check(result: EngineResult, burial_m: float, relief_m: float) -> plt.Figure:
    """The prospect's column beside the NCS seal-capacity record at its burial depth, capped at
    its relief; inset: the naive and the censored elasticity on the record."""
    from hcwc.core import censoring
    from hcwc.io import benchmarks

    fit = benchmarks._capacity_fit()
    rng = np.random.default_rng(11)
    bench = np.minimum(np.exp(rng.normal(fit.intercept + fit.slope * np.log(burial_m), fit.sigma,
                                         40_000)), relief_m)
    columns = result.column_m[result.above_minimum]
    grid = np.linspace(0.0, max(float(columns.max()), relief_m) * 1.02, 300)
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.plot(grid, engine.exceedance(columns, grid), color=GEO, linewidth=2.4,
            label="this prospect, geological")
    ax.plot(grid, engine.exceedance(bench, grid), color=INK, linewidth=1.6, linestyle="--",
            label=f"NCS record, censored fit, at {burial_m:,.0f} m burial, capped at the relief")
    ax.set_xlabel("hydrocarbon column height h (m)")
    ax.set_ylabel("P(H ≥ h)")
    ax.set_ylim(0, 1.02)
    ax.grid(color=GRID, linewidth=0.6)
    ax.legend(loc="upper right", frameon=False)

    data = benchmarks.load_edmundson().rows
    trap = data.trap_height_m.to_numpy(float)
    col = data.hc_column_m.to_numpy(float)
    filled = np.abs(col - trap) <= 1.0
    ins = ax.inset_axes([0.09, 0.10, 0.36, 0.42])
    ins.scatter(trap[~filled], col[~filled], s=5, color=GEO, alpha=0.6, linewidth=0,
                label="underfilled")
    ins.scatter(trap[filled], col[filled], s=5, color=DHI_C, alpha=0.7, linewidth=0,
                label=f"filled to spill ({filled.sum()} of {trap.size})")
    lim = float(np.nanmax(trap)) * 1.05
    ins.plot([0, lim], [0, lim], color=MUTED, linewidth=0.7)
    ins.set_xscale("log"); ins.set_yscale("log")
    ins.set_xlabel("closure height (m)", fontsize=6.5)
    ins.set_ylabel("column (m)", fontsize=6.5)
    ins.tick_params(labelsize=6)
    ins.legend(fontsize=5.5, frameon=False, loc="upper left")
    ins.set_title("the record: filled-to-spill points are right-censored", fontsize=6.5)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- all five
def draw_all(out_dir: pathlib.Path, *, limit_set: LimitSet, p_g: float, seed: int, n: int,
             h_min: float, evidence_index: float, pick_m: float, pick_sigma_m: float, c: float,
             z_well: float, burial_m: float) -> list[pathlib.Path]:
    """Draw the five figures from the scenario and return the paths written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    result = engine.run(limit_set, n, seed=seed)
    lr = dhi.StrengthModel().r_at(evidence_index)
    p_g_given_s = dhi.p_g_given_strength(p_g, lr)
    posterior = dhi.update(result, dhi.DetectionFunction(),
                           dhi.DhiObservation(seen=True, contact_m=pick_m,
                                              pick_sigma_m=pick_sigma_m, p_valid=c))
    spill = [j for j, lim in enumerate(limit_set.limits) if "spill" in lim.name.lower()]
    relief = float(np.median(result.sampled_m[:, spill[0]])) if spill else float(result.column_m.max())
    figures = {
        "paper_fig1_competing_limits.png": figure_competing_limits(result, h_min),
        "paper_fig2_controlling_mechanism.png": figure_controlling_mechanism(result, h_min),
        "paper_fig3_dhi_update.png": figure_dhi_update(result, posterior, p_g, p_g_given_s),
        "paper_fig4_chance_against_depth.png": figure_chance_against_depth(
            result, posterior, p_g, p_g_given_s, h_min, z_well),
        "paper_fig5_empirical_check.png": figure_empirical_check(result, burial_m, relief),
    }
    paths = []
    for name, fig in figures.items():
        path = out_dir / name
        fig.savefig(path)
        plt.close(fig)
        paths.append(path)
    return paths
