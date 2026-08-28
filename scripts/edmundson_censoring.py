"""Re-do the Edmundson trap-fill statistics with the spill-point censoring modelled.

Run:  python scripts/edmundson_censoring.py

This is the evidence behind docs/HCWC_Builder_PLAN.md section 5.3. It uses the authors'
own published data (open, CC-BY 4.0) and their own numbers reproduce exactly, so the
disagreement is purely about the estimator, not about the observations.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import chi2

from hcwc.core import censoring
from hcwc.io import benchmarks


def main() -> None:
    bm = benchmarks.load_edmundson()
    d = bm.rows
    H = d.trap_height_m.to_numpy(float)
    C = d.hc_column_m.to_numpy(float)
    D = d.burial_depth_m.to_numpy(float)

    print(f"{bm.name}\n  source  : {bm.source}\n  licence : {bm.licence}")
    print(f"  n = {bm.n},  filled to spill = {d.filled_to_spill.sum()} "
          f"({bm.censored_fraction:.1%}) -> right-censored\n")

    print("=" * 78)
    print("SEAL CAPACITY vs TRAP HEIGHT AND BURIAL DEPTH   (log-log elasticities)")
    print("=" * 78)
    both = censoring.censored_loglinear({"trap_height": H, "burial_depth": D}, C, H)
    x = np.column_stack([np.ones(C.size), np.log(H), np.log(D)])
    naive, *_ = np.linalg.lstsq(x, np.log(C), rcond=None)
    print(f"{'':26s}{'trap height':>14s}{'burial depth':>15s}")
    print(f"  {'naive OLS (published)':24s}{naive[1]:>14.3f}{naive[2]:>15.3f}")
    print(f"  {'censored MLE':24s}{both.coefficients['trap_height']:>14.3f}"
          f"{both.coefficients['burial_depth']:>15.3f}")
    print(f"  {'':24s}{'inflated':>14s}{'halved':>15s}")
    print(f"\n  residual sigma = {both.sigma:.3f} (log units), converged = {both.converged}")

    only_h = censoring.censored_loglinear({"trap_height": H}, C, H)
    only_d = censoring.censored_loglinear({"burial_depth": D}, C, H)
    for label, restricted in (("burial depth", only_h), ("trap height", only_d)):
        stat = 2.0 * (both.log_likelihood - restricted.log_likelihood)
        print(f"  likelihood ratio, {label:13s}: chi2 = {stat:6.2f}, 1 df, "
              f"p = {chi2.sf(stat, 1):.2e}")

    print("\n" + "=" * 78)
    print("IMPLIED P(FILLS TO SPILL) -- and how it compares to Graham et al. (2015)")
    print("=" * 78)
    med_depth = float(np.median(D))
    print(f"  at the dataset's median burial depth of {med_depth:.0f} m\n")
    print(f"  {'trap height':>12s}{'median capacity':>18s}{'P(fill to spill)':>19s}")
    from scipy.stats import norm
    for h in (100, 150, 250, 400, 600, 800):
        mu = (both.intercept + both.coefficients["trap_height"] * np.log(h)
              + both.coefficients["burial_depth"] * np.log(med_depth))
        print(f"  {h:>12d}{np.exp(mu):>18.0f}{norm.sf((np.log(h) - mu) / both.sigma):>19.2f}")
    print("\n  Graham et al. report 40% of traps shorter than 250 m filled to spill,")
    print("  from an independent global dataset. Read the 250 m row against it.")


if __name__ == "__main__":
    main()
