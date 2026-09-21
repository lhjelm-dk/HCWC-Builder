"""Tab 7.0 Export: the percentile table, WellVolPOS, every figure as images, the one-page report (from app.py, 18 Sep 2026)."""
from __future__ import annotations

import numpy as np
import streamlit as st

from hcwc.core import decompose as dc
from hcwc.core import pos, trust
from hcwc.io import geox, report
from hcwc.io import wellvolpos as wvp
from hcwc.plotting.app.colours import limit_colours
from hcwc.ui import numbering, sources, theme
from hcwc.ui import run as engine_run
from hcwc.ui.numbering import Numbering


def render() -> None:
    n8 = Numbering(7)
    theme.heading(7, "1 · 101-percentile export")
    st.markdown(
        "The GeoX 101-fractile format: two columns, `Percentile` and `Value`, running P100 → P0 "
        "in the exceedance convention, so P100 is the shallowest contact. Reversed, every contact "
        "GeoX imports would invert without an error anywhere, so the convention is asserted in "
        "the test suite.\n\n"
        "The same table is the planned hand-off to [SCOPE-HC](https://scope-hc.streamlit.app), "
        "which would then take its contact distribution from here rather than from a typed "
        "three-point estimate."
    )
    e1, e2 = st.columns([2, 1])
    _overlay = st.session_state.get("dhi_overlay")
    _has_dhi = bool(st.session_state.get("dhi_on")) and _overlay is not None
    if _has_dhi:
        # No default. Until this existed the export was silently geological even with a DHI on,
        # so a file handed to GeoX for a DHI prospect was the wrong distribution and nothing said
        # so. A pre-selected answer would reintroduce exactly that, one click further away.
        basis = e1.radio("Which distribution?", ["— choose —", theme.GEOLOGICAL, theme.GIVEN_DHI],
                         horizontal=True, key="export_basis",
                         help="They are different distributions and the numbers alone do not say "
                              "which is which. The choice goes in the filename and in the "
                              "provenance line inside the file.")
    else:
        basis = theme.GEOLOGICAL
        e1.markdown(f"Basis &nbsp; {theme.basis_tag(theme.GEOLOGICAL)} &nbsp; "
                    f"<span style='opacity:.7'>no DHI on this prospect</span>",
                    unsafe_allow_html=True)
    mode = e2.radio("Tail treatment", ["truncate", "raw"], horizontal=True,
                    help="P0 and P100 from a Monte Carlo are the sample minimum and maximum, the "
                         "least stable statistics in the run. Truncating at P0.5/P99.5 estimates "
                         "the endpoints from about 50 realisations instead of one.")

    limit_set = st.session_state.get("limit_set")
    if limit_set is None:
        st.info("The export needs the limits on tab 3.0.")
    elif basis == "— choose —":
        st.warning(
            "This prospect has a DHI, so there are two contact distributions and they are not "
            "interchangeable. The export waits for a choice. Nothing is offered by default: a "
            "bare table of contact depths looks identical either way, and the wrong one in a "
            "volumetrics package is an error nothing downstream can catch."
        )
    else:
        result = engine_run.current(limit_set)
        # On the given-the-DHI basis every number in this section carries both updates: the
        # geometry in the posterior weights and the evidence index in P(G | s). Until 21 Sep 2026
        # the element curves and the one-page sheet took the geological result under the DHI
        # label (Lars, 21 Sep 2026).
        _posterior = st.session_state.get("dhi_posterior") if basis == theme.GIVEN_DHI else None
        # `st.cache_data` hands back a copy, so the posterior's run is matched on content.
        _weights = (np.asarray(_posterior.weights, dtype=float)
                    if _posterior is not None and _posterior.result.n == result.n
                    and np.array_equal(_posterior.result.contact_m, result.contact_m) else None)
        _p_g_updated = (float(_overlay["p_g_given_amplitude"])
                        if _weights is not None and "p_g_given_amplitude" in _overlay else None)
        if basis == theme.GIVEN_DHI:
            samples = np.asarray(_overlay["contact_samples"], dtype=float)
        else:
            samples = result.contact_m[result.above_minimum]
        exp = geox.percentile_table(samples, tail_mode=mode, basis=basis)
        n8.table(exp.table,
                 f"{theme.basis_tag(basis)} &nbsp; The built contact distribution, h ≥ h_min "
                 f"only. {exp.provenance}", height=280)
        st.download_button(
            "Download CSV", exp.to_csv(),
            f"hcwc_percentiles_{basis.replace(' ', '_')}.csv", "text/csv")

        # ------------------------------------------------------------- WellVolPOS
        theme.heading(7, "2 · To WellVolPOS")
        st.markdown(
            "Two files, because they are two different things. The trial table is one row per "
            "realisation in WellVolPOS's canonical column names and units, so its importer maps "
            "every column with nothing to configure. The element curves are not per-trial data; "
            "they are the chance-against-depth curve per risk element from tab 4.0, which "
            "WellVolPOS cannot compute for itself because it never sees the competing limits."
        )

        try:
            # The grid on tab (3), not the shipped CSV -- an export describing a
            # structure the assessor had replaced would be a quiet lie.
            area_table = sources.current_area_depth()
            if area_table is None:
                raise FileNotFoundError
        except FileNotFoundError:
            area_table = None

        trials = wvp.trial_table(result, area_table)
        w1, w2 = st.columns(2)
        w1.metric("Trials exported", f"{len(trials):,}",
                  f"of {result.n:,}, h ≥ h_min only", delta_color="off")
        w2.metric("Columns WellVolPOS reads", f"{len(trials.columns)}",
                  "mapped with no configuration", delta_color="off")
        n8.table(trials.head(12), "The first twelve rows. Column names and units are "
                                  "WellVolPOS's canonical set, verified against its own adapter in "
                                  "the test suite.", height=260)
        st.download_button("Download trial table (CSV)", trials.to_csv(index=False),
                           "hcwc_trials.csv", "text/csv")

        st.warning(
            "This is a partial trial set, and WellVolPOS says so on import. It requires "
            "`resource` in MMboe, and this tool cannot produce one: a resource needs net-to-gross, "
            "porosity, saturation, a formation volume factor and a recovery factor, none of which "
            "is a contact-depth question.\n\n"
            "A made-up column written to get past the importer would compute every number "
            "downstream from fiction with nothing looking broken. The resource joins on from "
            "[SCOPE-HC](https://scope-hc.streamlit.app), which does the volumetrics, in trial "
            "order: row n here is row n there only where both were run on the same seed and "
            "trial count."
        )

        element_pos = st.session_state.get("element_pos")
        if element_pos is None:
            st.info("The element-curve export needs the element risk on tab 2.0.")
        else:
            curves = wvp.element_curve_table(
                dc.decompose(result, weights=_weights),
                dc.element_pos_given_index(element_pos, _p_g_updated))
            n8.table(curves.iloc[::20], "Chance against depth, one column per element, plus the "
                                        "whole-prospect curve read directly from the contact "
                                        "distribution. Every twentieth row shown."
                                        + (" Given the DHI: the element chances carry the "
                                           "evidence-index update spread by the allocation "
                                           "rule, the curves the posterior weights (8.1.6)."
                                           if _weights is not None else ""), height=240)
            st.download_button("Download element curves (CSV)", curves.to_csv(index=False),
                               "hcwc_element_curves.csv", "text/csv")
        st.caption(wvp.provenance(result, int(st.session_state.get("seed", 20260825)),
                                  int(st.session_state.get("n_trials", 10_000))))

        # ------------------------------------------------------------- figures
        theme.heading(7, "3 · Every figure, as images")
        _figs = st.session_state.get(numbering.FIGURES_KEY) or {}
        st.markdown(
            f"{len(_figs)} figures were drawn on this run, and each is exported under its own "
            f"number: `Figure_4-3.png`, not `newplot.png`. Rendered at 1600 px and 2× device "
            f"scale, which is enough for a slide or a printed page.\n\n"
            f"The camera button on any figure does one at a time, in the browser, at the same "
            f"resolution and with the same filename. This button does the set."
        )
        if not _figs:
            st.info("No figures yet. Only figures that rendered this run can be exported, since "
                    "a stale one would be worse than a missing one; they appear as their tabs "
                    "are visited.")
        elif st.button("Render every figure to PNG", key="render_figures"):
            import io as _io
            import zipfile as _zipfile
            _buffer = _io.BytesIO()
            _failed: list[str] = []
            _progress = st.progress(0.0, text="Rendering…")
            with _zipfile.ZipFile(_buffer, "w", _zipfile.ZIP_DEFLATED) as _zf:
                for _i, (_label, (_fig, _)) in enumerate(
                        sorted(_figs.items(), key=lambda kv: numbering.figure_order(kv[0])),
                        start=1):
                    try:
                        _png = _fig.to_image(format="png", width=1600, height=900, scale=2)
                    except Exception as _exc:                       # noqa: BLE001 — reported below
                        _failed.append(f"{_label}: {type(_exc).__name__}")
                        continue
                    _zf.writestr(f"{_label.replace(' ', '_').replace('.', '-')}.png", _png)
                    _progress.progress(_i / len(_figs), text=f"Rendering… {_label}")
            _progress.empty()
            if _failed:
                # Named rather than swallowed: a zip that is quietly short of what was asked for is
                # the kind of thing nobody notices until the figure is missing from the report.
                st.warning("These would not render, and are not in the archive:\n\n"
                           + "\n".join(f"- {x}" for x in _failed))
            st.download_button(
                f"Download {len(_figs) - len(_failed)} figures (.zip)", _buffer.getvalue(),
                f"{str(st.session_state.get('prospect_name', 'prospect')).replace(' ', '_')}"
                f"_figures.zip", "application/zip", key="download_figures")
        st.caption(
            "Server-side rendering, via kaleido. A page cannot zip twelve charts, which is why "
            "kaleido is in `requirements.txt`. Where this fails on a deployment, the camera "
            "button on each figure still works, because it never leaves the browser."
        )

        # ------------------------------------------------------------- one page
        theme.heading(7, "4 · One page, for the well proposal")
        _elements = st.session_state.get("element_pos") or {}
        _p_g = (pos.accumulation_chance(_elements) if _p_g_updated is None or not _elements
                else _p_g_updated)
        _p_g_name = "P(G)" if _weights is None else "P(G | s)"
        _f_min = (result.pos if _weights is None
                  else float(_posterior.exceedance(limit_set.min_column_m)[0]))
        st.markdown(
            f"Everything above is a CSV, and a CSV does not travel. This is the inputs, the "
            f"answer, the controlling-limit diagnostic, the trust checks and the provenance on "
            f"one sheet, printable to PDF from the browser.\n\n"
            f"It carries `Prospect POS = {_p_g_name} × P(column ≥ h | G)` = "
            f"{_p_g:.3f} × {_f_min:.3f} = {_p_g * _f_min:.3f} and both terms "
            f"separately, because the conditional term alone is {1 / _p_g if _p_g else 0:.1f}× the "
            f"prospect chance and reads like it."
            + (" On the given-the-DHI basis the sheet reads the posterior: P(G | s) from the "
               "evidence index, the percentiles, the curve and the controlling shares on the "
               "posterior weights." if _weights is not None else "")
        )
        if not _elements:
            st.warning("No element risk is set on tab 2.0, so `P(G)` is 1.0 and the page says so "
                       "in red. Without the four element chances the prospect POS on the sheet is "
                       "the column term alone.")
        _checks = trust.review(result, posterior=(st.session_state.get("dhi_posterior")
                                                  if st.session_state.get("dhi_on") else None))
        _name = st.session_state.get("prospect_name") or limit_set.name or "prospect"
        _html = report.build(
            result,
            report.Provenance(prospect=_name, basis=basis,
                              trials=int(st.session_state.get("n_trials", 10_000)),
                              seed=int(st.session_state.get("seed", 20260825)),
                              source_file=st.session_state.get("_loaded_name", "")),
            checks=_checks, p_geological=_p_g, weights=_weights,
            colours=limit_colours(limit_set),
            note=st.session_state.get("report_note", ""))
        st.text_area("A note for the sheet (optional)", key="report_note", height=68,
                     placeholder="One or two sentences: the seal argument, the analogue, "
                                 "whatever a reader will ask about first.")
        d1, d2 = st.columns(2)
        d1.download_button("Download the one-page summary (HTML)", _html,
                           f"{_name.replace(' ', '_')}_HCWC_summary.html", "text/html",
                           width="stretch")
        # The working record: the same summary, then every figure drawn this run with the caption
        # shown beside it in the app. Built on demand rather than every rerun -- it renders each
        # figure through kaleido, which is about a second apiece.
        if d2.button("Build the full report (with every figure and table)",
                     key="build_full_report",
                     width="stretch"):
            _full, _missing = report.build_full(
                result,
                report.Provenance(prospect=_name, basis=basis,
                                  trials=int(st.session_state.get("n_trials", 10_000)),
                                  seed=int(st.session_state.get("seed", 20260825)),
                                  source_file=st.session_state.get("_loaded_name", "")),
                st.session_state.get(numbering.FIGURES_KEY) or {},
                tables=st.session_state.get(numbering.TABLES_KEY) or {},
                checks=_checks, p_geological=_p_g, weights=_weights,
                colours=limit_colours(limit_set),
                note=st.session_state.get("report_note", ""))
            if _missing:
                st.warning("These figures would not render and are absent from the report "
                           "rather than substituted:\n\n"
                           + "\n".join(f"- {x}" for x in _missing))
            st.download_button("Download the full report (HTML)", _full,
                               f"{_name.replace(' ', '_')}_HCWC_report.html", "text/html",
                               key="download_full_report")
        st.caption(
            "The one-pager is one sheet with two charts at report size and the numbers that "
            "will be quoted. The full report is the working record: the same summary followed "
            "by every figure and table the app drew, in number order, each with its caption, so "
            "a number quoted later can be traced to its exhibit. Figures embed as vector SVG."
        )
        st.caption(
            "HTML rather than PDF: the browser's print dialogue makes the PDF. The file is "
            "self-contained, with no stylesheet, font or script, and the figures are vector.")
