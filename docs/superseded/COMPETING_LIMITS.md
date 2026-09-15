# Competing limits

*Why the contact is derived from the mechanisms rather than entered as a distribution.*

## The construction

A hydrocarbon column is stopped by whichever mechanism acts first. Charge may run out before the closure is full. The top seal may leak at a capillary pressure the column exceeds. A fault may juxtapose the reservoir against a carrier. The closure may spill. Each of these has a depth or capacity at which it acts, and each may or may not be active on a given prospect.

The tool samples every limit independently in each realisation: a depth or capacity from its stated uncertainty, and an active or inactive state from its stated probability. The shallowest active limit sets the contact. The mechanism that set it is recorded.

This is Hood's competition-between-limits construction (Hood 2019), run as a Monte Carlo rather than as a scenario tree.

## Why the limits are not blended

The alternative is to combine the limits into one distribution for the column: a weighted average of the capacities, or a single distribution wide enough to cover them. Both suppress outcomes.

If a leak that acts at 150 m is averaged into a background column of 300 m, the result puts weight at 200 and 250 m. Those depths are not reachable on that prospect when the leak is active: the column stops at 150 m. Blending puts probability where no mechanism can deliver it.

Taking the minimum of independent samples has the opposite property. Every realisation is a column some mechanism can produce, at a depth that mechanism can produce it. The distribution has no outcomes the geology cannot.

## What recording the controller adds

A distribution alone says where the contact may be. The record of which limit set it in each realisation says why, and how that changes with depth.

The share of realisations each mechanism controls is a measure of where the risk sits. A prospect controlled by top-seal capacity in most realisations is a seal prospect regardless of what the element chances say; the controller share is derived from the mechanisms, not allocated by judgement.

The same record gives the probability of hydrocarbons at any depth: the share of realisations in which the contact lies below that depth. Read at the assessment minimum, this is the geometric part of the prospect chance.

## The reference data are censored

The published column-height record (tab 6.0) is a set of discoveries. About half of them filled their closure to the spill point.

A filled-to-spill discovery is a right-censored observation of seal capacity. The seal held a column of the observed height; what it could have held is unknown, because the closure ran out first. Treating those columns as measurements of seal capacity biases every capacity statistic downward.

Tab 6.0 separates the two populations. Comparisons against the seal-limited subset are comparisons of like with like; the filled-to-spill subset is a comparison of closure sizes, which is a different question.

## Where this leaves the DHI

A DHI is an observation of the contact, not a competing opinion about it. It enters as evidence that reweights the realisations already drawn, with the weight set by how well the observation would have been produced under each. Tab 5.0 sets this out; the theory notes *Prior or likelihood?* and *Weight, not Bayes* cover the two ways of doing it wrong.
