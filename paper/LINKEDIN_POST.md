# LinkedIn post

*Companion to `paper/ARTICLE_SHORT.md`, the version written for LinkedIn: the post is the hook, the
article is the argument. It carries no numbers of its own — the worked figures are the full paper's,
printed by `scripts/paper_facts.py` — so nothing here goes stale when a default changes. Replace the
one placeholder before posting: `APP_URL` (https://hcwc-builder.streamlit.app unless the deployment
is named otherwise); the repository must be public before a link to it is used anywhere. The post
has to fit the composer's limit of three thousand characters, and `scripts/linkedin_article.py`
prints the count it will be measured by. Three images, in `paper/figures/`. `scripts/linkedin_article.py` writes
`paper/LINKEDIN_POST.html`, which is this post with the headline already in Unicode bold, because
LinkedIn's feed composer keeps no formatting from a paste.*

---

## Post text

**Where is the hydrocarbon–water contact?**

Just like most of you, I have also spent sleepless nights wondering about the perplexities of
figuring out how the Hydrocarbon–Water Contact (HCWC) distribution should look for an oil and gas
prospect, and especially how to combine it with a geological Probability of Success (POS) — and
then adding another layer of complexity when an apparent DHI modifies the POS, while the contact it
indicates sits well away from the minimum volume criterion used in the geological risking.

"What if? Could you perhaps? But then if… when should you not…?" 🤯

I know — it's the stuff of nightmares!

Ultimately, what you want is a coherent picture of how the probability of finding hydrocarbons
varies with depth, without throwing away the geological uncertainty when a DHI is observed, or
replacing it with a much more optimistic "DHI case".

Well, I think I have found a way I am comfortable with.

The basic idea is to stop treating the HCWC distribution as something that has to be specified
directly — from a company standard, or a statistically derived distribution.

Instead, model the geological mechanisms that can limit the hydrocarbon column: structural spill,
seal capacity and continuity, fault leakage, charge limitation, mechanical failure.

Each mechanism defines its own limit. In each Monte Carlo realisation all limits are sampled, and
the shallowest active one becomes the HCWC. The distribution is therefore not specified beforehand;
it emerges from the competition between the limits.

That gives three things from the same realisations: which mechanism controls the HCWC and how that
control changes with depth, the HCWC distribution itself, and the probability of success against
depth. No second elicitation, nothing to reconcile.

An apparent DHI then enters as evidence rather than as a separate case, in two separate channels.
The character of the response — amplitude, polarity, conformity, behaviour with offset — says
whether hydrocarbons are there at all, and updates the prospect POS. The geometry of the interpreted
event says where the contact is, and reweights the existing geological realisations. It is seldom
perfect evidence, so its stated strength decides how far the HCWC distribution is pulled towards the
indicated depths, and the geology behind it is never discarded.

And because the geological risk elements survive into the output, the model also shows how risk is
distributed with depth and which mechanism carries it — a better guide to where mitigation is worth
the money than one number for the whole prospect.

So I have built a small open-source tool around the idea, and written up the thinking behind it.

I'm sharing it because I'd genuinely like to hear how others handle this problem — particularly
your thoughts on the connection between HCWC uncertainty, geological POS and DHI evidence.

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
discovery record. The short article has the method; the full paper, with the derivations, the
worked numbers and the references, is on tab 8.2 of the tool.
