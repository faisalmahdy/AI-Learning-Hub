---
id: interference-inter-01
title: Randomize by cluster when units affect each other — a shared resource lets the treatment cannibalize the control group and inflate the lift
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A/B testing rests on a quiet assumption — each unit's outcome depends only on its own assignment, not on anyone else's (the stable unit treatment value assumption, SUTVA) — and it is false exactly where units interact: a social feature where a treated user's activity draws in their control-group friends, a marketplace or shared finite resource where treated users consuming more leaves less for control users, a ranking or pricing change that shifts demand between the arms. When a treated unit can change a control unit's outcome, the control group has been touched by the treatment and is no longer an untreated counterfactual, so the treated-minus-control difference measures the effect plus the contamination. In the resource-competition case, treated users grab more of a fixed resource and cannibalize the control users sharing it, pushing the control conversion rate below its true untreated level and the treated rate above its true level — both distortions widen the gap, inflating the measured lift into an effect that is partly real and partly just treated users taking from control. Cluster randomization fixes it by assigning whole clusters — markets, regions, communities — to a single arm, so spillover lands on other treated units in the same cluster rather than on the control group, and the between-cluster comparison recovers the true effect (at the cost of statistical power, since the independent unit is now the cluster). On a fixture where the true effect from cluster randomization is a 0.20 lift, individual randomization in a shared-resource market reports 0.60 — three times too high — because the control rate was cannibalized from its true 0.40 down to 0.20.
eli5: Imagine testing whether giving some kids at a party a head start to the snack table makes them get more snacks. If you let half the kids start early while the other half wait, the early kids grab lots of snacks — but partly because they took the snacks the waiting kids would have gotten. So it looks like the head start helped a huge amount, when really some of that was just stealing from the other group. The fair test is to run two separate parties: one where everyone gets the head start and one where nobody does, and compare how many snacks each party goes through. Then no one is stealing from a comparison group, and you see the head start's real effect, which is much smaller.
---

## Why this module

The whole logic of an A/B test is that the control group shows you what would have happened without the treatment. That logic silently assumes the treatment reaches only the units assigned to it. For most changes that holds — one user's experience does not alter another's. But a large and important class of treatments spills across units: anything social, anything competing for a shared resource, anything that moves demand around. There, assigning a user to control does not make them untreated; it makes them a bystander to the treated users' effects.

When the control group is contaminated, the comparison breaks in a way no amount of sample size fixes, because it is a bias, not noise. If the spillover helps control units (a treated user engages their control friends), the control's outcome rises and the measured lift is understated. If it hurts them (treated users consume a shared resource), the control's outcome falls and the lift is overstated. Either way the treated-minus-control difference is contaminated by an effect of the treatment on the control group — the one group that was supposed to be free of it.

This module builds the resource-competition case, where cannibalization inflates the lift, and contrasts individual randomization with cluster randomization on the same treatment.

**Interference makes the control group no longer an untreated counterfactual, so individual A/B randomization measures the effect plus the contamination — here cannibalization of a shared resource inflates the lift, and cluster randomization is needed to recover the true effect.**

## Concepts

The fixture gives the same treatment measured two ways. In a mixed market, users are individually randomized and share a finite resource. In the cluster design, whole markets are assigned to one arm.

```json filename=modules/evals-and-statistics/code/interference-inter-01/interference.json:3-9 COMPLETE
  "mixed": {
    "treated": {"n": 5, "conv": 4},
    "control": {"n": 5, "conv": 1}
  },
  "clusters": {
    "treated_market": {"n": 10, "conv": 6},
    "control_market": {"n": 10, "conv": 4}
  }
```

The naive lift is the treated-minus-control conversion rate within the mixed, individually-randomized market. The cluster lift is the all-treated market's rate minus the all-control market's rate.

```python filename=modules/evals-and-statistics/code/interference-inter-01/interference.py:32-43 COMPLETE
def rate(cell):
    return cell["conv"] / cell["n"]


def naive_lift(mixed):
    """Individual randomization: treated rate minus control rate, within the shared-resource market."""
    return rate(mixed["treated"]) - rate(mixed["control"])


def cluster_lift(clusters):
    """Cluster randomization: all-treated market rate minus all-control market rate."""
    return rate(clusters["treated_market"]) - rate(clusters["control_market"])
```

The difference between these two lifts is the interference: in the mixed market the treated and control users share one resource, so measuring them against each other confounds the treatment's effect with the transfer between them.

<svg role="img" aria-label="In the mixed market treated users take resource from control users, so treated rate rises to 0.8 and control falls to 0.2; in separate cluster markets the true rates are 0.6 and 0.4" viewBox="0 0 320 130">
  <text x="10" y="12" font-size="8" fill="var(--muted)">shared resource: treated take from control (individual randomization)</text>
  <text x="14" y="30" font-size="7.5" fill="var(--s1)">treated 0.80</text>
  <rect x="80" y="22" width="160" height="12" fill="var(--s1)"/>
  <text x="14" y="48" font-size="7.5" fill="var(--s2)">control 0.20</text>
  <rect x="80" y="40" width="40" height="12" fill="var(--s2)"/>
  <path d="M 130 46 L 90 28" stroke="var(--ink)" stroke-width="1" marker-end="url(#a)"/>
  <text x="132" y="52" font-size="6.5" fill="var(--ink)">cannibalized →</text>
  <text x="10" y="76" font-size="8" fill="var(--muted)">separate markets: no transfer (cluster randomization)</text>
  <text x="14" y="94" font-size="7.5" fill="var(--s1)">treated mkt 0.60</text>
  <rect x="90" y="86" width="120" height="12" fill="var(--s1)"/>
  <text x="14" y="112" font-size="7.5" fill="var(--s2)">control mkt 0.40</text>
  <rect x="90" y="104" width="80" height="12" fill="var(--s2)"/>
  <text x="10" y="126" font-size="7.5" fill="var(--muted)">true lift 0.20; the mixed-market gap of 0.60 is inflated by the transfer</text>
</svg>
^ In the individually-randomized market, treated users pull resource from control users, so the treated rate rises to 0.80 and control falls to 0.20 — a 0.60 gap. In separate cluster markets there is no transfer, and the true rates are 0.60 and 0.40, a 0.20 lift. The extra 0.40 is cannibalization, not effect.

**The naive lift compares treated and control units that share a resource, so it confounds the treatment's effect with the transfer between them; the cluster lift compares self-contained markets with no transfer.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the experiment-design step of a marketplace test, reduced to small markets so every rate is checkable by hand.

Run `--designs` to see the two randomizations.

```text filename=interference.py --designs
  individual (shared market): treated 0.80, control 0.20 -> lift +0.60
  cluster (whole markets):    treated 0.60, control 0.40 -> lift +0.20
```

Individual randomization reports a 0.60 lift: treated users convert at 0.80, control at 0.20. Cluster randomization reports 0.20: the all-treated market converts at 0.60, the all-control market at 0.40. Same treatment, and the measured lift differs by 3×. One of these is the effect of the treatment; the other is the effect plus what the treated users took from control.

Now `--bias` names which is which — comparing the mixed-market control rate against the true untreated rate the cluster design reveals.

```python filename=modules/evals-and-statistics/code/interference-inter-01/interference.py:62-63 COMPLETE
    true_untreated = rate(clusters["control_market"])
    observed_control = rate(mixed["control"])
```

The two control rates should be equal; that they are not is the interference.

```text filename=interference.py --bias
  true lift (cluster)              = +0.20
  naive lift (individual)          = +0.60
  true untreated rate              = 0.40
  control rate under individual A/B = 0.20  (cannibalized)
```

The true untreated rate is 0.40 — that is what the control market converts at when no treated users are competing with it. But in the mixed market the control rate is 0.20, half of that: the treated users cannibalized it. The naive lift is inflated from both ends — the control was pushed down to 0.20 and the treated pushed up to 0.80 — so it reports 0.60 when the true effect is 0.20. The control group failed at its one job: to show what happens without the treatment. It could not, because the treatment reached it.

<svg role="img" aria-label="Bars comparing true lift 0.20 from cluster randomization against naive lift 0.60 from individual randomization, three times larger" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">measured lift (same treatment)</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s1)">true (cluster)</text>
  <rect x="100" y="30" width="52" height="16" fill="var(--s1)"/><text x="156" y="42" font-size="8" fill="var(--ink)">+0.20</text>
  <text x="10" y="70" font-size="8.5" fill="var(--s2)">naive (individual)</text>
  <rect x="100" y="60" width="156" height="16" fill="var(--s2)"/><text x="260" y="72" font-size="8" fill="var(--ink)">+0.60 (3x)</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">the extra 0.40 is cannibalization: the control rate pushed from 0.40 down to 0.20</text>
</svg>
^ The cluster design measures the true 0.20 lift; individual randomization reports 0.60, three times larger. The inflation is the cannibalization — the control group's rate driven from its true 0.40 down to 0.20 by the treated users sharing its resource.

**Individual randomization reports a 0.60 lift against a true 0.20 because the treated users cannibalized the control group's shared resource — driving the control rate from 0.40 to 0.20 — while cluster randomization, with no shared resource across arms, recovers the true effect.**

## Build

The self-test establishes the inflation and its mechanism: individual randomization reports a larger lift than cluster, the control rate is below the true untreated rate, and the treated rate is above the true treated rate.

```python filename=modules/evals-and-statistics/code/interference-inter-01/interference.py:83-91 COMPLETE
    naive_overstates = nl > cl
    print("  individual randomization reports a larger lift than cluster = %s (%+.2f > %+.2f)" % (naive_overstates, nl, cl))

    control_cannibalized = observed_control < true_untreated
    print("  the individual-A/B control rate is below the true untreated rate = %s (%.2f < %.2f)" % (control_cannibalized, observed_control, true_untreated))

    treated_inflated = rate(mixed["treated"]) > rate(clusters["treated_market"])
    print("  the individual-A/B treated rate is above the true treated rate = %s (%.2f > %.2f)"
          % (treated_inflated, rate(mixed["treated"]), rate(clusters["treated_market"])))
```

Then the diagnosis: the control group was affected by the treatment (interference), so the naive lift is inflated well beyond the true effect.

```python filename=modules/evals-and-statistics/code/interference-inter-01/interference.py:93-96 COMPLETE
    interference_present = observed_control != true_untreated
    print("  the control group was affected by the treatment (interference) = %s" % interference_present)

    naive_biased_high = nl > cl * 1.5
    print("  the naive lift is inflated well beyond the true effect = %s (%.2fx)" % (naive_biased_high, nl / cl))
```

Running the check confirms every clause.

```text filename=interference.py --check
  individual randomization reports a larger lift than cluster = True (+0.60 > +0.20)
  the individual-A/B control rate is below the true untreated rate = True (0.20 < 0.40)
  the individual-A/B treated rate is above the true treated rate = True (0.80 > 0.60)
  the control group was affected by the treatment (interference) = True
  the naive lift is inflated well beyond the true effect = True (3.00x)
```

**The check pins the inflation to interference — the control rate driven below its true level and the treated rate above — and shows the naive lift at 3× the true effect, while cluster randomization recovers the truth.**

## Definition of done

Done means individual randomization is shown to overstate the lift because the control group is contaminated (its rate below the true untreated rate), and cluster randomization recovers the true effect. The clause that the control rate differs from the true untreated rate is the definition of the SUTVA violation made concrete: the control group's outcome was changed by the treatment, which is precisely why it can no longer serve as the counterfactual.

Two clarifications keep this actionable. First, the direction of the bias depends on the interference. Resource competition (cannibalization) inflates the lift, as here. Positive spillover — a treated user engaging their control-group friends, a network effect that lifts everyone — does the opposite: it raises the control group's outcome, shrinking the measured lift and understating a real effect. Both are interference; both mean the individual-level estimate is wrong; only the sign changes. The reflex is to ask, before trusting any A/B result, whether a treated unit could plausibly affect a control unit, and through what channel. Second, cluster randomization is the fix but it is not free: your number of independent units drops from users to clusters, so the experiment loses power and needs either many clusters or a larger effect to detect. That is why it is reserved for genuine interference rather than used everywhere — the tradeoff is bias for variance. Where clusters are few, specialized designs (switchback experiments that alternate a single market between arms over time, or ego-cluster designs that isolate a user and their neighborhood) buy back some power while still containing the spillover.

<svg role="img" aria-label="Two interference directions: resource competition cannibalizes control and inflates the lift, positive spillover raises control and understates the lift; both break individual randomization" viewBox="0 0 320 118">
  <rect x="14" y="22" width="140" height="38" fill="none" stroke="var(--s2)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s2)">resource competition</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">control ↓ → lift inflated</text>
  <rect x="166" y="22" width="140" height="38" fill="none" stroke="var(--s1)"/>
  <text x="174" y="37" font-size="7.5" fill="var(--s1)">positive spillover</text>
  <text x="174" y="49" font-size="7" fill="var(--ink)">control ↑ → lift understated</text>
  <text x="14" y="80" font-size="7.5" fill="var(--muted)">both are interference; individual randomization is biased either way</text>
  <text x="14" y="100" font-size="7.5" fill="var(--ink)">fix: cluster (or switchback) randomization — trades power for unbiasedness</text>
</svg>
^ Interference biases the individual-level estimate in either direction — cannibalization inflates the lift, positive spillover understates it. Cluster (or switchback) randomization contains the spillover within an arm, trading statistical power for an unbiased estimate.

**Done means individual randomization overstates the lift via a contaminated control group and cluster randomization recovers the true effect — the reflex being to ask whether a treated unit can affect a control unit, and to cluster-randomize (accepting the power cost) when it can.**

## Boss fight

A ride-hailing team A/B tests a new feature that offers drivers a bonus to accept rides faster. They randomize individual drivers, and the treated drivers show a large increase in completed rides, so they ship it — but after launch to all drivers, the fleet-wide completed-rides number barely moves. Why did the A/B test overstate the effect, and how should they have tested it?

The A/B test violated SUTVA through resource competition: the number of ride requests in a city at any moment is a largely fixed pool, so a treated driver who accepts faster is often taking a ride that a control driver would otherwise have gotten. The treated group's completed rides went up partly by cannibalizing the control group's rides, which means the control group's completed-rides rate was pushed below its true untreated level, and the treated-minus-control difference measured the real effect plus the transfer between the groups — a large, inflated lift. When the feature launched to everyone, there was no control group to take rides from, so the fleet-wide number reflected only the true effect (getting rides completed slightly faster, not creating new rides), which is small — exactly the gap between the A/B result and the launch result. They should have randomized by cluster: assign whole cities (or time-separated windows within a city) to treatment or control, so the ride pool a treated driver competes for contains only other treated drivers, and compare completed rides between all-treated cities and all-control cities. That contains the cannibalization within each arm and estimates the true fleet-level effect. Because cities are few, a switchback design — alternating a single city between the feature on and off over successive time windows — is a common power-preserving alternative, using the city as its own control across time. The general lesson: whenever units compete for a shared, roughly fixed resource (rides, inventory, ad slots, attention), individual randomization will overstate the effect by cannibalization, and the experiment must be run at the level where the resource is shared.

## External resources

The experimentation literature on interference and SUTVA violations (the network-effects and marketplace-experiment work from LinkedIn, Meta, and ride-hailing/marketplace teams, and the treatments of cluster and switchback randomization) — why individual randomization is biased under interference, in which direction, and how cluster, ego-cluster, and switchback designs contain the spillover.

Causal-inference references on SUTVA and interference (the stable-unit-treatment-value assumption and the estimands available when it fails, including total and spillover effects) — the formal statement of why a contaminated control group is not a valid counterfactual and what can and cannot be estimated when units interact.
