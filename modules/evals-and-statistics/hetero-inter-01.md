---
id: hetero-inter-01
title: Check the effect per segment, not just the average — a positive overall A/B result can hide a segment it harms
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: An A/B test reports one headline number: the average treatment effect, how much the change moved the metric across all users, and ship decisions are usually made on it — positive, ship it; negative, kill it. But the average is a single summary of what may be very different experiences underneath. A change does not affect everyone the same way: it can help one kind of user and hurt another (a simpler interface that delights newcomers but strips out shortcuts power users depend on; a model that improves the common case and regresses on a rare-but-important one). When the effect varies across segments — a heterogeneous treatment effect — the overall average is a weighted blend, and if the helped segment is large enough, the average comes out positive even while a smaller segment is actively harmed. The team sees a green number and ships a change that made a valuable minority worse. The average is not wrong, it is incomplete: it silently sums a big win for one group with a real loss for another, and the harm never appears on the dashboard because the dashboard shows the mean. The fix is to look at the effect by segment before shipping — break the result down along the axes that matter and check whether any important segment regressed, even when the overall number is positive — so a positive average with a harmed key segment is a decision made deliberately, not by accident. On a fixture where the change helps new users (+10, 700 of them) and hurts power users (−4, 300 of them), the size-weighted overall effect is +5.8 so an average-only view ships it, while the per-segment view shows power users regressed and flags the harm.
eli5: Imagine a new recipe you test on a big group: most people (the crowd) love it and rate it way up, but a small group who are allergic to one ingredient get sick. If you just average all the ratings together, the recipe looks like a big hit — the happy crowd drowns out the few who were harmed — so you'd serve it to everyone. But the average hid something important: it didn't make everyone a little happier, it made most people much happier and a few people worse off. To decide fairly, you have to look at the groups separately, notice "wait, this group got hurt," and choose on purpose — fix the recipe for them, warn them, or hold off — instead of letting the happy average bury the harm.
---

## Why this module

A single average is a comfortable thing to ship on and a dangerous thing to trust, because it reports the experience of a user who may not exist. When a change affects different users differently, the mean is a blend, and a blend can be positive for reasons that have nothing to do with any individual being helped — it can be positive because a large group gained a lot and a smaller group's loss got averaged into invisibility. The team reads +5.8, reads it as "the change is good," and ships — never seeing that the number is the sum of a big win and a real loss, and that some of their users are on the wrong side of it.

A change does not affect everyone the same way: it can help one kind of user and hurt another. When the effect varies across segments — a heterogeneous treatment effect — the overall average is a weighted blend, and if the helped segment is large enough, the average comes out positive even while a smaller segment is being actively harmed. The average is not wrong, it is incomplete: it silently sums a big win for one group with a real loss for another, and the harm never appears on the dashboard because the dashboard only shows the mean.

The fix is to look at the effect by segment before shipping, not only in aggregate: break the result down along the axes that matter (tenure, platform, region, usage level) and check whether any important segment regressed, even when the overall number is positive. A positive average with a harmed key segment is a decision to make deliberately, not by accident. This module computes the average and the per-segment breakdown.

**An A/B test's average treatment effect can be positive while the change harms an important subgroup, because the average blends a large helped segment with a smaller harmed one, so evaluate the effect per segment before shipping and treat a regressed key segment as a real cost — not as noise the positive average absolves.**

## Concepts

**The overall effect is the size-weighted average; the harmed segments are the ones with a negative effect.**

```python filename=modules/evals-and-statistics/code/hetero-inter-01/hetero.py:51-59 COMPLETE
def overall_effect(segments):
    """The size-weighted average treatment effect across all users."""
    total = sum(s["size"] for s in segments)
    return sum(s["effect"] * s["size"] for s in segments) / total


def harmed_segments(segments):
    """Segments the change made worse (negative effect)."""
    return [s for s in segments if s["effect"] < 0]
```

**The two ship rules differ in what they require:** the naive one ships on a positive average; the segment-aware one also requires no segment to have regressed.

```python filename=modules/evals-and-statistics/code/hetero-inter-01/hetero.py:62-69 COMPLETE
def ship_on_average(segments):
    """Naive decision: ship if the overall effect is positive."""
    return overall_effect(segments) > 0


def ship_with_segments(segments):
    """Segment-aware decision: only 'clear to ship' if positive overall AND no segment regressed."""
    return overall_effect(segments) > 0 and not harmed_segments(segments)
```

<svg role="img" aria-label="Two segments' effects: new users plus 10 (large, 700 users), power users minus 4 (smaller, 300 users); the size-weighted average is plus 5.8" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">effect per segment, and the size-weighted blend</text>
  <line x1="120" y1="24" x2="120" y2="88" stroke="var(--grid)"/><text x="108" y="100" fill="var(--muted)" font-size="6">0</text>
  <text x="10" y="38" fill="var(--muted)" font-size="7">new users</text>
  <rect x="120" y="30" width="120" height="12" fill="var(--s1)"/><text x="244" y="40" fill="var(--muted)" font-size="6">+10 (700)</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">power users</text>
  <rect x="72" y="52" width="48" height="12" fill="var(--s2)"/><text x="30" y="62" fill="var(--s2)" font-size="6">-4 (300)</text>
  <line x1="120" y1="72" x2="240" y2="72" stroke="var(--grid)"/>
  <text x="10" y="84" fill="var(--muted)" font-size="7">overall</text>
  <rect x="120" y="76" width="70" height="10" fill="var(--ink)"/><text x="194" y="85" fill="var(--muted)" font-size="6">+5.8 (blend)</text>
  <text x="10" y="104" fill="var(--muted)" font-size="6">the big +10 for new users pulls the blend positive despite power users' -4</text>
</svg>
^ New users gain +10 and power users lose −4, but because new users are the larger group the size-weighted blend lands at +5.8 — positive — so the harm to power users is real yet invisible in the one number a ship decision usually reads.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/hetero-inter-01/hetero.py

The fixture is two segments with their sizes and the treatment's effect on each.

```json filename=modules/evals-and-statistics/code/hetero-inter-01/hetero.json:3-6 COMPLETE
  "segments": [
    {"name": "new_users", "size": 700, "effect": 10},
    {"name": "power_users", "size": 300, "effect": -4}
  ]
```

Run `--segments`.

```text filename=--segments
SEGMENTS — per-segment effect and the size-weighted overall effect
------------------------------------------------------------
  segment       size   share   effect
  new_users     700    70%    +10
  power_users   300    30%    -4  <- harmed
------------------------------------------------------------
  overall (size-weighted) effect = +5.8
```

Read the effect column against the overall line. New users, 70% of the base, gained +10; power users, 30% of the base, lost −4. The size-weighted overall effect is 0.7×10 + 0.3×(−4) = 7 − 1.2 = +5.8. That +5.8 is a genuinely positive result — the change did, on average, improve the metric — and a team that reads only the aggregate sees a clean win and ships. But the "power_users → harmed" tag is the story the average erased: a valuable segment, nearly a third of the users, was made measurably worse by the change. The positive average did not happen because the change was good for everyone; it happened because the group it helped was more than twice the size of the group it hurt, and the arithmetic of the weighted mean let the large win swallow the smaller loss. Nothing about the number 5.8 tells you that underneath it, one in three users regressed.

## Build

The two decision rules diverge exactly on this case.

```text filename=--decision
DECISION — ship on the average vs ship with segments checked
--------------------------------------------------------------
  overall effect = +5.8
  SHIP ON AVERAGE:   overall positive -> ship = True
  SHIP WITH SEGMENTS: any segment regressed? ['power_users']
                      clear to ship = False
```

<svg role="img" aria-label="Three options once the harm is surfaced: ship to all (power users regress), ship to new users only (targeted), or hold; the segment breakdown enables the choice" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">surfacing the harm turns one number into a real choice</text>
  <text x="10" y="30" fill="var(--s2)" font-size="7">ship to all</text>
  <rect x="90" y="22" width="120" height="10" fill="var(--s1)"/><rect x="210" y="22" width="50" height="10" fill="var(--s2)"/><text x="214" y="30" fill="var(--panel)" font-size="6">power −4</text>
  <text x="10" y="50" fill="var(--s1)" font-size="7">new users only</text>
  <rect x="90" y="42" width="120" height="10" fill="var(--s1)"/><text x="214" y="50" fill="var(--muted)" font-size="6">power unchanged</text>
  <text x="10" y="70" fill="var(--muted)" font-size="7">hold / fix</text>
  <rect x="90" y="62" width="30" height="10" fill="none" stroke="var(--muted)"/><text x="124" y="70" fill="var(--muted)" font-size="6">fix the power-user path first</text>
  <text x="10" y="90" fill="var(--muted)" font-size="6">all three are valid — but only visible once the segment breakdown exists</text>
</svg>
^ Once the power-user regression is surfaced, the decision opens up into real options — ship to all and accept the harm, roll out to new users only, or hold until the power-user path is fixed — each defensible, and each invisible to a team that saw only the +5.8 average.

The ship-on-average rule looks at +5.8, sees positive, and returns ship = True — the change goes out, power users' regression along with it. The segment-aware rule computes the same +5.8 but also asks a second question: did any segment regress? It finds power_users did, and so it does not clear the change to ship — not because the change is bad on average (it is not), but because "good on average" is not the same as "safe to ship," and the difference is precisely the harmed segment. This does not mean the change can never ship; it means the decision has been surfaced instead of buried. With the segment breakdown in hand, the team can make a real choice: ship anyway because the power-user regression is acceptable and the overall win is large; ship a variant that fixes the power-user path; hold until the regression is addressed; or roll out to new users only. All of those are legitimate, and all of them require knowing the harm exists — which is exactly what the average hid. The general principle is that an average is a decision-making tool only when the thing it averages is roughly uniform; when the effect is heterogeneous, the average must be accompanied by the distribution, because the mean of a mixture can be positive while an important part of the mixture is negative, and ship decisions live in the parts, not the mean.

```python filename=modules/evals-and-statistics/code/hetero-inter-01/hetero.py:107-114 COMPLETE
    overall_positive = oe > 0
    print("  the overall treatment effect is positive = %s (%+.1f)" % (overall_positive, oe))

    a_segment_harmed = len(harmed) > 0
    print("  at least one segment was harmed = %s (%s)" % (a_segment_harmed, [(s["name"], s["effect"]) for s in harmed]))

    average_hides_harm = overall_positive and a_segment_harmed
    print("  a positive average hides a harmed segment = %s" % average_hides_harm)
```

## Definition of done

The self-test pins the positive average, the harmed segment, the average masking it, and the two decisions diverging.

```python filename=modules/evals-and-statistics/code/hetero-inter-01/hetero.py:116-119 COMPLETE
    ship_on_average_says_yes = ship_on_average(segs)
    print("  ship-on-average would ship it = %s" % ship_on_average_says_yes)

    segments_flag_it = not ship_with_segments(segs)
    print("  the segment-aware check does NOT clear it to ship = %s" % segments_flag_it)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the overall effect is positive while a segment is harmed; the average hides it, segmentation surfaces it
----------------------------------------------------------------------------------------------------------------------
  the overall treatment effect is positive = True (+5.8)
  at least one segment was harmed = True ([('power_users', -4)])
  a positive average hides a harmed segment = True
  ship-on-average would ship it = True
  the segment-aware check does NOT clear it to ship = True
```

<svg role="img" aria-label="The overall effect is a positive bar at plus 5.8, but the power-users segment is a negative bar at minus 4; ship-on-average sees only the positive bar" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">what each decision rule sees</text>
  <line x1="140" y1="22" x2="140" y2="82" stroke="var(--grid)"/><text x="130" y="92" fill="var(--muted)" font-size="6">0</text>
  <text x="10" y="36" fill="var(--muted)" font-size="7">ship-on-avg sees</text>
  <rect x="140" y="28" width="80" height="12" fill="var(--s1)"/><text x="224" y="38" fill="var(--muted)" font-size="7">+5.8 → ship</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">segment view sees</text>
  <rect x="140" y="52" width="80" height="12" fill="var(--s1)"/><text x="224" y="62" fill="var(--muted)" font-size="6">+5.8 overall</text>
  <rect x="92" y="68" width="48" height="12" fill="var(--s2)"/><text x="40" y="78" fill="var(--s2)" font-size="6">power −4 → flag</text>
  <text x="10" y="92" fill="var(--muted)" font-size="6">the segment view keeps the negative bar the average absorbed</text>
</svg>
^ Ship-on-average sees only the +5.8 bar and ships; the segment view keeps both bars — the +5.8 overall and the −4 for power users — so it flags the harm the average absorbed, turning an accidental ship into a deliberate choice.

**Done means the masked harm is proven on real numbers: the change helps new users (+10) and hurts power users (−4), and the size-weighted overall effect is +5.8, so ship-on-average returns True while the segment-aware check finds power_users regressed and does not clear it to ship — so an A/B result must be evaluated per segment, because a positive average can hide a harmed subgroup.**

## Boss fight

Predict two ways segment analysis is harder than "break it down and look," because slicing data has its own statistical traps and heterogeneity cuts both ways.

The first trap is that segmenting multiplies your comparisons and shrinks your samples, so naive subgroup analysis manufactures false harms as easily as it reveals real ones. If you slice a result into twenty segments and test each, some will show a "regression" by pure chance even if the change is uniformly neutral or positive — this is the multiple-comparisons problem applied to subgroups, and it is why medical trials treat unplanned subgroup findings with deep suspicion (the famous cautionary examples of drugs that "worked" only for people born under certain astrological signs come from exactly this). And each segment has a smaller sample than the whole, so its effect estimate is noisier, meaning a segment can look harmed when the true effect is zero and you got an unlucky draw. So segment analysis has to be disciplined: pre-register the segments you care about (the ones with a real product or fairness reason to matter, not every sliceable dimension), correct for multiple comparisons or use shrinkage/hierarchical models that pull noisy segment estimates toward the overall effect, and require a segment's harm to clear the noise of its own smaller sample before treating it as real. Otherwise you replace the average's blindness with a fishing expedition that flags harms that are not there — and chasing phantom regressions is its own way to make bad decisions.

The second trap is that heterogeneity is not only a risk to guard against but information to act on, and the deepest failure is treating "the average is positive" and "the average is negative" as the only two outcomes. A change with strongly heterogeneous effects is telling you something: the same treatment is right for some users and wrong for others, which often means the right product decision is not one global ship-or-kill but a targeted or personalized rollout — ship it to the segment it helps, withhold it from the segment it harms, or build the variant each needs. The average, by collapsing the distribution, throws away exactly the signal that would let you do better than a single global decision. This is why modern experimentation looks at conditional average treatment effects (CATE) and uses uplift modeling to find who responds well, not just whether the population does on average — the goal shifts from "is this change good?" to "for whom is this change good, and can we give each group the right treatment?" So segmentation is not merely a safety check that can veto a ship; it is the input to a better class of decision than ship-or-kill, and a positive-but-heterogeneous result is an opportunity to target, not just a landmine to avoid. Reporting the average alone forecloses that entirely.

**Disciplined segmentation, not fishing: slicing multiplies comparisons and shrinks samples, so unplanned subgroups manufacture false harms — pre-register the segments that matter, correct for multiple comparisons or shrink noisy segment estimates toward the overall effect, and require a harm to clear its own smaller sample's noise before acting. And heterogeneity is signal, not just risk: a strongly varying effect means the right decision is often targeted, not global (ship to the helped segment, withhold from the harmed one, build the variant each needs), so use conditional/uplift analysis to ask 'for whom is this good?' — the average forecloses that better decision by collapsing the distribution it lives in.**

## External resources

Experimentation and causal-inference references on heterogeneous treatment effects, conditional average treatment effects (CATE), and uplift modeling — how effects vary by segment, how to estimate them without overfitting, and how targeting beats a global ship-or-kill.

Writing on subgroup analysis pitfalls in clinical trials and A/B testing (the multiple-comparisons and small-sample hazards, pre-registration of subgroups) — why unplanned subgroup findings are treated skeptically and how to segment responsibly.

The companion multiple-comparisons, guardrail-metric, and imbalance modules in this topic — subgroup analysis reintroduces the multiple-comparisons risk those modules address, a harmed segment is a guardrail failure the primary metric hides, and both are cases where one aggregate number conceals what the breakdown reveals.
