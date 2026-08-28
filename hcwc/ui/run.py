"""One cached engine run, shared by every tab that needs it.

There were three of these — identical bodies in ``results_tab``, ``depth_risk_tab`` and
``dhi_tab``, each with its own ``@st.cache_data``. Streamlit keys its cache **per decorated
function**, so three copies meant three caches, and the same Monte Carlo ran three times on a cold
start: measured at 8.8 s against a 1.4 s warm rerun.

The duplication was invisible precisely because it worked. Each tab got a correct result and the
cache did its job *within* that tab; nothing was wrong except that the work happened three times,
and nothing in the UI could show you that.

**One function, one cache.** Every tab now calls :func:`current`, which reads the trial count and
seed from session state so the three call sites cannot drift apart on their arguments either —
which is the other thing three copies of a signature invite.
"""
from __future__ import annotations

import streamlit as st

from hcwc.core import engine
from hcwc.core.limits import LimitSet

#: Defaults, in one place. Tab ② owns these widgets; every reader needs the same fallbacks for the
#: runs that happen before it has been visited.
DEFAULT_TRIALS = 10_000
DEFAULT_SEED = 20260825


@st.cache_data(show_spinner="Running the competing-limits model…")
def run(payload: dict, n: int, seed: int) -> engine.EngineResult:
    """The engine, cached on the limit set, the trial count and the seed.

    ``payload`` is ``LimitSet.to_dict()`` rather than the object itself: Streamlit hashes the
    arguments, a dict of plain numbers hashes reliably, and a dataclass holding numpy arrays does
    not. Rebuilding the ``LimitSet`` inside costs nothing next to the Monte Carlo.
    """
    return engine.run(LimitSet.from_dict(payload), n, seed)


def current(limit_set: LimitSet) -> engine.EngineResult:
    """The run for the limit set on screen, at the trial count and seed the user chose."""
    return run(limit_set.to_dict(),
               int(st.session_state.get("n_trials", DEFAULT_TRIALS)),
               int(st.session_state.get("seed", DEFAULT_SEED)))
