"""One limit's input block — built once, instantiated twelve times on tab 3.0.

This is the component the restructure exists to make possible. The old tab 3.0 put every limit in a
`st.data_editor`, which forced all of them into one shape: four numeric columns whose meaning
changed depending on a distribution named in a neighbouring cell, and a *Source* cell that had to
be edited to reveal a whole calculator. Nothing about that is discoverable, and the calculator it
hid was one the author of the tool could not find.

A block is five things, in the order an assessor thinks about them:

1. **Is it present at all** — ``P(active)``, defaulting to 100 %.
2. **What space is it stated in** — m TVDSS for a mapped surface, metres of column for a capacity.
   See :class:`hcwc.core.limits.Limit`; the choice is per limit because the two are natural for
   different mechanisms.
3. **Which distribution**, and only the parameters that distribution actually takes. A field that
   does not apply is not shown greyed out — it is not there, because a visible empty box is an
   invitation to fill it in.
4. **What that means as numbers** — P100/P90/P50/P10/P0 and the mean, in the exceedance convention
   used everywhere else in this tool.
5. **What it looks like** — histogram and cumulative exceedance on one figure.

The block never mutates anything global. It returns a :class:`hcwc.core.limits.Limit` or ``None``,
and the caller decides what to do with it. That is what lets the same code serve a fixed named limit
and a user-added one.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from hcwc.core import engine
from hcwc.core.limits import COLUMN, DEPTH, DepthDistribution, Group, Limit
from hcwc.ui import theme

#: Distribution -> (label, parameter specs). Each spec is (key, label, default-rule).
#: Ordered by how often an assessor reaches for them, not alphabetically.
FORMS: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    "pert": ("PERT (min / mode / max)",
             (("minimum", "Min"), ("mode", "Mode"), ("maximum", "Max"))),
    "beta_subj": ("BetaSubj (min / mode / mean / max)",
                  (("minimum", "Min"), ("mode", "Mode"),
                   ("mean", "Mean"), ("maximum", "Max"))),
    "normal_alt": ("Normal from two percentiles",
                   (("x1", "P10 value"), ("x2", "P90 value"))),
    "uniform": ("Uniform (min / max)", (("minimum", "Min"), ("maximum", "Max"))),
    "beta_general": ("BetaGeneral (α1 / α2 / min / max)",
                     (("alpha1", "α1"), ("alpha2", "α2"),
                      ("minimum", "Min"), ("maximum", "Max"))),
    "fixed": ("Fixed value", (("value", "Value"),)),
}

#: Human names for the calculators a block can offer.
LABELS = {"charge": "From charge volume", "seal": "From seal capacity",
          "seal_as_top": "Same as the top seal",
          "fracture": "From fracture pressure",
          "empirical": "From the NCS data"}

#: The exceedance fractiles shown under every block. P100 is the shallowest outcome and P0 the
#: deepest, matching the GeoX export and the rest of the tool. Getting this backwards is the one
#: mistake that would survive silently, so the convention is stated on the table itself.
FRACTILES: tuple[int, ...] = (100, 90, 50, 10, 0)


def stats_row(samples: np.ndarray) -> dict[str, float]:
    """P100/P90/P50/P10/P0 and the mean, in the **exceedance** convention.

    ``P90`` is the value 90 % of realisations are *deeper* than, so it is the shallow end. One
    estimator for every percentile the app prints, :func:`hcwc.core.engine.weighted_percentiles`
    (Hazen midpoints, unit weights), since 18 Sep 2026; the linear order statistics this used
    to read differed from the engine's in the last digit.
    """
    values = engine.weighted_percentiles(np.asarray(samples, dtype=float), None,
                                         np.asarray(FRACTILES, dtype=float))
    out = {f"P{p}": float(v) for p, v in zip(FRACTILES, values)}
    out["Mean"] = float(np.mean(samples))
    return out


def _defaults(lo: float, hi: float, mode: float | None = None) -> dict[str, float]:
    """Sensible starting parameters spanning ``lo`` to ``hi``, for every parameter any form takes.

    One dict covering all forms, so switching distribution never blanks the inputs or throws — an
    assessor changes their mind about the shape far more often than about the range.

    ``normal_alt`` gets values at the tenth and ninetieth of the span because its percentiles are
    pinned at P10/P90 below; an assessor states two *values*, not two quantiles.

    **The mode is deliberately not at the midpoint.** ``BetaSubj`` has no solution when the mode
    sits exactly halfway between min and max — the four points then determine symmetry and nothing
    else. A midpoint default would mean selecting BetaSubj threw an error before the user had typed
    anything, so the default is mildly right-skewed instead, and the mean is offset from the mode
    for the same reason.
    """
    span = hi - lo
    # An explicit mode wins where a spec states one. Everything derived from the mode moves with
    # it -- the mean stays offset, for the BetaSubj reason above -- so a stated mode does not
    # leave a mean sitting on the wrong side of it.
    peak = lo + 0.40 * span if mode is None else float(mode)
    mean = peak + 0.05 * span
    return {"minimum": lo, "maximum": hi,
            "mode": peak, "mean": mean, "value": lo + 0.5 * span,
            "alpha1": 2.0, "alpha2": 2.0,
            "x1": lo + 0.1 * span, "x2": lo + 0.9 * span}


def _param_key(params: dict) -> tuple:
    """A distribution's parameters as something hashable, for the preview cache.

    Most parameters are floats, but ``empirical`` carries two arrays, and an array is neither
    hashable nor comparable — so they become tuples, which ``np.asarray`` reads back identically.
    """
    return tuple(sorted((k, tuple(np.ravel(v).tolist()) if np.ndim(v) else float(v))
                        for k, v in params.items()))


@st.cache_data(show_spinner=False, max_entries=256)
def _preview_samples(kind: str, params: tuple, n: int) -> np.ndarray:
    """The twenty thousand draws behind one limit's preview, cached on what they depend on.

    They depend on the distribution and nothing else — the seed is fixed at 1 — so redrawing them
    on every rerun was the second-largest cost on the page after the browser payload: twelve
    limits, ~0.48 s of `pert_ppf` and `beta_general_ppf` per interaction, all of it recomputing
    identical numbers. Editing one limit now costs one limit's worth of sampling instead of twelve.

    Kept at twenty thousand rather than thinned. The cheaper fix was a smaller sample (4 000 draws
    measured at 20 ms against 95 ms) but it buys a rougher histogram and noisier percentiles for a
    saving the cache already makes on eleven of the twelve.
    """
    return DepthDistribution(kind, dict(params)).ppf(np.random.default_rng(1).random(n))


def _figure(samples: np.ndarray, colour: str, unit: str) -> go.Figure:
    """Histogram and cumulative exceedance on one figure, twin axes.

    **The x-axis is never reversed, including for a depth-stated limit.** The depth-down convention
    belongs to the *vertical* axis; applied here it puts shallow on the right and makes the
    exceedance curve rise left to right, which reads backwards. Left to right is increasing value
    and the exceedance falls across it — the shape of the reference figure this is modelled on, and
    the shape of every exceedance curve elsewhere in the tool.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # **Binned here, not in the browser.** `add_histogram` ships every sample and lets plotly count
    # them client-side: twenty thousand numbers per limit, twelve limits, on every rerun. The
    # picture is fifty bars either way, so the bars are what gets sent -- 20 000 points down to 50,
    # and the page's payload from 6.7 MB to about a megabyte.
    counts, edges = np.histogram(samples, bins=50)
    centres = 0.5 * (edges[:-1] + edges[1:])
    fig.add_bar(x=centres, y=counts, name="Frequency", marker_color=colour, opacity=0.75,
                width=float(edges[1] - edges[0]), hovertemplate="%{y:,} of the sample<extra></extra>")

    grid = np.linspace(float(np.min(samples)), float(np.max(samples)), 200)
    exceedance = engine.exceedance(samples, grid)
    fig.add_scatter(x=grid, y=exceedance, name="Probability of exceedance", mode="lines",
                    line=dict(color=theme.shade_hex(colour, -0.35), width=2.5), secondary_y=True)

    # `add_vline` costs about 4 ms each -- it re-walks every axis-spanning shape on the figure
    # every time it is called. Forty-five of them across the page is 190 ms of the render, against
    # 1 ms for the same lines declared once. Same picture, same annotations.
    rules, notes = [], []
    for label, value in zip(("P90", "P50", "P10"),
                            engine.weighted_percentiles(samples, None, [90.0, 50.0, 10.0])):
        value = float(value)
        rules.append(dict(type="line", x0=value, x1=value, y0=0, y1=1, yref="paper",
                          line=dict(color="#888", width=1, dash="dash")))
        notes.append(dict(x=value, y=1, yref="paper", text=f"{label}: {value:,.0f}",
                          showarrow=False, font=dict(size=10), yanchor="bottom"))

    fig.update_layout(height=300, margin=dict(t=30, b=10), shapes=rules, annotations=notes,
                      legend=dict(orientation="h", y=1.15), bargap=0.02)
    fig.update_xaxes(title_text=unit)
    fig.update_yaxes(title_text="Frequency", secondary_y=False)
    fig.update_yaxes(title_text="Probability of exceedance", range=[0, 1.02], secondary_y=True)
    return fig


def render(name: str, group: Group, *, key: str, default_kind: str = COLUMN,
           default_form: str = "pert", span: tuple[float, float] = (50.0, 300.0),
           default_p_active: float = 1.0, default_mode: float | None = None,
           n_preview: int = 20_000,
           colour: str | None = None, help_text: str = "", default_source: str = "Typed",
           computed=None) -> Limit | None:
    """Render one limit's inputs and return the :class:`Limit`, or ``None`` if it is switched off.

    ``computed`` is an optional ``{name: callable}`` of calculators, each returning a
    ``(DepthDistribution, p_active, summary)`` triple. A radio at the top of the block chooses
    between *Typed* and any of them — the replacement for the buried Source cell, and the reason
    the charge filling, the seal capacity and the empirical fit are reachable at all.

    ``default_source`` picks which of them the block opens on. It is *Typed* everywhere except the
    top seal, where the calculator is the better answer than anything an assessor would type: `P_c`
    goes as `1/r`, so the spread on pore-throat radius dominates, and a typed capacity hides that.
    """
    colour = colour or theme.PILLAR_COLOURS[group.value]
    include = st.toggle("Include this limit", value=True, key=f"{key}_on",
                        help="Off removes the mechanism from the model entirely. P(active) = 0 "
                             "differs: it keeps the mechanism in the diagnostic as one that never "
                             "applies.")
    if not include:
        st.caption("Excluded from the model.")
        return None
    if help_text:
        st.caption(help_text)

    source = "Typed"
    if computed:
        # Seeded once, then owned by the widget -- passing an index every run would fight a
        # loaded prospect that had chosen differently.
        if default_source in computed:
            st.session_state.setdefault(f"{key}_src", default_source)
        source = st.radio("Distribution from", ["Typed", *computed], horizontal=True,
                          key=f"{key}_src",
                          format_func=lambda s_: LABELS.get(s_, s_),
                          help="Typed takes the distribution as entered below. A calculator "
                               "derives it from physical inputs and replaces those controls.")

    if source != "Typed":
        result = computed[source](key)
        if result is None:
            return None
        distribution, p_active, summary = result
        note = f"computed: {summary}"
        kind = default_kind
    else:
        c1, c2, c3 = st.columns([1, 1, 2])
        p_active = c1.number_input("P(active)", 0.0, 1.0, default_p_active, 0.05,
                                   key=f"{key}_pa",
                                   help="The chance the mechanism is present at all. Below 1 the "
                                        "limit applies in that share of realisations, and its "
                                        "curve on tab 4.0 flattens at this value.")
        kind = c2.selectbox("Stated as", [COLUMN, DEPTH], key=f"{key}_kind",
                            index=[COLUMN, DEPTH].index(default_kind),
                            format_func=lambda k: ("m column below apex" if k == COLUMN
                                                   else "m TVDSS (mapped surface)"),
                            help="A capacity (what a seal holds, what a fault leaks past) is a "
                                 "column height and does not move when the apex pick moves. A "
                                 "mapped surface (spill, a juxtaposition window, a pinch-out) is "
                                 "a depth.")
        form = c3.selectbox("Distribution", list(FORMS), key=f"{key}_form",
                            index=list(FORMS).index(default_form),
                            format_func=lambda f: FORMS[f][0])

        lo, hi = span
        base = _defaults(lo, hi, default_mode)
        cols = st.columns(len(FORMS[form][1]))
        params: dict[str, float] = {}
        for col, (param_key, label) in zip(cols, FORMS[form][1]):
            params[param_key] = col.number_input(
                f"{label} ({'m TVDSS' if kind == DEPTH else 'm'})",
                value=float(base[param_key]), step=5.0, key=f"{key}_{form}_{param_key}")
        if form == "normal_alt":
            # The percentiles are fixed at P10/P90 rather than asked for. An assessor states two
            # values; making them also state which quantiles those are invites a mismatch between
            # the label and the number.
            params |= {"p1": 0.10, "p2": 0.90}

        try:
            distribution = DepthDistribution(form, params)
            preview = distribution.ppf(np.linspace(0.001, 0.999, 64))
            if not np.isfinite(preview).all():
                raise ValueError("the parameters give a non-finite value somewhere")
        except ValueError as exc:
            st.error(f"{name}: {exc}")
            return None
        note = ""

    try:
        limit = Limit(name, group, float(p_active), distribution, note=note, kind=kind)
    except ValueError as exc:
        st.error(f"{name}: {exc}")
        return None

    samples = _preview_samples(distribution.kind, _param_key(distribution.params), n_preview)
    stats = stats_row(samples)
    metrics = st.columns(len(stats))
    for col, (label, value) in zip(metrics, stats.items()):
        col.metric(label, f"{value:,.0f}")
    st.plotly_chart(_figure(samples, colour, limit.unit_label),
                    width="stretch", key=f"{key}_fig")
    st.caption(
        f"{limit.unit_label}. Percentiles are exceedance: P90 is the shallow end, the value 90 % "
        f"of realisations come out deeper than, as in the export and every other figure. This "
        f"preview is the limit on its own; its effect on the contact depends on the others it "
        f"competes with."
    )
    return limit
