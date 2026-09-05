# Can a base rate be a likelihood?

*The argument behind tab 8.0 §1. Short answer: no — a base rate is a prior over column height, and
this tool already has one. A DHI can be a likelihood because it is an observation of* this
*prospect.*

The benchmark on tab 6.0 gives a probability distribution over column height. So does the model on
tab 4.0. Bayes' rule multiplies a prior by a likelihood — so why can the DHI be a likelihood and the
statistics not?

**Because a prior and a likelihood are the same kind of object.** Both are functions of the unknown;
`p(h)` and `L(h)` have the same type signature. A likelihood is not a *kind of distribution*, it is
a **kind of use** — and the question is never *is this a probability?* but **probability of what,
given what?**

To act as a likelihood, something must be `P(data | h)` where the data is a thing **you observed on
this prospect**.

## You can get a real likelihood out of the benchmark

Here it is, honestly built. The dataset carries the joint behaviour of column, relief and burial
across the discoveries. You measured your prospect's relief and burial depth. So

```
L(h) = P(your relief, your burial | column = h)
```

is a genuine likelihood, and there is nothing wrong with it. Multiply it by a prior on `h` and a
proper posterior comes out.

## The problem is what you multiply it by

With a *neutral* prior you recover the benchmark's own conditional prediction — correct, and simply
the benchmark reached by a longer road. With **your model** as the prior you have conditioned on
relief and burial **twice**, because your model was built out of them: your spill point *is* the
relief, and the seal calculator takes its temperature from the burial depth. There is no fact in the
benchmark's conditioning set that your model has not already used.

**So the test is not "is this a probability?" It is: does this data carry something my model has not
already used?**

## Where a genuine likelihood *does* live in that dataset

The **outcomes**. Two hundred and forty-two drilled results are real observations and they are new —
your model has never seen them. But they are observations of *other prospects*, so they cannot be a
likelihood for your column.

They can be a likelihood for something you and those 242 share: **the parameters of the
seal-capacity relationship**. Compaction closes pore throats the same way on your prospect as on
theirs. So the honest chain has two steps, and only the first is Bayes:

```
242 outcomes       ──►  the shared parameters     genuine Bayesian updating
shared parameters  ──►  your prospect             shrinkage, with a stated weight
```

That is empirical Bayes, and it is what the seal limit on tab 3.0 offers under *Pull this toward the
NCS record*. **The reason that one is defensible and a direct update is not** is not a matter of
taste: it updates something your prospect and the population genuinely share, rather than trying to
update your prospect with somebody else's answers.

## And the case where the benchmark *is* a prior

After you drill. Then `p(h | relief, burial)` from the record is a perfectly good prior, your
measured column is the data, and Bayes applies with nothing awkward about it. The asymmetry only
exists before the well, because before the well there is no observation of *this* prospect's column
at all — which is the reason you are building a distribution for it.

## The same failure, twice more

Two other places in this tool are the same mistake wearing different clothes, and both have their
own notes:

- **Fusing the benchmark into your model** by multiplication rather than by a stated weight — see
  *A benchmark is a second prior, not a likelihood*.
- **Multiplying a base rate's odds by a prospect PoS**, which is symmetric and so cannot be a
  Bayesian update at all — see *Base-rate neglect, and the arithmetic to avoid*.
