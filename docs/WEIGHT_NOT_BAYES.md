# A benchmark is a second prior, not a likelihood

*Why tab 6.0 §8 combines the model with the published record by a stated weight rather than by
multiplying, and what would have to be true for the multiplication to be legitimate.*

The tempting move is to treat the benchmark as evidence and multiply:

`p(h | benchmark) ∝ p(h) · L(benchmark | h)`

The quick dismissal of this is wrong, and is dealt with first. It is tempting to say the record was
measured on other traps, so `L(benchmark | h)` cannot depend on this `h`, so the term is flat and
nothing happens. That argument fails. If the prospect is exchangeable with the record, then its
column and theirs are draws from one population with a shared, unknown parameter, which makes them
conditionally independent given that parameter and therefore marginally dependent. The record does
move the distribution of `h`. Every hierarchical model uses this.

The question is therefore not whether the record is informative. It is which population
distribution the assessor is entitled to use.

The marginal, all 242 columns pooled, is not it, and the data say so. Regressing log column on trap
height and burial depth removes 81 % of the spread: the variance falls from 0.71 to 0.13 in log
space. Most of the width of that distribution is traps being different sizes from each other, and
the size of the prospect in hand is known. For a 350 m closure at 2 050 m:

|                                       | P90 | P50 | P10 |
| ------------------------------------- | --- | --- | --- |
| the marginal record, pooled           |  38 | 146 | 308 |
| conditioned on this relief and burial | 151 | 240 | 382 |

Those are different beliefs, and the pooled one is not a prior for the prospect: it re-imports
uncertainty about trap size that mapping has already resolved. It is also not close to
exchangeable, since the record spans 14 m to 715 m of relief.

The tool therefore conditions before it compares. Every benchmark on tab 6.0 is evaluated at the
prospect's own relief and burial depth, never pooled. That is the legitimate content of the
base-rate argument, and it is applied.

What survives the conditioning is a statement about mechanisms, and that is where it belongs.
Residual variance of 0.13 in log space is seal, charge and fault behaviour in comparable rocks, a
shared parameter the prospect is exchangeable with. The censoring-corrected fit in tab 6.0 §3
estimates it, and it sets the prior for one limit, the top-seal capacity, with its own weight on
tab 3.0, Retention. The competition then runs as before, so the controlling-limit bookkeeping
survives.

## Three reasons this stays a stated weight rather than a multiplication

- Double-counting. The relief already enters the model as the spill limit, and the burial already
  sets the seal calculator's temperature. Multiplying in a distribution that also encodes relief
  counts the geometry twice, the same failure as the base-rate rule in *Base-rate neglect, and the
  arithmetic to avoid*, which counts the play twice.
- Their columns are not capacities. Each is `min(capacity, their trap height)`, and tab 6.0 §3
  shows nearly half are censored at spill. Even at the same relief, the upper tail is shaped by
  their geometry.
- Every trap in the record had hydrocarbons in it. The benchmark is conditional on success, so it
  can inform where a contact sits and never the chance of having one.

What could be a likelihood without any of this: something observed on this prospect whose
probability depends on where the contact is. A seismic amplitude, an offset penetration, a pressure
point. That is why tab 5.0 is an unqualified update and tab 6.0 §8 is a weight the assessor sets,
defaulting to zero.
