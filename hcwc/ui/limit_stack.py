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

    ``posterior`` is the DHI weight vector, one weight per realisation, or ``None``. With one,
    **every curve and every lane is drawn under it** and the geological contact is added beside the
    updated one as a reference, so the figure shows both. See :func:`_exceedance_mode` for why
    weighting the whole family rather than only the answer is the only coherent choice.
    """
    limit_set = result.limit_set
    apex = float(np.median(result.apex_m))
    # Ordering follows the basis too. Ranking the lanes geologically and then drawing them under
    # the posterior puts them in an order the figure itself contradicts.
    ranked = [name for name, _ in engine.limit_ranking(result, weights=posterior)]
    colour_of = _limit_colours(limit_set)

    lo, hi = window if window else default_window(result, space, apex, _spill(result, apex))
    lo, hi = min(lo, hi), max(lo, hi)

    fig = go.Figure()
    if mode == "Exceedance curves":
        _exceedance_mode(fig, result, space, apex, ranked, colour_of, lo, hi, posterior)
    else:
        _density_mode(fig, result, space, apex, ranked, colour_of, lo, hi, mode, every, posterior)

    fig.update_yaxes(title_text=Limit.label_for(space), autorange="reversed", range=[hi, lo])
    fig.update_layout(height=660, margin=dict(t=30, b=20, l=80, r=10),
                      legend=dict(orientation="v", x=1.02), plot_bgcolor="rgba(0,0,0,0)")
    _datums(fig, result, space, apex)
    return fig


def _exceedance_mode(fig, result, space, apex, ranked, colour_of, lo, hi, posterior) -> None:
    """The analytic view: every limit's exceedance curve, and the contact as their lower envelope.

    **Why the whole family is reweighted, not only the answer.** The caption promises that the bold
    line is the *lower envelope* of the thin ones, and that promise is what makes the figure
    readable — a curve to the right of the bold line is a mechanism that never mattered. The
    identity holds under any one weighting (the contact is the shallowest active limit in every
    realisation, so it is shallower than each of them in every realisation) but it does **not** hold
    across two: draw the limits geologically and the answer under the posterior and the bold line
    can cross above a thin one, which the caption then reads as impossible.

    The geological contact is kept beside the updated one, thin and in the geological blue, because
    the size of the gap between them *is* what the amplitude bought.
    """
    depths = np.linspace(min(lo, hi), max(lo, hi), 260)
    as_depth = convert(depths, frm=space, to=DEPTH, apex_m=apex)
    curves = decompose.limit_curves_at_depth(result, as_depth, weights=posterior)
    for name in ranked:
        if curves[name].max() <= 0.001:
            continue
        fig.add_scatter(x=curves[name], y=depths, mode="lines", name=name,
                        line=dict(color=colour_of[name], width=1.9),
                        hovertemplate=f"{name}<br>%{{y:,.0f}} · %{{x:.0%}}<extra></extra>")

    deeper = result.contact_m[None, :] > as_depth[:, None]
    geological = deeper.mean(axis=1)
    if posterior is None:
        fig.add_scatter(x=geological, y=depths, mode="lines", name="Resulting HC depth",
                        line=dict(color=theme.BASIS_COLOUR[theme.GEOLOGICAL], width=5),
                        hovertemplate="Resulting HC depth<br>%{y:,.0f} · %{x:.0%}<extra></extra>")
    else:
        # **This line used to be the weight vector itself.** `posterior` is one weight per
        # realisation -- ten thousand of them -- and it was handed straight to `x` against 260
        # depths. Plotly zips to the shorter of the two, so the dashed "with the DHI" curve was the
        # first 260 raw weights read as probabilities: a squiggle between 0.1 % and 2 % pinned to
        # the left edge of a 0-100 % axis. Meanwhile the bold line labelled "Resulting HC depth"
        # was the *geological* envelope, on a tab whose banner says everything below it carries the
        # amplitude evidence. Both halves of the figure said the wrong thing.
        weights = np.asarray(posterior, dtype=float)
        updated = deeper @ weights / weights.sum()
        fig.add_scatter(x=geological, y=depths, mode="lines", name="Resulting HC depth | geological",
                        line=dict(color=theme.BASIS_COLOUR[theme.GEOLOGICAL], width=2.2,
                                  dash="dash"),
                        hovertemplate="Geological<br>%{y:,.0f} · %{x:.0%}<extra></extra>")
        fig.add_scatter(x=updated, y=depths, mode="lines", name="Resulting HC depth | given the DHI",
                        line=dict(color=theme.BASIS_COLOUR[theme.GIVEN_DHI], width=5),
                        hovertemplate="Given the DHI<br>%{y:,.0f} · %{x:.0%}<extra></extra>")
    fig.update_xaxes(title_text="Probability the contact is deeper", range=[0, 1],
                     tickformat=".0%")


def _density_mode(fig, result, space, apex, ranked, colour_of, lo, hi, mode, every,
                  posterior=None) -> None:
    """One lane per limit, plus the contact, all against the same depth axis.

    With a posterior every lane is weighted by it, for the reason given in
    :func:`_exceedance_mode`, and the geological contact gets a lane of its own next to the updated
    one. Before this the posterior never reached here at all: four of the five display modes drew
    the geological sample on a tab that says it carries the amplitude evidence, and gave the reader
    nothing to notice it by.

    Each mode takes the weights in its own exact form rather than through one resampled sample --
    `np.histogram(weights=)`, `gaussian_kde(weights=)` -- so no Monte Carlo noise is added to a
    picture whose whole job is to be looked at closely. **Points** is the exception and has to be:
    it draws individual realisations, so the posterior is shown by *importance resampling* them,
    which is the honest rendering (a realisation the DHI likes appears more than once).
    """
    weights = None if posterior is None else np.asarray(posterior, dtype=float)
    series: list[tuple[str, np.ndarray, str, np.ndarray | None]] = []
    for j, limit in enumerate(result.limit_set.limits):
        drawn = np.where(result.active[:, j], result.sampled_m[:, j], np.nan)
        keep = np.isfinite(drawn)
        drawn = drawn[keep]
        if drawn.size < 2:
            continue
        # The mask has to be carried onto the weights as well. A limit is only drawn in the
        # realisations where it is active, and pairing that subset with the full weight vector
        # would silently pair each value with some other realisation's weight.
        series.append((limit.name, convert(drawn, frm=COLUMN, to=space, apex_m=apex),
                       colour_of[limit.name], None if weights is None else weights[keep]))
    series.sort(key=lambda s: ranked.index(s[0]) if s[0] in ranked else len(ranked))
    contact = convert(result.contact_m, frm=DEPTH, to=space, apex_m=apex)
    if weights is None:
        series.append(("Resulting HC depth", contact,
                       theme.BASIS_COLOUR[theme.GEOLOGICAL], None))
    else:
        series.append(("Resulting HC depth | geological", contact,
                       theme.BASIS_COLOUR[theme.GEOLOGICAL], None))
        series.append(("Resulting HC depth | given the DHI", contact,
                       theme.BASIS_COLOUR[theme.GIVEN_DHI], weights))

    grid = np.linspace(lo, hi, 300)
    for lane, (name, values, colour, w) in enumerate(series):
        centre = lane + 0.5
        if mode == "Points":
            if w is not None:
                rng = np.random.default_rng(lane)
                values = values[rng.choice(values.size, values.size, p=w / w.sum())]
            thinned = values[::max(int(every), 1)]
            jitter = np.random.default_rng(lane).uniform(-0.30, 0.30, thinned.size)
            fig.add_scatter(x=centre + jitter, y=thinned, mode="markers", name=name,
                            marker=dict(color=colour, size=3, opacity=0.45),
                            hovertemplate=f"{name}<br>%{{y:,.0f}}<extra></extra>")
            continue
        if mode == "Histogram":
            counts, edges = np.histogram(values, bins=45, range=(lo, hi), weights=w)
            peak = counts.max() or 1
            mids = 0.5 * (edges[:-1] + edges[1:])
            fig.add_bar(x=LANE_FILL * counts / peak, y=mids, orientation="h", name=name,
                        width=(hi - lo) / 45, base=centre - LANE_FILL / 2,
                        marker=dict(color=theme.rgba(colour, 0.75), line_width=0),
                        hovertemplate=f"{name}<br>%{{y:,.0f}}<extra></extra>")
            continue
        density = _density(values, grid, w)
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
                     ticktext=[name for name, *_ in series], tickangle=-40,
                     showgrid=False, zeroline=False, range=[0, len(series)])
    fig.update_layout(barmode="overlay", showlegend=False)


def _density(values: np.ndarray, grid: np.ndarray,
             weights: np.ndarray | None = None) -> np.ndarray:
    if np.allclose(values, values[0]):
        out = np.zeros_like(grid)
        out[np.argmin(np.abs(grid - float(values[0])))] = 1.0
        return out
    from scipy.stats import gaussian_kde
    density = gaussian_kde(values, weights=weights)(grid)
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
