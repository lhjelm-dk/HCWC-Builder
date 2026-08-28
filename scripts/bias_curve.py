"""Ship the errors-in-variables curve instead of recomputing it on every cold start.

It is 540 censored MLE fits -- 60 replicates at each of six sigmas -- and it takes about six
seconds. It is also, on inspection, *constant*: the sigmas are a fixed tuple, the generator is
seeded, and nothing the user enters reaches it. It is a demonstration of how the two estimators
behave under depth-conversion error, not a result about anyone's prospect.

So it is computed once and shipped. The file records the sigmas it was computed for, and the app
recomputes if they no longer match -- a stale curve would be worse than a slow one.
"""
import json
import pathlib

import numpy as np

import sys
sys.path.insert(0, ".")
from hcwc.core import censoring

SIGMAS = (0.0, 10.0, 25.0, 50.0, 75.0, 100.0)
REPLICATES = 60


def compute(sigmas):
    rng = np.random.default_rng(5)
    naive_out, censored_out = [], []
    for sigma in sigmas:
        nv, cn = [], []
        for _ in range(REPLICATES):
            apex = rng.normal(2500.0, 400.0, 242)
            spill = apex + np.exp(rng.normal(np.log(200.0), 0.7, 242))
            capacity = np.exp(rng.normal(np.log(250.0), 0.8, 242))
            contact = apex + np.minimum(capacity, spill - apex)
            err = rng.normal(0.0, sigma, 242)
            hh = np.clip(spill - (apex + err), 5.0, None)
            cc = np.minimum(np.clip(contact - (apex + err), 1.0, None), hh)
            nv.append(censoring.naive_slope(hh, cc))
            cn.append(censoring.censored_slope(hh, cc, hh).slope)
        naive_out.append(float(np.mean(nv)))
        censored_out.append(float(np.mean(cn)))
    return naive_out, censored_out


if __name__ == "__main__":
    naive, censored = compute(SIGMAS)
    out = pathlib.Path("reference/bias_curve.json")
    out.write_text(json.dumps({
        "_comment": ("Mean fitted trap-height elasticity against apex-pick error, for the naive "
                     "and censored estimators. Regenerate with scripts/bias_curve.py. Constant by "
                     "construction: fixed sigmas, seeded generator, no user input -- shipped "
                     "because recomputing it costs about six seconds of every cold start and "
                     "returns the same numbers every time."),
        "seed": 5, "replicates": REPLICATES, "n_per_replicate": 242,
        "sigmas_m": list(SIGMAS), "naive": naive, "censored": censored,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    for s, a, b in zip(SIGMAS, naive, censored):
        print(f"   sigma {s:5.0f} m   naive {a:.4f}   censored {b:.4f}")
