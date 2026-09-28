# LinkedIn post

*Companion to `paper/ARTICLE.md`: the post is the hook, the article is the argument. It carries no
numbers of its own — the worked figures are the article's, printed by `scripts/paper_facts.py` —
so nothing here goes stale when a default changes. Replace the two placeholders before posting:
`ARTICLE_URL` and `APP_URL` (https://hcwc-builder.streamlit.app unless the deployment is named
otherwise); the repository must be public before `GITHUB_URL` is used anywhere. Three images, in
`paper/figures/`.*

---

## Post text

Where is the hydrocarbon–water contact?

Just like most of you, I have also spent sleepless nights wondering about the perplexities of
combining the geological Probability of Success (POS) for an oil and gas prospect with a
distribution of where the Hydrocarbon–Water Contact (HCWC) might actually be. And then, adding
complexity, a DHI comes along and modifies the POS, while the apparent HCWC sits somewhere quite
different from the minimum volume criterion used in the geological risking.

"What if? Could you perhaps? But then if… when should you not…?" 🤯

I know — it's the stuff of nightmares.

Ultimately, what you want is a coherent picture of how the probability of finding a commercial
volume changes with hydrocarbon column height, without quietly throwing away the geological
uncertainty when the DHI arrives.

So how do you combine the two without simply making a "DHI case" and replacing the geological
uncertainty with a much more optimistic contact?

Well, I think I might have found a way I am comfortable with.

The basic idea is to stop treating the HCWC distribution as something that has to be specified
directly, from a standard or a statistical distribution. Instead, model the geological mechanisms
that can limit the column: geometry, retention (seal), lateral containment, charge uncertainty and
the rest. The HCWC distribution then emerges from the competing limits.

That also means the same model describes which mechanism is controlling, the probability of
achieving a given column height, and the resulting geological POS at any depth.

The DHI can then be treated as evidence rather than as a replacement model. Its likelihood updates
the existing geological HCWC limits, with the strength of the update made explicit.

So I've built a small open-source tool around the idea, and written up the thinking behind it.

I'm sharing both because I'd genuinely like to hear how others handle this problem — particularly
if you have input on the connection between HCWC uncertainty, geological POS and DHI evidence.

The article is here: ARTICLE_URL

And the tool is here: APP_URL

Feedback, criticism and alternative approaches are very welcome.

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
