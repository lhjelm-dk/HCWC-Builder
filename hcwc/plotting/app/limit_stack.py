"""Every limit and the answer, on **one** shared depth axis, drawn however you want to see it.

This replaces three figures that were showing the same information three ways: a grid of small
exceedance curves, an overlay of those curves, and a row of violin panels. *"the
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

from typing import NamedTuple

import numpy as np
import plotly.graph_objects as go

from hcwc.core import decompose, engine
from hcwc.core.limits import COLUMN, DEPTH, Limit, convert
from hcwc.plotting.app.colours import limit_colours
from hcwc.ui import theme

MODES = ("Exceedance curves", "Violin", "Half violin", "Histogram", "Points")

#: Vertical space one limit's density occupies, as a share of its lane.
LANE_FILL = 0.86

#: Empty space between the three groups of lanes, in lane widths. The request was for
#: *"the limit distributions and then the dhi distribution (not a limit) and then the one or two
#: resulting distributions ... with just a bit of visual separation"*. The three are different
#: kinds of thing -- twelve competing mechanisms, one piece of evidence, and the answer -- and a
#: reader scanning fourteen identical lanes has nothing to tell them apart. Gap, rule and a label
#: over each group: the gap alone reads as an accident, the rule alone is easy to miss.
GROUP_GAP = 0.9

#: Where the amplitude's own lane is cut off. It is a *ratio* of two kernel densities, so out in the
#: tails it is a small number divided by a smaller one and can take any value at all. Below this
#: share of the prior's peak there are too few realisations for the ratio to mean anything.
EVIDENCE_FLOOR = 0.03

#: Group headings, so the vocabulary is in one place.
LIMITS_GROUP, EVIDENCE_GROUP, RESULT_GROUP = ("Competing limits", "The evidence alone",
                                              "Result")


def default_window(result, space: str, apex: float, spill: float | None) -> tuple[float, float]:
    """The default depth range: 1 % above the apex to 1 % below the spill point.

    Bounding by the *structure* rather than by the deepest thing any limit could have
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
    colour_of = limit_colours(limit_set)

    lo, hi = window if window else default_window(result, space, apex, _spill(result, apex))
    lo, hi = min(lo, hi), max(lo, hi)

    fig = go.Figure()
    if mode == "Exceedance curves":
        _exceedance_mode(fig, result, space, apex, ranked, colour_of, lo, hi, posterior)
    else:
        _density_mode(fig, result, space, apex, ranked, colour_of, lo, hi, mode, every, posterior)

    # **`autorange` and `range` together is `autorange` winning**, which is why the depth slider
    # looked like it worked in four modes and not in **Points**. The other four clip their own data
    # to the window -- the KDE grid runs lo..hi, the histogram passes `range=(lo, hi)` -- so
    # auto-ranging landed on the window by accident. Points drew every realisation, so the axis
    # stretched to 3 600 m on a window set to 2 030-2 400 m. Descending bounds are what reverses a
    # depth axis, so the explicit range does both jobs and `autorange` has to go.
    fig.update_yaxes(title_text=Limit.label_for(space), range=[hi, lo], autorange=False)
    # The lane modes carry a heading over each group, which needs room above the plot.
    fig.update_layout(height=660,
                      # The lane modes need room above for the group headings and a great deal
                      # below for the tick labels: they are limit names, set at -40°, and `b=20`
                      # was cutting every one of them off part-way through. "Resulting HC depth |
                      # given the DHI" is the longest and sets the figure.
                      margin=(dict(t=30, b=20, l=80, r=10) if mode == "Exceedance curves"
                              else dict(t=64, b=150, l=80, r=10)),
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
        # Named for the evidence actually in the weights, not for the amplitude that usually
        # supplies them. A prospect updated by an offset penetration alone reaches this figure
        # too, and a legend entry reading "given the DHI" on it would be false.
        fig.add_scatter(x=updated, y=depths, mode="lines",
                        name=f"Resulting HC depth | {theme.evidence_basis()}",
                        line=dict(color=theme.BASIS_COLOUR[theme.GIVEN_DHI], width=5),
                        hovertemplate=theme.evidence_title()
                        + "<br>%{y:,.0f} · %{x:.0%}<extra></extra>")
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
    grid = np.linspace(lo, hi, 300)

    limits: list[_Lane] = []
    for j, limit in enumerate(result.limit_set.limits):
        drawn = np.where(result.active[:, j], result.sampled_m[:, j], np.nan)
        keep = np.isfinite(drawn)
        drawn = drawn[keep]
        if drawn.size < 2:
            continue
        # The mask has to be carried onto the weights as well. A limit is only drawn in the
        # realisations where it is active, and pairing that subset with the full weight vector
        # would silently pair each value with some other realisation's weight.
        limits.append(_Lane(limit.name, colour_of[limit.name],
                            convert(drawn, frm=COLUMN, to=space, apex_m=apex),
                            None if weights is None else weights[keep]))
    limits.sort(key=lambda s: ranked.index(s.name) if s.name in ranked else len(ranked))

    contact = convert(result.contact_m, frm=DEPTH, to=space, apex_m=apex)
    groups: list[tuple[str, list[_Lane]]] = [(LIMITS_GROUP, limits)]
    if weights is None:
        groups.append((RESULT_GROUP,
                       [_Lane("Resulting HC depth", theme.BASIS_COLOUR[theme.GEOLOGICAL], contact)]))
    else:
        groups.append((EVIDENCE_GROUP,
                       [_Lane("The evidence, on its own", theme.BASIS_COLOUR[theme.GIVEN_DHI],
                              curve=_evidence_curve(contact, weights, grid))]))
        groups.append((RESULT_GROUP, [
            _Lane("Resulting HC depth | geological", theme.BASIS_COLOUR[theme.GEOLOGICAL], contact),
            _Lane(f"Resulting HC depth | {theme.evidence_basis()}",
                  theme.BASIS_COLOUR[theme.GIVEN_DHI], contact, weights)]),
        )

    # Lay the lanes out with a gap between groups, then hang the rules and headings off the gaps.
    centres: list[float] = []
    spans: list[tuple[float, float]] = []
    cursor = 0.0
    for index, (_, lanes) in enumerate(groups):
        if index:
            cursor += GROUP_GAP
        start = cursor
        for _ in lanes:
            centres.append(cursor + 0.5)
            cursor += 1.0
        spans.append((start, cursor))

    flat = [lane for _, lanes in groups for lane in lanes]
    drawn_points = max(1, contact.size // max(int(every), 1))
    for position, (centre, lane) in enumerate(zip(centres, flat)):
        if lane.curve is not None:
            _evidence_lane(fig, lane, centre, grid, mode, lo, hi, drawn_points)
            continue
        values, w = lane.values, lane.weights
        if mode == "Points":
            if w is not None:
                # The one mode that cannot take its weights exactly: it draws realisations, so the
                # posterior has to be shown *as* realisations. Importance resampling is the honest
                # rendering -- a realisation the amplitude favours appears more than once.
                rng = np.random.default_rng(position)
                values = values[rng.choice(values.size, values.size, p=w / w.sum())]
            # Thin what is on screen, not what was sampled. Every tenth realisation of a set that
            # runs to 3 600 m spends most of its budget below a window ending at 2 400 m, so the
            # visible cloud was thinner than the control claimed.
            values = values[(values >= lo) & (values <= hi)]
            if values.size == 0:
                continue
            thinned = values[::max(int(every), 1)]
            jitter = np.random.default_rng(position).uniform(-0.30, 0.30, thinned.size)
            fig.add_scatter(x=centre + jitter, y=thinned, mode="markers", name=lane.name,
                            marker=dict(color=lane.colour, size=3, opacity=0.45),
                            hovertemplate=f"{lane.name}<br>%{{y:,.0f}}<extra></extra>")
            continue
        if mode == "Histogram":
            counts, edges = np.histogram(values, bins=45, range=(lo, hi), weights=w)
            peak = counts.max() or 1
            mids = 0.5 * (edges[:-1] + edges[1:])
            fig.add_bar(x=LANE_FILL * counts / peak, y=mids, orientation="h", name=lane.name,
                        width=(hi - lo) / 45, base=centre - LANE_FILL / 2,
                        marker=dict(color=theme.rgba(lane.colour, 0.75), line_width=0),
                        hovertemplate=f"{lane.name}<br>%{{y:,.0f}}<extra></extra>")
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
                        name=lane.name, fillcolor=theme.rgba(lane.colour, 0.70),
                        line=dict(color=theme.shade_hex(lane.colour, -0.35), width=1),
                        hovertemplate=f"{lane.name}<br>%{{y:,.0f}}<extra></extra>")

    rules = [dict(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper",
                  line=dict(color="#B9B4AA", width=1, dash="dot"))
             for x in [(spans[i][1] + spans[i + 1][0]) / 2 for i in range(len(spans) - 1)]]
    headings = [dict(x=(start + end) / 2, y=1.0, yref="paper", yanchor="bottom", text=title,
                     showarrow=False, font=dict(size=11, color=theme.INK))
                for (title, _), (start, end) in zip(groups, spans)]
    fig.update_xaxes(tickvals=centres, ticktext=[lane.name for lane in flat], tickangle=-40,
                     showgrid=False, zeroline=False, range=[0, cursor])
    fig.update_layout(barmode="overlay", showlegend=False, shapes=rules, annotations=headings)


class _Lane(NamedTuple):
    """One column of the lane modes.

    Either a **sample** — ``values``, optionally with per-realisation ``weights`` — which each mode
    draws in its own way, or a ready-made peak-normalised ``curve``, which is drawn as an outline in
    every mode because there is no sample behind it to bin, jitter or resample.
    """
    name: str
    colour: str
    values: np.ndarray | None = None
    weights: np.ndarray | None = None
    curve: np.ndarray | None = None


def _evidence_curve(contact: np.ndarray, weights: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """What the amplitude says about depth **on its own**, peak-normalised.

    The DHI is drawn beside the limits but not as a limit: it is not
    a competing mechanism, it is the evidence the mechanisms are being judged against. The object
    that belongs in that lane is the likelihood as a function of depth — the factor the update
    multiplies the geology by — and it is recoverable from what is already here without any new
    model. Since ``posterior(z) ∝ prior(z) · E[L | z]``, the ratio of the two kernel densities *is*
    ``E[L | z]`` up to a constant::

        E[L | z]  ∝  KDE(contact, weights=L)(z)  /  KDE(contact)(z)

    Read it as a shape, not as a probability. A likelihood has no area to normalise — dividing it by
    its own integral over whatever window happens to be on screen would make the lane's height
    depend on the depth slider, which is worse than having no scale at all. So it is normalised to
    its own peak, which is what every other lane in these modes already is.

    **Why it is clipped.** Out in the tails this is a small number divided by a smaller one, and a
    handful of realisations can send the ratio anywhere. Below :data:`EVIDENCE_FLOOR` of the prior's
    peak the lane is drawn as zero rather than as noise the reader would have to know to distrust.
    """
    from scipy.stats import gaussian_kde

    if contact.size < 2 or np.allclose(contact, contact[0]) or weights.sum() <= 0:
        return np.zeros_like(grid)
    prior = gaussian_kde(contact)(grid)
    updated = gaussian_kde(contact, weights=weights)(grid)
    out = np.zeros_like(grid)
    live = prior > EVIDENCE_FLOOR * prior.max()
    out[live] = updated[live] / prior[live]
    peak = float(out.max())
    return out / peak if peak > 0 else out


def _evidence_lane(fig, lane: "_Lane", centre: float, grid: np.ndarray, mode: str,
                   lo: float, hi: float, n_points: int) -> None:
    """The amplitude's lane, drawn in whichever idiom the reader has chosen.

    *"the amp alone is a violin even if you select half-violin or histogram or
    points. make consistent."* It was, and it looked like the control had failed on that one lane.

    So the geometry follows the mode and the **distinction is carried by style instead**: a hollow
    shape with a dotted edge, hollow bars, open markers. That distinction still has to be there,
    because this lane is a likelihood and every other lane is a count of realisations -- one says
    *the amplitude prefers this depth by this much*, the others say *this many realisations landed
    here*, and drawing them identically would invite reading the first as the second.

    **Points is the awkward one and is labelled as such.** There are no realisations behind a
    likelihood, so the markers are drawn *from* the curve by inverse-transform sampling rather than
    observed. Open circles, and the caption says so. The alternative -- leaving one lane as a violin
    while the other fourteen became points -- reads as a bug
    rather than as a distinction.
    """
    # Drawn only where the curve is alive. Outside the floor it is zero, and a zero-width polygon
    # is not nothing on screen -- it is a dotted line running the full height of the plot, which
    # reads as a tail the evidence does not have. The shape should simply stop.
    curve = lane.curve
    live = curve > 0
    if not live.any():
        return
    first, last = int(np.argmax(live)), len(live) - int(np.argmax(live[::-1]))
    curve, grid = curve[first:last], grid[first:last]

    if mode == "Points":
        cumulative = np.cumsum(curve)
        if cumulative[-1] <= 0:
            return
        rng = np.random.default_rng(0)
        draws = np.interp(rng.random(n_points), cumulative / cumulative[-1], grid)
        fig.add_scatter(x=centre + rng.uniform(-0.30, 0.30, draws.size), y=draws, mode="markers",
                        name=lane.name,
                        marker=dict(color=lane.colour, size=4, opacity=0.55, symbol="circle-open"),
                        hovertemplate=f"{lane.name}<br>%{{y:,.0f}}<extra></extra>")
        return

    if mode == "Histogram":
        edges = np.linspace(lo, hi, 46)
        mids = 0.5 * (edges[:-1] + edges[1:])
        heights = np.interp(mids, grid, curve, left=0.0, right=0.0)
        fig.add_bar(x=LANE_FILL * heights, y=mids, orientation="h", name=lane.name,
                    width=(hi - lo) / 45, base=centre - LANE_FILL / 2,
                    marker=dict(color=theme.rgba(lane.colour, 0.13),
                                line=dict(color=lane.colour, width=1)),
                    hovertemplate=f"{lane.name}<br>%{{y:,.0f}}<extra></extra>")
        return

    half = mode == "Half violin"
    left = (np.full_like(curve, centre) if half else centre - LANE_FILL / 2 * curve)
    right = centre + (LANE_FILL if half else LANE_FILL / 2) * curve
    fig.add_scatter(x=np.concatenate([right, left[::-1]]),
                    y=np.concatenate([grid, grid[::-1]]), fill="toself", mode="lines",
                    name=lane.name, fillcolor=theme.rgba(lane.colour, 0.13),
                    line=dict(color=lane.colour, width=1.6, dash="dot"),
                    hovertemplate=f"{lane.name}<br>%{{y:,.0f}}<extra></extra>")


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


def _spill(result, apex: float) -> float | None:
    for j, limit in enumerate(result.limit_set.limits):
        if "spill" in limit.name.lower():
            return float(apex + np.median(result.sampled_m[:, j]))
    return None
