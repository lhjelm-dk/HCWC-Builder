"""Every limit and the answer, on **one** shared depth axis, drawn however you want to see it.

This replaces three figures that were showing the same information three ways: a grid of small
exceedance curves, an overlay of those curves, and a row of violin panels. Lars, 27 Aug 2026: *"the
4.5 is not great in that there are 3 rows. I want all the curves on one depth y axis"* — and,
looking at the two that remained, *"is 4.5 and 4.7 not the same?"* They were. One figure with a
display mode is the honest version of all three.

**Modes, and what each is for.**

* **Exceedance curves** — the analytic view. A limit that is only sometimes present flattens at its
  ``P(active)``, and the result is the *lower envelope* of the family, because the contact is the
  shallowest active limit. That relationship is only visible with everything on one axis.
* **Violin / half violin** — where each limit's mass actually sits. Better than curves for spotting
  two limits that overlap, worse for reading a probability off.
* **Histogram** — the same, unsmoothed, for when a kernel would invent a shape the samples do not
  have.
* **Points** — every *n*-th realisation, jittered. The only mode that shows the sample itself,
  which is what you want when a distribution looks implausibly smooth.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from hcwc.core import decompose, engine
from hcwc.core.limits import COLUMN, DEPTH, Limit, convert
from hcwc.ui import theme

MODES = ("Exceedance curves", "Violin", "Half violin", "Histogram", "Points")

#: Vertical space one limit's density occupies, as a share of its lane.
LANE_FILL = 0.86


def default_window(result, space: str, apex: float, spill: float | None) -> tuple[float, float]:
    """The default depth range: 1 % above the apex to 1 % below the spill point.

    Lars's rule. Bounding by the *structure* rather than by the deepest thing any limit could have
    imposed keeps the picture on the part of the section that exists — several limits carry long
    tails reaching a kilometre below the apex, and letting those set the range pushes everything
    interesting into the top eighth of the plot.
    """
    deep = spill if spill is not None else float(np.percentile(result.contact_m, 99.8))
    lo_d, hi_d = apex * 0.99, deep * 1.01
    return (convert(lo_d, frm=DEPTH, to=space, apex_m=apex),
            convert(hi_d, frm=DEPTH, to=space, apex_m=apex))


def figure(result, *, space: str = DEPTH, mode: str = "Exceedance curves",
           window: tuple[float, float] | None = None, every: int = 10,
           posterior: np.ndarray | None = None) -> go.Figure:
    """All limits and the contact, on one depth axis.

    ``space`` is m TVDSS or metres of column below the apex — display only; the model always
    competes in column height. ``window`` clips the depth axis. ``every`` is the thinning for the
    points mode.
    """
    limit_set = result.limit_set
    apex = float(np.median(result.apex_m))
    ranked = [name for name, _ in engine.limit_ranking(result)]
    colour_of = _limit_colours(limit_set)

    lo, hi = window if window else default_window(result, space, apex, _spill(result, apex))
    lo, hi = min(lo, hi), max(lo, hi)

    fig = go.Figure()
    if mode == "Exceedance curves":
        _exceedance_mode(fig, result, space, apex, ranked, colour_of, lo, hi, posterior)
    else:
        _density_mode(fig, result, space, apex, ranked, colour_of, lo, hi, mode, every)

    fig.update_yaxes(title_text=Limit.label_for(space), autorange="reversed", range=[hi, lo])
    fig.update_layout(height=660, margin=dict(t=30, b=20, l=80, r=10),
                      legend=dict(orientation="v", x=1.02), plot_bgcolor="rgba(0,0,0,0)")
    _datums(fig, result, space, apex)
    return fig


def _exceedance_mode(fig, result, space, apex, ranked, colour_of, lo, hi, posterior) -> None:
    depths = np.linspace(min(lo, hi), max(lo, hi), 260)
    as_depth = convert(depths, frm=space, to=DEPTH, apex_m=apex)
    curves = decompose.limit_curves_at_depth(result, as_depth)
    for name in ranked:
        if curves[name].max() <= 0.001:
            continue
        fig.add_scatter(x=curves[name], y=depths, mode="lines", name=name,
                        line=dict(color=colour_of[name], width=1.9),
                        hovertemplate=f"{name}<br>%{{y:,.0f}} · %{{x:.0%}}<extra></extra>")
    final = (result.contact_m[None, :] > as_depth[:, None]).mean(axis=1)
    if posterior is not None:
        fig.add_scatter(x=posterior, y=depths, mode="lines", name="with the DHI",
                        line=dict(color="#DD8452", width=2.6, dash="dash"))
    fig.add_scatter(x=final, y=depths, mode="lines", name="Resulting HC depth",
                    line=dict(color="#C44E52", width=5))
    fig.update_xaxes(title_text="Probability the contact is deeper", range=[0, 1],
                     tickformat=".0%")


def _density_mode(fig, result, space, apex, ranked, colour_of, lo, hi, mode, every) -> None:
    """One lane per limit, plus the contact, all against the same depth axis."""
    series: list[tuple[str, np.ndarray, str]] = []
    for j, limit in enumerate(result.limit_set.limits):
        drawn = np.where(result.active[:, j], result.sampled_m[:, j], np.nan)
        drawn = drawn[np.isfinite(drawn)]
        if drawn.size < 2:
            continue
        series.append((limit.name, convert(drawn, frm=COLUMN, to=space, apex_m=apex),
                       colour_of[limit.name]))
    series.sort(key=lambda s: ranked.index(s[0]) if s[0] in ranked else len(ranked))
    series.append(("Resulting HC depth",
                   convert(result.contact_m, frm=DEPTH, to=space, apex_m=apex), "#C44E52"))

    grid = np.linspace(lo, hi, 300)
    for lane, (name, values, colour) in enumerate(series):
        centre = lane + 0.5
        if mode == "Points":
            thinned = values[::max(int(every), 1)]
            jitter = np.random.default_rng(lane).uniform(-0.30, 0.30, thinned.size)
            fig.add_scatter(x=centre + jitter, y=thinned, mode="markers", name=name,
                            marker=dict(color=colour, size=3, opacity=0.45),
                            hovertemplate=f"{name}<br>%{{y:,.0f}}<extra></extra>")
            continue
        if mode == "Histogram":
            counts, edges = np.histogram(values, bins=45, range=(lo, hi))
            peak = counts.max() or 1
            mids = 0.5 * (edges[:-1] + edges[1:])
            fig.add_bar(x=LANE_FILL * counts / peak, y=mids, orientation="h", name=name,
                        width=(hi - lo) / 45, base=centre - LANE_FILL / 2,
                        marker=dict(color=theme.rgba(colour, 0.75), line_width=0),
                        hovertemplate=f"{name}<br>%{{y:,.0f}}<extra></extra>")
            continue
        density = _density(values, grid)
        half = mode == "Half violin"
        # A half violin's left edge is the lane centre — but as an *array* along the grid, because
        # the polygon below reverses it. A bare float made `left[::-1]` a TypeError, so one of the
        # five options in the dropdown took the page down every time it was chosen.
        left = (np.full_like(density, centre) if half
                else centre - LANE_FILL / 2 * density)
        right = centre + (LANE_FILL if half else LANE_FILL / 2) * density
        fig.add_scatter(x=np.concatenate([right, left[::-1]]),
                        y=np.concatenate([grid, grid[::-1]]), fill="toself", mode="lines",
                        name=name, fillcolor=theme.rgba(colour, 0.70),
                        line=dict(color=theme.shade_hex(colour, -0.35), width=1),
                        hovertemplate=f"{name}<br>%{{y:,.0f}}<extra></extra>")

    fig.update_xaxes(tickvals=[i + 0.5 for i in range(len(series))],
                     ticktext=[name for name, _, _ in series], tickangle=-40,
                     showgrid=False, zeroline=False, range=[0, len(series)])
    fig.update_layout(barmode="overlay", showlegend=False)


def _density(values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if np.allclose(values, values[0]):
        out = np.zeros_like(grid)
        out[np.argmin(np.abs(grid - float(values[0])))] = 1.0
        return out
    from scipy.stats import gaussian_kde
    density = gaussian_kde(values)(grid)
    peak = float(density.max())
    return density / peak if peak > 0 else density


def _datums(fig, result, space, apex) -> None:
    spill = _spill(result, apex)
    for value, label in ((apex, "Structural apex"), (spill, "Spill point")):
        if value is None:
            continue
        y = float(convert(value, frm=DEPTH, to=space, apex_m=apex))
        fig.add_hline(y=y, line=dict(color="#8A8A8A", width=1, dash="dot"),
                      annotation_text=label, annotation_position="top left",
                      annotation_font_size=10)


def _limit_colours(limit_set) -> dict[str, str]:
    from hcwc.core.limits import Group
    out: dict[str, str] = {}
    for group in Group:
        members = [n for n, g in zip(limit_set.names, limit_set.groups) if g is group]
        for name, colour in zip(members, theme.element_shades(group.value, len(members))):
            out[name] = colour
    return out


def _spill(result, apex: float) -> float | None:
    for j, limit in enumerate(result.limit_set.limits):
        if "spill" in limit.name.lower():
            return float(apex + np.median(result.sampled_m[:, j]))
    return None
