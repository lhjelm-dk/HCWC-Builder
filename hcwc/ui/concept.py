"""Tab 1.0 Concept: the problem statement, the guide figure and the reading order (from app.py, 18 Sep 2026)."""
from __future__ import annotations

import streamlit as st

from hcwc.paths import DOCS, REFERENCE
from hcwc.ui import cheatsheet, prospect_tab, theme
from hcwc.ui.numbering import Numbering


def render() -> None:
        st.markdown(
            """
    Predrill uncertainty in the depth of the hydrocarbon–water contact is often the largest single
    driver of prospect resource potential, and it sets the probability of encountering hydrocarbons at
    a specific well location.

    This tool models the contact as a competition between geological limiting mechanisms: charge,
    closure and spill, fault seal, top- and base-seal capacity and continuity, tilt-related spillage,
    reservoir pinch-out. Each is assigned a probability of being active and an uncertainty in depth or
    capacity; in each Monte Carlo realisation the shallowest active limit sets the contact, and the
    simulation records which one it was.

    The result answers four questions: where the contact is, which mechanism controls it, how the
    chance changes with depth, and what that means for the assessment minimum and a well drilled to a
    given depth. Where available, the distribution is compared with
    empirical data and updated with DHI or well evidence. Method: see 8.1.
            """
        )

        cheatsheet.render(
            where="concept",
            lead="A quick look at the whole method: one page, nine panels, every figure the app's "
                 "own. The same sheet is above 8.1.1.")

        st.markdown("---\n\nNew here? The figure is the model with the tab each box lives on; the "
                    "tabs follow it left to right, top to bottom.")
        # The guide version of the workflow figure, drawn by scripts/workflow_figure.py: the same
        # boxes as 8.1.2's conceptual one, each line naming the tab and what is entered or read
        # there. Numbered 1.0a, and the section sketch below it 1.1a, from one sequence: a second
        # Numbering(1) would reset the section and number the sketch 1.0b. Tab 2's Numbering
        # resets the exhibit registry, so both stay out of the results export.
        n1 = Numbering(1)
        n1.image(
            DOCS / "figures" / "fig0_workflow_guide.svg",
            "The model as a map of the app. Geological model, the prior: the element chances "
            "(2.0) give P(G), the accumulation chance; given an accumulation, the limits (3.0) "
            "compete and the shallowest active one sets the contact (4.1). DHI evidence, the "
            "update (5.1): the evidence index gives a likelihood ratio that updates P(G); the "
            "contact geometry reweights the same realisations (5.2). Each row ends in the "
            "probability of meeting the threshold, read at the assessment minimum and at the well "
            "(4.1.3, 4.1.4; 5.2.3, 5.2.4); the benchmarks (6.0) are compared beside both contact "
            "distributions; 7.0 exports the percentiles.",
        )
        st.markdown(
            """
    - **2.0 Prospect** — apex, spill point, the element chances and the assessment minimum, the
      smallest column that counts as a discovery at the well.
    - **3.0 HCWC Limiters** — the limits: each with its probability of being active and its depth
      or capacity uncertainty.
    - **4.0 HCWC (geological)** — the contact, its controlling mechanism and the chance against
      depth, from the competing limits alone.
    - **5.0 HCWC (DHI + well)** — the same given a DHI or a well: 5.1 the evidence, 5.2 and 5.3
      the updated results.
    - **6.0 Benchmarks** — the empirical record beside the contact distributions.
    - **7.0 Export** — the contact percentiles for volumetric tools, with the basis stated.
    - **8.0 Theory** — the method behind each box, and the paper.

            """
        )
        # Plan item A3, 15 Sep 2026: the examples were a sentence here pointing at a collapsed
        # expander on tab 2. One click on the first screen is the difference between meeting the
        # tool and reading about it.
        st.markdown("Two shipped examples fill every input for a real prospect: one seal-limited, "
                    "one spill-limited. Either loads with one click and can be edited on **2.0 "
                    "Prospect** and **3.0 HCWC limiters**.")
        prospect_tab.example_buttons("tab1_example")

        theme.heading(1, "1 · What can set a hydrocarbon–water contact")
        concept_png = REFERENCE / "defaults" / "concept.png"
        if concept_png.exists():
            n1.image(
                concept_png,
                "Every mechanism that can stop the column, on one section, with the distribution "
                "of the depth at which it acts. Charge enters from below and fills downward from "
                "the apex, so every capacity is measured from the apex. Figure by Lars Hjelm. "
                "Method: see 8.1.3.",
            )

        # Trimmed 16 Sep 2026 to the operational statement. The argument for reading the chance
        # off the contact distribution, the ranking of effort, the precedent and the limitations
        # are stated once, on tab 8.1 (the explanation map of 16 Sep 2026, tab 1).
        st.markdown(
            "A discovery is a column of at least the assessment minimum set on **2.0 Prospect**; the "
            "chance that the well finds hydrocarbons is the contact distribution read at that depth. Method: see 8.1.4. "
            "Limitations: see 8.1.10."
        )
        st.markdown(
            "Related tools: [E-POS](https://lhjelm-e-pos.streamlit.app) supplies the element chances on "
            "tab 2.0; [SCOPE-HC](https://scope-hc.streamlit.app) computes the volumes; "
            "[WellVolPOS](https://wellvolpos.streamlit.app) turns the export on tab 7.0 into "
            "well-location chance and volume. See 8.1.11."
        )

        st.divider()
        _left, _mid, _right = st.columns([1, 2, 1])
        with _mid:
            st.caption(
                "The tool is free and open source. Contributions towards its development are "
                "welcome and optional."
            )
            # `st.iframe` rather than `components.html`, which is deprecated with a removal
            # date of 2026-06-01 that has already passed. It takes the URL directly, so the
            # widget is no longer a frame inside a frame.
            st.iframe("https://ko-fi.com/lhjelm/?hidefeed=true&widget=true&embed=true&preview=true",
                      height=712)
            # The embed is the most-blocked kind of third-party frame there is: uBlock Origin and
            # Firefox's strict tracking protection both drop ko-fi widgets, and the viewer then sees
            # an empty box with no way to tell whether it is broken or still loading. The link is the
            # part that always works, so it sits beside the embed rather than instead of it.
            st.caption(
                "Not showing? Some ad blockers and Firefox's strict mode drop embedded widgets \u2014 "
                "[ko-fi.com/lhjelm](https://ko-fi.com/lhjelm) works either way."
            )
