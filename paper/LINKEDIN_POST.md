# LinkedIn post

*Companion to `paper/ARTICLE.md`: the post is the hook, the article is the argument. Its numbers
are `scripts/paper_facts.py`'s. Replace the three placeholders before posting: `ARTICLE_URL`,
`APP_URL` (https://hcwc-builder.streamlit.app unless the deployment is named otherwise),
`GITHUB_URL` (the repository must be public first). Three images, in `paper/figures/`.*

---

## Post text

Where is the hydrocarbon–water contact? In most prospect evaluations the answer is a distribution
somebody typed in: uniform from apex to spill, a three-point estimate, the company standard.

A detailed Monte Carlo model can still answer the wrong geological question.

I built a tool that asks the geology instead. Every mechanism that can stop a column — charge,
spill, a leaking fault, seal capacity, seal continuity, mechanical failure — gets two numbers:
how likely it is to be there, and how deep it acts if it is. Ten thousand times over, the
shallowest active one sets the contact. The distribution is the output, and the model records
which mechanism set it in each realisation.

That second part is the one I use most. On the worked prospect the top seal sets the contact in
33 % of realisations, a fault leak in 23 %, seal continuity in 16 %. A few mechanisms carry the
answer in this case; the rest can stay rough. A reviewer can argue with a mechanism instead of a curve.

The DHI is treated as evidence, not as a replacement contact. Its character, placed on an
evidence index, updates the chance that hydrocarbons are there at all: 40 % to 64 % on the worked
prospect. Its geometry reweights the same geological realisations: the contact narrows from a
136 m to a 105 m P90–P10 spread, with an effective sample size of 4 857 of the 10 000. Strong DHI
evidence can raise P(G) substantially while the contact depth stays uncertain — and a well 180 m
below the crest reads 49 %, not 64 %, because it also needs the column to reach it.

The competing-limits idea is Beha, Christensen and Young's (2012); the tool puts it in one place
with the DHI update and a censoring-aware comparison against the NCS record.

Article: ARTICLE_URL
App, open source, no geomodel needed: APP_URL
Code and theory: GITHUB_URL

---

## Images

1. `figures/Figure_4.1.1a_the-competition-realisation-by-realisation.png` — Each limit's chance of permitting a contact at
   least this deep; the contact is the lower envelope, and the distribution follows.
2. `figures/Figure_4.1.2a_the-controlling-mechanism-at-each-depth.png` — Which mechanism stops the column, and where.
3. `figures/Figure_5.1.4a_where-the-contact-is-before-and-after-the.png` — The contact distribution before and after the DHI: a
   reweighting, with the prior still visible.

## First comment (post immediately after publishing)

The tool runs in a browser and ships with a worked prospect; every number in the post is printed
by one script from the code. The article has the method; tab 8.1 of the tool has it in full.
