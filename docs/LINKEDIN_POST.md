# LinkedIn post — draft

*Companion to the article `docs/ARTICLE.md`. The post is the hook; the article is the argument.
Overlap between them is limited to the closing line and one figure. Images are in `docs/post/`,
regenerated from the app by `scripts/post_images.py`; nothing in them is typed. Replace the
three placeholders before posting: `ARTICLE_URL` (the LinkedIn article), `APP_URL`
(https://hcwc-builder.streamlit.app unless the deployment is named otherwise), `GITHUB_URL`
(the repository must be public first). LinkedIn allows up to 20 images on a post; this uses 11.*

---

## Post text

Where is the hydrocarbon–water contact? In most prospect evaluations the answer is a
distribution somebody typed in. Uniform from apex to spill. A three-point estimate. Whatever the
company standard says.

I built a tool that refuses to answer that way. It asks the geology instead.

Every mechanism that can stop a column — charge, spill, fault leak, seal capacity, seal
continuity, fracture — gets two numbers: how likely it is to be there, and how deep it acts if it
is. Ten thousand times over, the shallowest one wins. The contact distribution is what comes out.
Nobody chose its shape.

That is not a new idea. Beha, Christensen and Young wrote it down in 2012; Hood, Grant and Lowry
were there before and after. What I wanted was the whole chain in one place, with the receipts:
which mechanism controlled each realisation, the chance read at any depth, a well tested against
every draw, and a DHI treated as evidence rather than as a replacement contact.

The DHI part is the one I care most about. A bright amplitude with a picked termination does two
different things. Its strength says something about whether there are hydrocarbons at all; its
geometry says something about how deep they go, if they are there. The tool keeps those apart. On
the worked prospect a moderate anomaly takes the chance from 40 % to 64 %, narrows the contact
from 130 m to 99 m, and leaves 4 872 of the 10 000 realisations doing the work. That last number
is the honest one: it says how far the seismic pushed the geology.

A strong DHI does not make the contact certain. It makes hydrocarbons likely. The depth
uncertainty stays where it came from: the pick, the depth conversion, and whether that flat
thing is a contact at all.

The article has the reasoning and the maths, in about two thousand words: ARTICLE_URL

The tool is open source, MIT, and runs in a browser without a geomodel: APP_URL
Code, tests and the theory notes: GITHUB_URL

The point is not to find a better distribution. It is to let the geology generate the
distribution.

---

## Images, in order, with their captions

1. `01_concept.png` — Every mechanism that can stop a column, on one section, with the depth at
   which it acts. Filling works down from the apex, so every capacity is measured from there.

2. `02_ranking.png` — Which limit sets the contact, and how often. On this prospect the top seal
   and a fault leak are the competition; six of the thirteen limits never win and can stay rough.

3. `03_all_limits_one_axis.png` — The competition drawn. Each violin is one limit's sampled
   depth; the right-hand one is the shallowest active limit in every realisation, which is the
   contact.

4. `04_contact_distribution.png` — The result: the contact distribution and its exceedance
   curve. Every probability of success in the workflow is a reading of this curve at a depth.

5. `05_controlling_by_depth.png` — The same distribution coloured by what controls it. Shallow
   contacts are seal-limited; deep ones pass to fault geometry and spill. A generic distribution
   cannot draw this figure.

6. `06_chance_against_depth.png` — The prospect chance against depth, element risk included.
   Read at the assessment minimum it is the headline POS; read at a well's entry depth it is the
   chance that well finds hydrocarbons.

7. `07_the_pick_against_the_geology.png` — Enter the DHI. Blue is the geology; red is the
   picked contact with its uncertainty. Everything downstream is these two meeting.

8. `08_update_at_a_glance.png` — What the update did, and through which channel. Strength moved
   P(G); geometry moved the contact and its spread; the effective sample size says how much
   geology is left underneath.

9. `09_dhi_updated_contact.png` — The contact distribution before and after. The DHI reshaped
   it; it did not replace it, and nothing was ruled out.

10. `10_chance_before_after.png` — The chance against depth, geological and updated, from the
    same weighted realisations. The two curves meet the headline numbers by construction, not by
    rescaling.

11. `11_benchmark_family.png` — A reality check, not a score: the prospect beside 242 Norwegian
    discoveries at the same relief, with the filled-to-spill ones treated as censored. Compared,
    never multiplied in.

---

## Notes for posting

- Overlap with the article: the closing line, the 40 → 64 % / 130 → 99 m / 4 872 numbers, and
  image 9 (the article's panel c). Everything else in the post is picture-led and the article
  carries the derivation.
- The article's figure (`docs/figures/fig6_paper.png`) is not in the post; the post's images
  are the app's own, so a reader who opens the app recognises them.
- `GITHUB_URL` requires the repository to be public; until then, drop the line or link the
  app only.
- The strength / σ / c settings behind images 7–10 are the shipped defaults with strength 20 and
  σ 10 m, the same case as the article, so the two documents quote one run.
