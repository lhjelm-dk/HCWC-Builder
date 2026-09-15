# Base-rate neglect, and the arithmetic to avoid

*A note on combining a base rate with a prospect estimate. Referenced from tab 6.0 §9, which shows
the two side by side and does not merge them.*

Milkov (2017) is right about the problem, and the paper is worth reading: explorers under-use
population frequencies, and a portfolio that ignores them drifts. Nothing below disputes that.

The difficulty is in the arithmetic usually attached to it. The combination rule takes the base
rate `b` and the prospect's own PoS `q` and multiplies their odds:

`P_updated = b·q / ( b·q + (1−b)(1−q) )`

The rule is symmetric. A base rate of 0.2 and a prospect PoS of 0.9 return 69.2 %; 0.9 and 0.2
return 69.2 % again. It cannot tell which input is the population and which is the prospect, and a
Bayesian update is never symmetric between a prior and its evidence. That symmetry is the
diagnostic: the formula performs a fusion of two opinions, not an update of one by the other.

## The fixed-point test

The sharpest test asks what happens when there is nothing to learn. Suppose the assessor's own PoS
already equals the base rate. The two agree, no new information exists, and a coherent update must
return the number unchanged. This rule does not:

| b = q | the rule returns |
| ----- | ---------------- |
|   0.2 |            0.059 |
|   0.4 |            0.308 |
|   0.5 |            0.500 |
|   0.6 |            0.692 |
|   0.8 |            0.941 |

An explorer who has done what the paper asks, looked the base rate up and matched it, is told to
revise 0.8 to 0.94. Only `b = 0.5` survives, and only because the expression collapses to `P = q`
there.

Two further consequences follow, and both cut against the paper's own purpose:

- A confident assessor erases the base rate entirely. At `q = 1` the result is 1 whatever `b` is;
  at `q = 0` it is 0. The base rate has no influence where over-confidence needs restraining.
- It double-counts whenever the assessor already used base-rate knowledge, which is the behaviour
  the paper asks for.

## Where the arithmetic comes from

In odds the rule is `posterior odds = prior odds × b/(1−b)`: the odds form of Bayes with the
likelihood ratio set to `b/(1−b)`. That is a Fagan nomogram, the standard diagnostic device, for a
test whose sensitivity and specificity are both `b`. The nomogram is sound; the base rate has been
entered on the axis meant for the accuracy of a test rather than the axis meant for the prior. In
Bayes the base rate is the prior, which is the reason base-rate neglect is a fallacy and what the
cognitive literature the paper cites is about. Putting it on the likelihood axis while also
supplying a separate prior counts the play twice and leaves the prospect's own evidence nowhere to
enter.

## Why the tab stops where it does

Combining a base rate with a prospect estimate needs a stated weight and a defence of it, and no
rule that hides the weight inside an identity can supply one. So the two are shown side by side on
tab 6.0 §9 and not merged. Where the tool does combine them, the shrinkage on the top-seal limit in
tab 6.0 §7, the weight is a slider the assessor sets, the result always lies between the two, and
agreement is a fixed point.

## Sourcing

The rule above is Figure 10 of Milkov (2017) and the paragraph introducing it on p. 1915, which
offers Bayes' theorem "directly" with "the historical success rate" as the conditional probability.
The figure's own worked example, an initial PoS of 0.3 and a base rate of 0.6 giving "approximately
0.39", reproduces to 0.3913 under this expression, which is how the rule is identified. It also
matches a spreadsheet implementation exactly, 99 of 99 rows to machine precision. Applied to the
paper's own case, Lundin's assessed average of 0.26 against an NCS base rate of 0.52, it returns
0.276.

None of this touches the paper's finding. Base-rate neglect is real, the Lundin record demonstrates
it, and the recommendation to learn the base rates and check portfolio outcomes against them stands
on its own. Schofield (GEOAdvisors) raises a separate objection about the choice of reference class,
pooling the mature North Sea with the emerging Barents, and does not reach Figure 10.
