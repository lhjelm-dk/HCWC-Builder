# Can a base rate be a likelihood?

*The argument behind tab 8.0 §1. Short answer: no. A base rate is a prior over column height, and
the tool already has one. A DHI can be a likelihood because it is an observation of the prospect
in hand.*

The benchmark on tab 6.0 gives a probability distribution over column height. So does the model on
tab 4.0. Bayes' rule multiplies a prior by a likelihood, so the question is why the DHI can be a
likelihood and the statistics cannot.

A prior and a likelihood are the same kind of object. Both are functions of the unknown; `p(h)`
and `L(h)` have the same type signature. A likelihood is not a kind of distribution but a kind of
use, and the question is never whether something is a probability but probability of what, given
what.

To act as a likelihood, a term must be `P(data | h)` where the data was observed on the prospect
being assessed.

## A real likelihood can be built from the benchmark

The dataset carries the joint behaviour of column, relief and burial across the discoveries. The
prospect's relief and burial depth are measured. So

```
L(h) = P(this relief, this burial | column = h)
```

is a likelihood, and there is nothing wrong with it. Multiplied by a prior on `h`, a proper
posterior comes out.

## The problem is what it is multiplied by

With a neutral prior the result is the benchmark's own conditional prediction: correct, and the
benchmark reached by a longer road. With the prospect model as the prior, relief and burial have
been conditioned on twice, because the model was built out of them: the spill point is the relief,
and the seal calculator takes its temperature from the burial depth. There is no fact in the
benchmark's conditioning set that the model has not already used.

The test is therefore not whether the data is a probability. It is whether the data carries
something the model has not already used.

## Where a likelihood does live in that dataset

The outcomes. Two hundred and forty-two drilled results are observations, and they are new: the
model has not seen them. But they are observations of other prospects, so they cannot be a
likelihood for this column.

They can be a likelihood for something this prospect and those 242 share: the parameters of the
seal-capacity relationship. Compaction closes pore throats the same way on one prospect as on
another. The chain therefore has two steps, and only the first is Bayes:

```
242 outcomes       ──►  the shared parameters     Bayesian updating
shared parameters  ──►  this prospect             shrinkage, with a stated weight
```

That is empirical Bayes, and it is what the seal limit on tab 3.0 offers under **Pull this toward
the NCS record**. It is defensible where a direct update is not because it updates something the
prospect and the population share, rather than updating the prospect with other prospects'
answers.

## The case where the benchmark is a prior

After the well. Then `p(h | relief, burial)` from the record is a prior, the measured column is the
data, and Bayes applies without difficulty. The asymmetry exists only before the well, because
before the well there is no observation of this prospect's column, which is the reason a
distribution for it is being built.

## The same failure, twice more

Two other places in the tool are the same mistake in different clothes, and both have their own
notes:

- Fusing the benchmark into the model by multiplication rather than by a stated weight: *A
  benchmark is a second prior, not a likelihood*.
- Multiplying a base rate's odds by a prospect PoS, which is symmetric and so cannot be a Bayesian
  update: *Base-rate neglect, and the arithmetic to avoid*.
