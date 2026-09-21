# LinkedIn post — options

Attach **fig1_competing_limits.png** (or fig5 for option B). One image outperforms several in the
feed; save the rest for the article.

---

## Option A — the workflow argument (recommended)

Somewhere in every prospect assessment, a Monte Carlo model asks:

"What distribution do you want for the hydrocarbon–water contact?"

Uniform? Lognormal? PERT? Beta?

We spend months on depth conversion, structural mapping and reservoir modelling — and then answer
one of the most consequential questions in the whole assessment by picking a shape that looks
reasonable.

But the contact isn't an input. It's a *result*.

Charge can stop the column. So can spill, a leaking fault, top-seal capacity, seal continuity,
regional tilt, reservoir pinch-out. Each is a different geological problem, and each imposes its own
limit.

So sample the mechanisms instead of the contact. In every realisation, the shallowest active limit
wins:

HCWC = min(H_charge, H_spill, H_fault, H_seal, H_reservoir, …)

Run it thousands of times and the distribution becomes an output of your geology rather than an
assumption about it. And because the model records which limit won, it answers something a fitted
curve never can: what actually controls this column?

I've written up the reasoning — including why 46 % of the discoveries in the standard NCS dataset
are statistically censored rather than measured, and why that changes what the record is telling us.

Link in the comments. 👇

#Exploration #PetroleumGeology #ProspectEvaluation #RiskAndUncertainty #SubsurfaceGeoscience

---

## Option B — the censoring hook (sharper, more contrarian)

111 of the 242 NCS discoveries in Edmundson et al. (2021) filled to spill.

That's almost 46 % — and it quietly breaks the statistics we build on top of them.

A trap that filled to spill tells you the hydrocarbons reached the structural limit. It does not
tell you the maximum column the seal could have held. Maybe another 50 m. Maybe another 500 m. The
observation is a **lower bound, not a measurement** — censored, in the statistical sense.

Fit that dataset conventionally and trap height looks like the overwhelming control: a log-log
elasticity of 0.880, against 0.143 for burial depth.

Treat the filled-to-spill discoveries as censored and the same data gives 0.701 and 0.277.

The direction is robust even if the exact numbers move with the censoring definition. And the reason
is not subtle once you see it: every filled-to-spill accumulation sits on the structural limit by
definition, so the regression is partly fitting an identity imposed by the geometry of the trap.

It doesn't make burial depth the dominant control. It does mean we should be careful about what the
discovery record is actually telling us — especially when we use it to justify a contact
distribution.

I've written up the wider argument: why the hydrocarbon–water contact should be an output of
competing geological limits rather than a distribution we choose.

Link in the comments. 👇

#Exploration #PetroleumGeology #ProspectEvaluation #Geostatistics #SubsurfaceGeoscience

---

## Option C — short, for reach

"What distribution do you want for the hydrocarbon–water contact?"

Uniform? Lognormal? PERT?

It's the wrong question.

The contact isn't an input to the model. It's the result of a competition: charge, spill, fault
leakage, seal capacity, seal continuity, tilt, pinch-out. Each imposes a limit. In every realisation,
the shallowest active one wins.

Sample the mechanisms, not the contact — and the distribution becomes an output of your geology
instead of an assumption about it.

You also get the thing a fitted curve can never give you: which mechanism actually stopped the
column.

Full argument in the article below.

#Exploration #PetroleumGeology #ProspectEvaluation #SubsurfaceGeoscience

---

## First comment (post this yourself, immediately after publishing)

LinkedIn suppresses posts with outbound links in the body, so put the link here:

> Full article: [link]
>
> It covers the competing-limits construction, the censoring problem in the published discovery
> record, and how a DHI should update a contact distribution rather than replace it.
