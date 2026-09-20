"""The images for the LinkedIn post and the article, exported from the app's own figures.

Runs the app once through ``AppTest`` on its shipped prospect (DHI on, the default), lifts the
registered figures out of the exhibit registry and writes them as PNG with kaleido, plus one
drawn card for the at-a-glance strip, whose numbers are metrics rather than a figure. Nothing is
typed: every image is what the app draws. Run from the repository root::

    python scripts/post_images.py

Output: ``paper/post/*.png``, listed in ``paper/LINKEDIN_POST.md``, and the article's figures in
``paper/figures/`` (Lars, 17 Sep 2026: the article's figures are the app's, same look; the
matplotlib set they replace is kept in ``archive/old_figures/``). The workflow figure that opens the
article is drawn by ``scripts/workflow_figure.py``; the concept sketch ``fig5`` by
``scripts/paper_figures.py``.
"""
from __future__ import annotations

import contextlib
import io as _io
import pathlib
import sys
import warnings

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "paper" / "post"

#: Exhibit label -> file name and the width to draw it at. Order is the post's order.
FIGURES = [
    ("Figure 3.1a", "02_ranking.png", 1200, 520),
    ("Figure 4.1.2e", "03_all_limits_one_axis.png", 1400, 760),
    ("Figure 4.1.1a", "04_contact_distribution.png", 1400, 700),
    ("Figure 4.1.2a", "05_controlling_by_depth.png", 1400, 700),
    ("Figure 4.1.3a", "06_chance_against_depth.png", 1400, 620),
    ("Figure 5.1.1a", "07_the_pick_against_the_geology.png", 1400, 520),
    ("Figure 5.1.4a", "09_dhi_updated_contact.png", 1400, 620),
    ("Figure 5.1.5a", "10_chance_before_after.png", 1400, 700),
    ("Figure 6.7a", "11_benchmark_family.png", 1400, 760),
]

#: Exhibit label -> file name in paper/figures, for paper/ARTICLE.md and the long manuscript.
ARTICLE = [
    ("Figure 4.1.1a", "fig1_competing_limits.png", 1400, 700),
    ("Figure 4.1.2a", "fig2_controlling_mechanism.png", 1400, 700),
    ("Figure 4.1.3a", "fig3_chance_against_depth.png", 1400, 620),
    ("Figure 5.1.4a", "fig4_dhi_update.png", 1400, 620),
    ("Figure 5.1.5a", "fig6_chance_before_after.png", 1400, 700),
]
FIGURES_DIR = ROOT / "paper" / "figures"
#: The number each exported file carries in paper/ARTICLE.md (the manuscript's numbering is its own).
ARTICLE_NUMBERS = {"fig1_competing_limits.png": "Figure 2", "fig2_controlling_mechanism.png": "Figure 3",
                   "fig3_chance_against_depth.png": "manuscript Figure 3",
                   "fig4_dhi_update.png": "Figure 4", "fig6_chance_before_after.png": "Figure 5"}


def main() -> None:
    warnings.filterwarnings("ignore")
    # Captions carry ≥ and ×; a cp1252 console must not stop the export over a print.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import plotly.io as pio
    from streamlit.testing.v1 import AppTest

    from hcwc.plotting.paper import manifest
    from hcwc.ui import numbering

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=900)
    at.session_state["min_column_input"] = 120.0
    at.session_state["dhi_in_strength"] = 20.0
    at.session_state["dhi_in_sigma"] = 10.0
    with contextlib.redirect_stderr(_io.StringIO()):
        at.run()
    assert not at.exception, "\n".join(str(e.value) for e in at.exception)
    figures = at.session_state[numbering.FIGURES_KEY]
    OUT.mkdir(parents=True, exist_ok=True)

    entries = []
    for folder, table in ((OUT, FIGURES), (FIGURES_DIR, ARTICLE)):
        for label, name, width, height in table:
            fig, caption = figures[label]
            fig.update_layout(template="plotly_white", font=dict(size=15),
                              margin=dict(l=70, r=30, t=30, b=70))
            pio.write_image(fig, folder / name, width=width, height=height, scale=2)
            print(f"  {folder.name}/{name}  <- {label}: {caption}")
            if folder is FIGURES_DIR:
                entries.append(manifest.Entry(ARTICLE_NUMBERS.get(name, "-"), name,
                                              f"`scripts/post_images.py`, the app's {label}", caption))

    # ---- the manifest: number, file, source, caption and the run behind every paper figure ----
    entries.insert(0, manifest.Entry("Figure 1", "fig0_workflow.png",
                                     "`scripts/workflow_figure.py`, the conceptual version",
                                     "The model as two rows: geological, the prior; DHI evidence, "
                                     "the update; each ending in the probability of meeting the "
                                     "threshold."))
    entries.append(manifest.Entry("manuscript Figure 5", "fig5_truncate_vs_terminate.png",
                                  "`scripts/paper_figures.py`, drawn from a two-limit sketch",
                                  "Terminating versus truncating at spill."))
    manifest.write(FIGURES_DIR / "MANIFEST.md", entries, {
        "prospect": "the shipped default (Tiramisu-C4), `paper/figures/prospect.json`",
        "seed": 20260825, "realisations": 10_000, "assessment minimum h_min": "120 m",
        "DHI evidence index": 20.0, "pick sigma": "10 m", "contact attribution c": 0.36,
        "detection": "h50 25 m, width 8 m, ceiling 0.90, false positive 0.5"})
    print(f"  {FIGURES_DIR.name}/MANIFEST.md")

    # ---- the at-a-glance card: four metrics, before and after --------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    overlay = at.session_state["dhi_overlay"]
    post = at.session_state["dhi_posterior"]
    res = post.result
    p_g_before = 1.0
    for chance in at.session_state["element_pos"].values():
        p_g_before *= float(chance)
    p50_b = float(post.percentiles(50.0, posterior=False)[0])
    p50_a = float(post.percentiles(50.0)[0])
    sp_b = float(np.diff(post.percentiles(np.array([90.0, 10.0]), posterior=False))[0])
    sp_a = float(np.diff(post.percentiles(np.array([90.0, 10.0])))[0])
    cards = [
        ("P(G)", f"{p_g_before:.0%}", f"{overlay['p_g_given_amplitude']:.0%}", "evidence strength"),
        ("HCWC P50", f"{p50_b:,.0f} m", f"{p50_a:,.0f} m", "contact geometry"),
        ("P90–P10", f"{sp_b:,.0f} m", f"{sp_a:,.0f} m", "contact geometry"),
        ("Effective sample size", f"{res.n:,}", f"{post.effective_sample_size:,.0f}",
         "how much geology is left"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.4), dpi=150)
    for ax, (title, before, after, channel) in zip(axes, cards):
        ax.axis("off")
        ax.text(0.5, 0.92, title, ha="center", va="top", fontsize=13, color="#555555",
                transform=ax.transAxes)
        ax.text(0.5, 0.62, after, ha="center", va="center", fontsize=30, fontweight="bold",
                color="#C44E52", transform=ax.transAxes)
        ax.text(0.5, 0.30, f"from {before}", ha="center", va="center", fontsize=13,
                color="#333333", transform=ax.transAxes)
        ax.text(0.5, 0.10, channel, ha="center", va="center", fontsize=10.5, color="#7d8794",
                transform=ax.transAxes)
        ax.add_patch(plt.Rectangle((0.03, 0.02), 0.94, 0.96, transform=ax.transAxes,
                                   fill=False, edgecolor="#C44E52", linewidth=1.4))
    fig.suptitle("The DHI update at a glance: shipped prospect, strength 20, pick σ 10 m, "
                 "c = 0.36", fontsize=12.5, color="#333333", y=1.02)
    fig.savefig(OUT / "08_update_at_a_glance.png", bbox_inches="tight", facecolor="white")
    print("  08_update_at_a_glance.png  <- tab 5.1 metrics")

    # ---- the concept figure travels as is --------------------------------------------------
    import shutil
    shutil.copy(ROOT / "reference" / "defaults" / "concept.png", OUT / "01_concept.png")
    print("  01_concept.png  <- reference/defaults/concept.png")


if __name__ == "__main__":
    main()
