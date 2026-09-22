"""The scientific defaults, in one place, each with its name, unit, meaning, provenance and range.

Phase 4 of the clean-up (18 Sep 2026). These numbers were spread over the tabs and the core as
module constants and widget literals; the values are unchanged, and the modules that used them
import them from here. Python rather than YAML on purpose: a default is a scientific statement
with a reason, and the reason belongs next to the number where a reader and a test can see it.

Model *structure* constants stay where their rationale is: the likelihood-ratio caps
(``dhi.R_SINGLE_CHANNEL``, ``dhi.R_CAP``) and the contact-weight ceiling
(``dhi.CONTACT_WEIGHT_CEILING``) are listed in :data:`REGISTER` for the audit but defined in
``hcwc.core.dhi``.

Everything here is a *default* the assessor is expected to overwrite for a real prospect, except
the seed and the trial count, which are run settings.
"""
from __future__ import annotations

from typing import NamedTuple


class Parameter(NamedTuple):
    """One entry of the register: enough to audit the number without opening the code."""
    name: str
    default: object
    unit: str
    meaning: str
    provenance: str
    allowed: str


# ---- run settings ---------------------------------------------------------------------------------
#: Fixed seed, so every number on every tab can be regenerated (`engine.run` default).
SEED = 20260825
#: Realisations per run: the count a reader would reproduce, not a smoother one.
N_TRIALS = 10_000

# ---- the geological accumulation chance -----------------------------------------------------------
#: Element chance defaults as (play, conditional) per risk element, keyed by the element's name
#: as `hcwc.core.limits.Group` values it. Product 0.90 x 1.00 x 0.63 x 0.72 = 0.408, the shipped
#: P(G). Elicited defaults for the worked prospect; closure is 1.00 because the spill point is a
#: limit on tab 3.0 and not a chance (8.1.2).
ELEMENT_CHANCES: dict[str, tuple[float, float]] = {
    "Charge": (1.00, 0.90),
    "Closure": (1.00, 1.00),
    "Reservoir": (0.90, 0.70),
    "Retention": (0.90, 0.80),
}

# ---- the DHI evidence index and its reference distributions ---------------------------------------
#: The hydrocarbon-bearing reference distribution f(s | HC) on the evidence index, as its 1st and
#: 99th percentiles, and the non-hydrocarbon one f(s | NoHC). The reference relationship the tool
#: ships with (E-POS's defaults), editable on tab 5.1.2, not a calibration for any basin; the
#: index is a relative scale with no units and the two cross at 0.
EVIDENCE_INDEX_HC_P1_P99: tuple[float, float] = (-50.0, 100.0)
EVIDENCE_INDEX_NOHC_P1_P99: tuple[float, float] = (-100.0, 50.0)
#: Where the evidence-index slider opens: just above the crossing point, so an untouched slider
#: states barely supportive evidence rather than none. Deliberately not
#: E-POS's own default of 7, which `dhi.DEFAULT_STRENGTH` keeps as a faithful copy.
OPENING_EVIDENCE_INDEX = 5.0

# ---- the contact geometry ------------------------------------------------------------------------
#: c = P(the picked event is the contact | G, contact attributes). 0.36 since 15 Sep 2026,
#: from 0.70: a cautious stated value. Since 20 Sep 2026 the graded attributes open one level
#: lower on fit to structure (:data:`DEFAULT_ATTRIBUTE_LEVELS`, geometric mean 0.25), so an
#: untouched tab shows a stated value beside a graded suggestion that differs from it; the DHI
#: score route still gives 0.36. Range 0.05 to 1.0 on the slider, clipped to [0.01, 0.99] in use.
DEFAULT_CONTACT_GIVEN_HC = 0.36
#: The DHI score at which Monigle et al.'s weighting practice w = min(2 x score, 0.95) returns
#: the shipped c; the comparison on tab 5.1.3 opens in agreement with the stated value. It is
#: not a calibration and not a source of c.
DEFAULT_DHI_SCORE = 0.18
#: The picked contact and its one-sigma error, m, the worked prospect's DHI (tab 5.1.1).
DEFAULT_PICK_M = 2_250.0
DEFAULT_PICK_SIGMA_M = 10.0

#: The three contact attributes after Monigle et al. (2025) and the score each graded level
#: carries. Elicited judgements combined by geometric mean; a heuristic and not a calibration,
#: which is why the result is offered rather than applied.
CONTACT_ATTRIBUTES: dict[str, dict[str, float]] = {
    "Fit to structure": {
        "Flat, conformable, cuts dipping structure": 0.95,
        "Broadly conformable": 0.75,
        "Ambiguous": 0.45,
        "Follows stratigraphy, not structure": 0.15,
    },
    "Amplitude terminations": {
        "Sharp, at the picked depth": 0.90,
        "Moderate": 0.65,
        "Diffuse or long": 0.35,
        "No clear termination": 0.15,
    },
    "Fluid contact reflection": {
        "Clear FCR": 0.95,
        "Weak or possible": 0.70,
        "Absent, and not expected here": 0.60,
        "Absent, where one was expected": 0.30,
    },
}
#: The level each attribute opens on: geometric mean 0.25 (0.15, 0.35, 0.30), deliberately
#: below the stated 0.36 so the two routes are seen to differ.
DEFAULT_ATTRIBUTE_LEVELS: dict[str, str] = {
    "Fit to structure": "Follows stratigraphy, not structure",
    "Amplitude terminations": "Diffuse or long",
    "Fluid contact reflection": "Absent, where one was expected",
}

# ---- the detection function D(h) ----------------------------------------------------------------
#: Logistic in column height: the 50 % column (roughly tuning thickness), the transition width,
#: the ceiling below 1 (a thick column can fail to show), and the false-positive assumption, the
#: barren trap's chance of showing relative to the filled one (0.5 is maximum ignorance; no
#: calibration is known). Defaults of `dhi.DetectionFunction` and the widgets on tab 5.1.3.
DETECTION_H50_M = 25.0
DETECTION_WIDTH_M = 8.0
DETECTION_CEILING = 0.90
DETECTION_FALSE_POSITIVE = 0.50

#: The register: what an auditor reads. Values above are the source; this lists them.
REGISTER: tuple[Parameter, ...] = (
    Parameter("SEED", SEED, "-", "random seed of every run", "fixed 25 Aug 2026 so figures regenerate", "any int"),
    Parameter("N_TRIALS", N_TRIALS, "realisations", "Monte Carlo count per run", "app default", "1 to 100 000 on the tab"),
    Parameter("ELEMENT_CHANCES", ELEMENT_CHANCES, "probability", "play and conditional chance per element; product is P(G)", "elicited, worked prospect", "0 to 1 each"),
    Parameter("EVIDENCE_INDEX_HC_P1_P99", EVIDENCE_INDEX_HC_P1_P99, "index (relative)", "f(s | HC) as P1, P99 of a Gaussian", "the shipped reference relationship (E-POS defaults)", "-200 to 200"),
    Parameter("EVIDENCE_INDEX_NOHC_P1_P99", EVIDENCE_INDEX_NOHC_P1_P99, "index (relative)", "f(s | NoHC) as P1, P99 of a Gaussian", "the shipped reference relationship (E-POS defaults)", "-200 to 200"),
    Parameter("OPENING_EVIDENCE_INDEX", OPENING_EVIDENCE_INDEX, "index (relative)", "where the slider opens", "by decision", "the slider's axis, ended where LR reaches 10"),
    Parameter("DEFAULT_CONTACT_GIVEN_HC", DEFAULT_CONTACT_GIVEN_HC, "probability", "c, the contact attribution, stated", "by decision; a cautious stated value", "0.05 to 1.0"),
    Parameter("DEFAULT_DHI_SCORE", DEFAULT_DHI_SCORE, "score 0 to 1", "Monigle et al.'s DHI score at which their weighting practice returns the shipped c", "2 x 0.18 = 0.36; an external reference, not a calibration", "0 to 1"),
    Parameter("DEFAULT_PICK_M", DEFAULT_PICK_M, "m TVDSS", "the picked contact of the worked prospect", "worked prospect", "inside the closure"),
    Parameter("DEFAULT_PICK_SIGMA_M", DEFAULT_PICK_SIGMA_M, "m", "one-sigma pick and depth-conversion error", "worked prospect", "> 0"),
    Parameter("CONTACT_ATTRIBUTES", "table", "score 0 to 1", "score per graded level of the three contact attributes", "elicited after Monigle et al. (2025); heuristic", "0 to 1"),
    Parameter("DEFAULT_ATTRIBUTE_LEVELS", DEFAULT_ATTRIBUTE_LEVELS, "-", "the level each attribute opens on; geometric mean 0.25", "differs from the stated c on purpose", "a level of each attribute"),
    Parameter("DETECTION_H50_M", DETECTION_H50_M, "m", "column at 50 % detection", "roughly tuning thickness", "1 to 500"),
    Parameter("DETECTION_WIDTH_M", DETECTION_WIDTH_M, "m", "width of the logistic transition", "modelling choice", "1 to 200"),
    Parameter("DETECTION_CEILING", DETECTION_CEILING, "probability", "the most a column can be detected", "below 1 on purpose", "0.05 to 1.0"),
    Parameter("DETECTION_FALSE_POSITIVE", DETECTION_FALSE_POSITIVE, "relative to d", "a barren trap's chance of showing, relative to a filled one", "maximum ignorance; uncalibrated", "0 to 1"),
    Parameter("dhi.R_SINGLE_CHANNEL", 10.0, "ratio", "cap on one channel's likelihood ratio either way", "Simm & Bacon 2014; Simm 2020", "defined in hcwc.core.dhi"),
    Parameter("dhi.R_CAP", 50.0, "ratio", "guard on the combined ratio", "above Kjønsberg et al. 2010's 29", "defined in hcwc.core.dhi"),
    Parameter("dhi.CONTACT_WEIGHT_CEILING", 0.95, "probability", "ceiling on the contact weight", "the ceiling Hood 2019 and Monigle et al. 2025 use in practice", "defined in hcwc.core.dhi"),
)
