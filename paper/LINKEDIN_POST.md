# LinkedIn post

*Companion to `paper/ARTICLE.md`: the post is the hook, the article is the argument. It carries no
numbers of its own — the worked figures are the article's, printed by `scripts/paper_facts.py` —
so nothing here goes stale when a default changes. Replace the two placeholders before posting:
`ARTICLE_URL` and `APP_URL` (https://hcwc-builder.streamlit.app unless the deployment is named
otherwise); the repository must be public before `GITHUB_URL` is used anywhere. Three images, in
`paper/figures/`.*

---

## Post text

**Where is the hydrocarbon–water contact?**

Just like most of you, I have also spent sleepless nights wondering about the perplexities of
figuring out how the Hydrocarbon–Water Contact (HCWC) distribution should look for an oil and gas
prospect, and especially how to combine it with a geological Probability of Success (POS) — and
then adding another layer of complexity when an apparent DHI modifies the POS, while the contact it
indicates sits somewhere quite different from the minimum volume criterion used in the geological
risking.

"What if? Could you perhaps? But then if… when should you not…?" 🤯

I know — it's the stuff of nightmares!

Ultimately, what you want is a coherent picture of how the probability of finding hydrocarbons
varies with depth, without quietly throwing away the geological uncertainty when a DHI is observed,
or simply replacing it with a potentially much more optimistic "DHI case".

Well, I think I might have found a way I am comfortable with.

The basic idea is to stop treating the HCWC distribution as something that has to be specified
directly — whether from a company standard or by choosing a statistically derived distribution.

Instead, model the geological mechanisms that can limit the hydrocarbon column: structural spill,
seal capacity and continuity, fault leakage, charge limitation, mechanical failure.

Each mechanism defines a possible range of limiting HCWC depths. In each Monte Carlo realisation,
all limits are sampled, and the shallowest active limit becomes the HCWC for that realisation. The
HCWC distribution is therefore not specified beforehand; it emerges from the competition between the
geological limits.

That means the model describes three things at the same time: (a) which geological mechanism
controls the HCWC, (b) the probability of achieving a given column height, and (c) the resulting
geological POS as a function of depth.

The apparent DHI can be considered as evidence that, via Bayesian updating, can modify the prospect
POS given its strength. It is seldom perfect evidence, but its likelihood can be used to reweight
the existing ensemble of geological possibilities, so that the strength of the DHI decides how far
the HCWC distribution is drawn towards the observed DHI depths, without discarding the geological
HCWC assumptions behind it.

It is all rather complicated, so I've built a small open-source tool around the idea and written up
the thinking behind it.

I'm sharing both because I'd genuinely like to hear how others handle this problem — particularly
your thoughts on the connection between HCWC uncertainty, geological POS and DHI evidence.

ARTICLE_URL

APP_URL

---

## Images

1. `figures/Figure_4.1.1a_the-competition-realisation-by-realisation.png` — Fifty realisations of
   the competition: each limit's sampled depth, the shallowest active one ringed as the contact,
   and the distribution those minima make.
2. `figures/Figure_4.1.2a_the-controlling-mechanism-at-each-depth.png` — Which mechanism stops the
   column, and where.
3. `figures/Figure_5.1.4a_where-the-contact-is-before-and-after-the.png` — The contact distribution
   before and after the DHI: a reweighting, with the prior still visible.

## First comment (post immediately after publishing)

The tool runs in a browser and ships with a worked prospect, so nothing has to be set up to see
what it does. The competing-limits idea is Beha, Christensen and Young's (2012); what the tool adds
is the DHI update on the same realisations and a censoring-aware comparison against the NCS
discovery record. The article has the method; tab 8.1 of the tool has it in full.
