"""The numbers the article and the post quote, printed from the code: the single numerical source.

    python scripts/paper_facts.py            prints the facts as a table
    python scripts/paper_facts.py --json     prints them as JSON (paper/figures/facts.json)

The scenario is stated here as data and nowhere else: the app's shipped prospect (tab 2 and
tab 3 defaults, read through the app so the calculators run as they do on screen), at the
article's assessment minimum, evidence index, pick and contact attribution. The app itself
opens at a 5 m minimum and evidence index +5 (``core/defaults``); the article reads the same
prospect at 120 m and +20, and says so. Every number the manuscript uses comes from
:func:`facts`; the figure scripts import the scenario from here.
"""
from __future__ import annotations

import contextlib
import io as _io
import json
import pathlib
import sys
import warnings

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hcwc.core import decompose, dhi, engine, pos  # noqa: E402
from hcwc.core.limits import LimitSet  # noqa: E402

# ---- the scenario, as data --------------------------------------------------------------------
SEED = 20260825
N_TRIALS = 10_000
H_MIN_M = 120.0             #: the article's assessment minimum, m column
EVIDENCE_INDEX = 20.0       #: the article's DHI evidence index (the app opens at +5)
PICK_M = 2_250.0            #: the indicated contact, m TVDSS
PICK_SIGMA_M = 10.0         #: one sigma of the pick and depth conversion, m
CONTACT_ATTRIBUTION = 0.36  #: c = P(the DHI is the contact | G, contact attributes)
WELL_ENTRY_M = 2_230.0      #: the well's reservoir entry depth, m TVDSS
BURIAL_M = 2_500.0          #: the burial depth the benchmark is read at, m TVDSS (tab 2.0)
FACTS_JSON = ROOT / "paper" / "figures" / "facts.json"


def scenario() -> tuple[LimitSet, dict, float]:
    """The shipped prospect read through the app: the limit set, the element chances, P(G)."""
    warnings.filterwarnings("ignore")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=900)
    at.session_state["min_column_input"] = H_MIN_M
    at.session_state["dhi_in_strength"] = EVIDENCE_INDEX
    at.session_state["dhi_in_contact"] = PICK_M
    at.session_state["dhi_in_sigma"] = PICK_SIGMA_M
    with contextlib.redirect_stderr(_io.StringIO()):
        at.run()
    assert not at.exception, "\n".join(str(e.value) for e in at.exception)
    limit_set = at.session_state["dhi_posterior"].result.limit_set
    element_pos = {g.value: float(v) for g, v in at.session_state["element_pos"].items()}
    return limit_set, element_pos, pos.accumulation_chance(element_pos)


def facts() -> dict:
    """Every number the article and the post use, computed from the canonical chain."""
    limit_set, element_pos, p_g = scenario()
    result = engine.run(limit_set, N_TRIALS, seed=SEED)
    strength = dhi.StrengthModel()
    lr = strength.r_at(EVIDENCE_INDEX)
    p_g_given_s = dhi.p_g_given_strength(p_g, lr)
    observation = dhi.DhiObservation(seen=True, contact_m=PICK_M, pick_sigma_m=PICK_SIGMA_M,
                                     p_valid=CONTACT_ATTRIBUTION)
    posterior = dhi.update(result, dhi.DetectionFunction(), observation)

    pct = np.array([90.0, 50.0, 10.0])
    prior_pct = result.percentiles(pct)
    post_pct = posterior.percentiles(pct)
    f_prior = float(result.pos)
    f_post = float(posterior.pos())
    r_well_prior = float(pos.depth_exceedance(result, WELL_ENTRY_M)[0])
    r_well_post = float(pos.depth_exceedance(result, WELL_ENTRY_M, posterior.weights)[0])
    shares = result.controlling_shares(successes_only=True)
    shares = dict(sorted(shares.items(), key=lambda kv: -kv[1]))
    outcomes = dhi.outcome_shares(posterior, p_g_given_s)

    return {
        "scenario": {
            "seed": SEED, "trials": N_TRIALS, "h_min_m": H_MIN_M,
            "evidence_index": EVIDENCE_INDEX, "pick_m": PICK_M, "pick_sigma_m": PICK_SIGMA_M,
            "contact_attribution_c": CONTACT_ATTRIBUTION, "well_entry_m": WELL_ENTRY_M,
            "burial_m": BURIAL_M,
            "element_chances": element_pos,
        },
        "P(G)": p_g,
        "F(h_min) geological": f_prior,
        "POS geological": p_g * f_prior,
        "LR(s)": lr,
        "P(G | s)": p_g_given_s,
        "F_post(h_min)": f_post,
        "POS given the DHI": p_g_given_s * f_post,
        "prior HCWC P90/P50/P10 (m)": [float(v) for v in prior_pct],
        "posterior HCWC P90/P50/P10 (m)": [float(v) for v in post_pct],
        "prior P90-P10 spread (m)": float(prior_pct[2] - prior_pct[0]),
        "posterior P90-P10 spread (m)": float(post_pct[2] - post_pct[0]),
        "effective sample size": float(posterior.effective_sample_size),
        "P(z_HCWC >= z_well | G) geological": r_well_prior,
        "P(z_HCWC >= z_well | G, DHI)": r_well_post,
        "P(well) geological": p_g * r_well_prior,
        "P(well) given the DHI": p_g_given_s * r_well_post,
        "controlling shares (h >= h_min)": {k: float(v) for k, v in shares.items()},
        "six largest controls, summed": float(sum(list(shares.values())[:6])),
        "outcomes": (None if outcomes is None else
                     {"band_m": list(outcomes.band_m), "attribution": outcomes.attribution,
                      "shares": outcomes.shares}),
    }


def _print(f: dict) -> None:
    s = f["scenario"]
    print(f"Scenario: seed {s['seed']}, {s['trials']:,} trials, h_min {s['h_min_m']:.0f} m, "
          f"evidence index {s['evidence_index']:+.0f}, pick {s['pick_m']:,.0f} ± {s['pick_sigma_m']:.0f} m, "
          f"c {s['contact_attribution_c']:.2f}, well {s['well_entry_m']:,.0f} m")
    for k, v in f.items():
        if k in ("scenario", "controlling shares (h >= h_min)", "outcomes"):
            continue
        if isinstance(v, list):
            print(f"{k:38s} " + " / ".join(f"{x:,.1f}" for x in v))
        elif isinstance(v, float) and v <= 1.0 and "m)" not in k and "size" not in k and "LR" not in k:
            print(f"{k:38s} {v:.4f}  ({v:.1%})")
        else:
            print(f"{k:38s} {v:,.1f}" if isinstance(v, float) else f"{k:38s} {v}")
    print("controlling shares, h >= h_min (six largest, then the rest):")
    for i, (k, v) in enumerate(f["controlling shares (h >= h_min)"].items()):
        if v > 0.0005:
            print(f"  {k:28s} {v:.1%}" + ("   ---- six largest" if i == 5 else ""))
    if f["outcomes"]:
        o = f["outcomes"]
        print(f"outcomes (band {o['band_m'][0]:,.0f}-{o['band_m'][1]:,.0f} m, attribution {o['attribution']:.2f}):")
        for k, v in o["shares"].items():
            print(f"  {k:42s} {v:.1%}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    f = facts()
    if "--json" in sys.argv:
        FACTS_JSON.parent.mkdir(parents=True, exist_ok=True)
        FACTS_JSON.write_text(json.dumps(f, indent=2), encoding="utf-8")
        print(FACTS_JSON.relative_to(ROOT))
    else:
        _print(f)
