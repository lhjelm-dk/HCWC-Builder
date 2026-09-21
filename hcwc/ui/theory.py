"""Tab 8.0 Theory: 8.1 the method (docs/THEORY.md, with the references as 8.1.11), 8.2 the article."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from hcwc.io import benchmarks
from hcwc.paths import DOCS, PAPER
from hcwc.ui import dhi_walkthrough, theme
from hcwc.ui import run as engine_run
from hcwc.ui.markdown import render_with_figures
from hcwc.ui.numbering import Numbering


def render() -> None:
    st.markdown(
        "The method, once: an overview of the model, then the sections in the order the model "
        "runs. The operational tabs refer here by section number. The paper is the long-form "
        "version and the bibliography carries the sources."
    )

    # 8.1 is docs/THEORY.md: one `## ` section per numbered part, rendered in order, 8.1.2
    # Model overview to 8.1.11 References. The document's H1 is the 8.1 heading; the italic
    # subtitle before the first section is dropped, the tab intro above says the same. Three
    # pieces of the tool render inside it: the DHI walkthrough under 8.1.10, the worked base-rate
    # example under 8.1.9, and the bibliography (docs/REFERENCES.md) under 8.1.11.
    _theory = DOCS / "THEORY.md"
    if _theory.exists():
        _parts: list[tuple[str, list[str]]] = []
        _preamble: list[str] = []
        _in_subtitle = False
        _h1 = "Theory and methods"
        for _line in _theory.read_text(encoding="utf-8").split("\n"):
            if _line.startswith("# "):
                _h1 = _line[2:].strip()
                continue
            if _line.startswith("## "):
                _parts.append((_line[3:].strip(), []))
            elif _parts:
                _parts[-1][1].append(_line)
            else:
                # Lines before the first section: the overview figure and the map of the
                # sections. The italic subtitle, one paragraph, is dropped; the tab intro
                # above says the same.
                if _line.startswith("*"):
                    _in_subtitle = True
                if not _in_subtitle:
                    _preamble.append(_line)
                if _in_subtitle and not _line.strip():
                    _in_subtitle = False
        _worked_example_slot = None
        theme.heading(8, f"1 · {_h1}")
        _n8 = Numbering(8, sub=1)
        # The overview figure keeps its number, 8.1.1a: the preamble counts as section 1.
        theme.CURRENT_SECTION[(8, 1)] = "1"
        render_with_figures("\n".join(_preamble), DOCS, demote=3, numbering=_n8)
        for _k, (_title, _body) in enumerate(_parts):
            theme.subheading(8, 1, _k + 1, _title)
            render_with_figures("\n".join(_body), DOCS, demote=3, numbering=_n8)
            if _title.startswith("Combined DHI"):
                dhi_walkthrough.render(_n8)
            if _title.startswith("Empirical"):
                _worked_example_slot = st.container()
            if _title == "References":
                _render_references()
        if _worked_example_slot is None:
            _worked_example_slot = st.container()
    else:
        st.info("`docs/THEORY.md` not found in this checkout.")

    # The worked example that used to be section 1 in full, on arrival, above everything else.
    # It is one illustration of one of the five notes above and it now sits where an illustration
    # belongs -- behind its own summary, after the note it illustrates.
    with _worked_example_slot, st.expander(
            "Worked: what multiplying a base rate in would do to this prospect"):
        st.markdown(
            "A base rate is a prior over column height, and the tool already has one, so "
            "multiplying it in counts the same belief twice. A DHI can be a likelihood because "
            "it is an observation of this prospect.\n\n"
            "A prior and a likelihood are the same kind of object, both functions of the unknown. "
            "A likelihood is a use rather than a kind of distribution, and to act as one the data "
            "must have been observed on this prospect.\n\n"
            "The test is therefore not whether the data is a probability but whether it carries "
            "something the model has not already used. Method: see 8.1.9 above; the table below "
            "shows what getting it wrong does to a real prospect."
        )
        _t8_limits = st.session_state.get("limit_set")
        _t8_spill = ([i for i, nm in enumerate(_t8_limits.names) if "spill" in nm.lower()]
                     if _t8_limits is not None else [])
        # `_t8_mine` is the success cases, and an assessment minimum above every achievable column
        # leaves it empty -- the same emptiness tab 6.0 guards, reached by a different route. Checked
        # here rather than at each `np.percentile` below, because none of the four rows means anything
        # without it.
        _t8_have_successes = True
        if _t8_limits is not None and _t8_spill:
            _t8_probe = engine_run.current(_t8_limits)
            _t8_have_successes = bool(_t8_probe.above_minimum.any())
            if not _t8_have_successes:
                st.info(
                    "No realisation reaches the assessment minimum, so there is no column "
                    "distribution to fuse with the benchmark. A lower minimum on tab 2.0 "
                    "restores one."
                )
        if _t8_limits is not None and _t8_spill and _t8_have_successes:
            _t8_result = engine_run.current(_t8_limits)
            _t8_relief = float(np.median(_t8_result.sampled_m[:, _t8_spill[0]]))
            # `or` would take the fallback for a burial of zero, because zero is falsy -- a typed 0
            # silently became 2500 m. Only a genuinely absent value should fall back.
            _t8_stored = st.session_state.get("burial_depth")
            _t8_burial = float(_t8_stored if _t8_stored is not None else 2500.0)
            _t8_mine = _t8_result.column_m[_t8_result.above_minimum]

            _t8_fit = benchmarks._capacity_fit()
            _t8_bench = np.minimum(
                np.exp(np.random.default_rng(11).normal(
                    _t8_fit.intercept + _t8_fit.slope * np.log(_t8_burial), _t8_fit.sigma, 60_000)),
                _t8_relief)
            _t8_fused = benchmarks.shrink_toward(_t8_mine, _t8_bench, 0.5)

            # Histogram densities rather than a KDE: the point is the *width* of the product, which a
            # coarse density carries perfectly well, and it costs nothing on every rerun of this tab.
            _t8_edges = np.linspace(0.0, _t8_relief * 1.02, 220)
            _t8_mid = 0.5 * (_t8_edges[:-1] + _t8_edges[1:])

            def _t8_density(sample):
                # Normalised by hand rather than with `density=True`, which divides by the total and
                # hands back NaNs when that total is zero. A non-empty sample can still put nothing in
                # these bins: the axis runs to the structural relief, and at a high assessment minimum
                # every surviving column sits at or beyond it. NaNs there would read as a distribution
                # rather than as an empty one, and `_t8_pct` below already knows what to do with zeros.
                counts, _ = np.histogram(sample, bins=_t8_edges)
                total = float(counts.sum())
                if total <= 0:
                    return np.zeros(counts.size, dtype=float)
                return counts / np.diff(_t8_edges) / total

            def _t8_pct(density, p):
                cumulative = np.cumsum(density)
                if cumulative[-1] <= 0:
                    return float("nan")
                return float(np.interp(p / 100.0, cumulative / cumulative[-1], _t8_mid))

            _t8_dm, _t8_db = _t8_density(_t8_mine), _t8_density(_t8_bench)
            _t8_product = _t8_dm * _t8_db
            _t8_rows = [
                ("this model", _t8_pct(_t8_dm, 10), _t8_pct(_t8_dm, 50), _t8_pct(_t8_dm, 90)),
                ("the benchmark at this relief", _t8_pct(_t8_db, 10), _t8_pct(_t8_db, 50),
                 _t8_pct(_t8_db, 90)),
                ("the two fused, weight 0.5, as tab 6.0 draws",
                 float(np.percentile(_t8_fused, 10)), float(np.percentile(_t8_fused, 50)),
                 float(np.percentile(_t8_fused, 90))),
                ("multiplied as if the benchmark were a likelihood",
                 _t8_pct(_t8_product, 10), _t8_pct(_t8_product, 50), _t8_pct(_t8_product, 90)),
            ]
            st.dataframe(
                pd.DataFrame([
                    {"": name, "P10": f"{p10:,.0f} m", "P50": f"{p50:,.0f} m",
                     "P90": f"{p90:,.0f} m", "P10–P90 spread": f"{p90 - p10:,.0f} m"}
                    for name, p10, p50, p90 in _t8_rows]),
                hide_index=True, width="stretch", key="t8_likelihood_table")
            st.caption(
                f"Computed from the current prospect, relief {_t8_relief:,.0f} m and burial "
                f"{_t8_burial:,.0f} m, so it can be checked rather than believed.\n\n"
                f"The last row reads against the first two. Multiplying two densities always "
                f"sharpens, which is correct when two independent instruments measure the same "
                f"thing. Here it produces a spread of {_t8_rows[3][3] - _t8_rows[3][1]:,.0f} m, "
                f"tighter than the model's own {_t8_rows[0][3] - _t8_rows[0][1]:,.0f} m, after "
                f"consulting a source whose own spread is "
                f"{_t8_rows[1][3] - _t8_rows[1][1]:,.0f} m. A vaguer opinion has increased the "
                f"certainty, which says the two are not independent evidence."
            )

        st.markdown(
            "One thing in that dataset is a likelihood: not the distribution, the outcomes. They "
            "cannot inform this column, but they can inform what this prospect and those 242 "
            "share, the parameters of the seal-capacity relationship. That is empirical Bayes, "
            "and it is the seal limit\u2019s **Pull this toward the NCS record** on tab 3.0."
        )

    theme.heading(8, "2 · The paper")
    st.markdown(
        "The article, for a reader who does not use the tool: why the contact distribution is "
        "derived rather than chosen, what the controlling mechanism adds, and how a DHI updates "
        "the distribution rather than replacing it. The method in full is 8.1."
    )
    _paper = PAPER / "ARTICLE.md"
    if _paper.exists():
        _paper_text = _paper.read_text(encoding="utf-8")
        st.info(
            "Every number in it is computed rather than typed: the worked prospect is the app's "
            "own default read at a 120 m assessment minimum, and the figures are the app's own, "
            "exported by `scripts/post_images.py`. The long-form manuscript it shortens is "
            "kept as `paper/ARTICLE_LONG_2026-09.md`."
        )
        with st.expander("The source: Markdown, for posting or for a document"):
            st.code(_paper_text, language="markdown")
        render_with_figures(_paper_text, PAPER, demote=2)
    else:
        st.info("`paper/ARTICLE.md` not found in this checkout.")


def _render_references() -> None:
    """The bibliography, docs/REFERENCES.md, under 8.1.11: each `## ` group an unnumbered
    subsection, the entries rendered beneath it."""
    _refs = DOCS / "REFERENCES.md"
    if not _refs.exists():
        st.info("`docs/REFERENCES.md` not found in this checkout.")
        return
    _part: list[str] = []
    for _line in _refs.read_text(encoding="utf-8").split("\n") + ["## "]:
        if _line.startswith("## "):
            if _part:
                render_with_figures("\n".join(_part), DOCS, demote=3)
                _part = []
            if _line.strip() != "##":
                theme.subsection(8, _line[3:].strip())
        elif not _line.startswith("# "):
            _part.append(_line)
