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


#: How many engine runs to keep. **`st.cache_data` is global to the server process, not per
#: session**, and nothing evicted from it until this was set: on Streamlit Cloud every visitor's
#: prospects accumulated in one cache that never released. One result is 1.8 MB at 10 000 trials
#: and 18 MB at 100 000, so an unbounded cache and a long-lived process is an out-of-memory kill
#: that cannot happen on a laptop, where the process is restarted all day.
#:
#: Four is enough for the only pattern that benefits: the current prospect, plus a couple of recent
#: edits a user is flipping between. A fifth entry buys nothing and costs 18 MB.
MAX_CACHED_RUNS = 4

#: An hour. A cache entry older than that belongs to a session that has moved on, and on a shared
#: process it is holding memory for somebody who left.
CACHE_TTL_S = 3600


@st.cache_data(show_spinner="Running the competing-limits model…",
               max_entries=MAX_CACHED_RUNS, ttl=CACHE_TTL_S)
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
