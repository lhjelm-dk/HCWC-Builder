"""One limit's input block — built once, instantiated twelve times on tab ③.

This is the component the restructure exists to make possible. The old tab ③ put every limit in a
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
          "empirical": "From the NCS data"}

#: The exceedance fractiles shown under every block. P100 is the shallowest outcome and P0 the
#: deepest, matching the GeoX export and the rest of the tool. Getting this backwards is the one
#: mistake that would survive silently, so the convention is stated on the table itself.
FRACTILES: tuple[int, ...] = (100, 90, 50, 10, 0)


def stats_row(samples: np.ndarray) -> dict[str, float]:
    """P100/P90/P50/P10/P0 and the mean, in the **exceedance** convention.

    ``P90`` is the value 90 % of realisations are *deeper* than, so it is the shallow end. That is
    numpy's 10th percentile, and the inversion is done here once rather than at every call site.
    """
    out = {f"P{p}": float(np.percentile(samples, 100 - p)) for p in FRACTILES}
    out["Mean"] = float(np.mean(samples))
    return out


def _defaults(lo: float, hi: float) -> dict[str, float]:
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
    return {"minimum": lo, "maximum": hi,
            "mode": lo + 0.40 * span, "mean": lo + 0.45 * span, "value": lo + 0.5 * span,
            "alpha1": 2.0, "alpha2": 2.0,
            "x1": lo + 0.1 * span, "x2": lo + 0.9 * span}


def _figure(samples: np.ndarray, colour: str, unit: str) -> go.Figure:
    """Histogram and cumulative exceedance on one figure, twin axes.

    **The x-axis is never reversed, including for a depth-stated limit.** The depth-down convention
    belongs to the *vertical* axis; applied here it puts shallow on the right and makes the
    exceedance curve rise left to right, which reads backwards. Left to right is increasing value
    and the exceedance falls across it — the shape of the reference figure this is modelled on, and
    the shape of every exceedance curve elsewhere in the tool.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_histogram(x=samples, nbinsx=50, name="Frequency", marker_color=colour, opacity=0.75)

    grid = np.linspace(float(np.min(samples)), float(np.max(samples)), 200)
    exceedance = (samples[None, :] >= grid[:, None]).mean(axis=1)
    fig.add_scatter(x=grid, y=exceedance, name="Probability of exceedance", mode="lines",
                    line=dict(color=theme.shade_hex(colour, -0.35), width=2.5), secondary_y=True)

    for label, value in (("P90", np.percentile(samples, 10)),
                         ("P50", np.percentile(samples, 50)),
                         ("P10", np.percentile(samples, 90))):
        fig.add_vline(x=float(value), line=dict(color="#888", width=1, dash="dash"),
                      annotation_text=f"{label}: {value:,.0f}", annotation_font_size=10)

    fig.update_layout(height=300, margin=dict(t=30, b=10),
                      legend=dict(orientation="h", y=1.15), bargap=0.02)
    fig.update_xaxes(title_text=unit)
    fig.update_yaxes(title_text="Frequency", secondary_y=False)
    fig.update_yaxes(title_text="Probability of exceedance", range=[0, 1.02], secondary_y=True)
    return fig


def render(name: str, group: Group, *, key: str, default_kind: str = COLUMN,
           default_form: str = "pert", span: tuple[float, float] = (50.0, 300.0),
           default_p_active: float = 1.0, n_preview: int = 20_000,
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
                        help="Off removes the mechanism from the model entirely. That is different "
                             "from P(active) = 0, which keeps it in the diagnostic as a mechanism "
                             "that never bites.")
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
                          help="Each calculator is right here rather than behind a menu — the "
                               "previous arrangement hid them well enough that they could not be "
                               "found.")

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
                                        "limit only bites in that share of realisations, and its "
                                        "curve on tab ④ flattens at exactly this value.")
        kind = c2.selectbox("Stated as", [COLUMN, DEPTH], key=f"{key}_kind",
                            index=[COLUMN, DEPTH].index(default_kind),
                            format_func=lambda k: ("m column below apex" if k == COLUMN
                                                   else "m TVDSS (mapped surface)"),
                            help="A capacity — what a seal holds, what a fault leaks past — is a "
                                 "column height and does not move when the apex pick moves. A "
                                 "mapped surface — spill, a juxtaposition window, a pinch-out — is "
                                 "a depth.")
        form = c3.selectbox("Distribution", list(FORMS), key=f"{key}_form",
                            index=list(FORMS).index(default_form),
                            format_func=lambda f: FORMS[f][0])

        lo, hi = span
        base = _defaults(lo, hi)
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
            st.error(f"**{name}** — {exc}")
            return None
        note = ""

    try:
        limit = Limit(name, group, float(p_active), distribution, note=note, kind=kind)
    except ValueError as exc:
        st.error(f"**{name}** — {exc}")
        return None

    samples = distribution.ppf(np.random.default_rng(1).random(n_preview))
    stats = stats_row(samples)
    metrics = st.columns(len(stats))
    for col, (label, value) in zip(metrics, stats.items()):
        col.metric(label, f"{value:,.0f}")
    st.plotly_chart(_figure(samples, colour, limit.unit_label),
                    use_container_width=True, key=f"{key}_fig")
    st.caption(
        f"**{limit.unit_label}.** Percentiles are exceedance: **P90 is the shallow end** — the "
        f"value 90 % of realisations come out deeper than — matching the export and every other "
        f"figure here. This preview is the limit *on its own*; what it does to the contact depends "
        f"on the others it competes with."
    )
    return limit
