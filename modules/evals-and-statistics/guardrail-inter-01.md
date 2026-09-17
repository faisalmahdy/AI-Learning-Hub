---
id: guardrail-inter-01
title: Gate the ship on guardrail metrics, not just the primary — a win on the metric you optimized can hide a regression in one you also care about
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: A team optimizes a primary metric and the A/B test shows it improved, which reads as a clean win — but an intervention almost never moves only its target. Making a feature stickier can slow the page, surface more errors, or cannibalize revenue; optimizing one number rarely leaves the others untouched, and some of those others matter too. Guardrail metrics are the secondary metrics you watch precisely to catch these side effects, each with a direction (higher-is-better or lower-is-better) and a regression limit — the worst move in the bad direction you are willing to tolerate — and a guardrail is breached when it moves in its bad direction by more than its limit. Deciding on the primary alone is blind to all of this: the primary improved, so the primary-only rule ships, and it ships whatever the guardrails did because it never looked at them, so a real regression in latency or errors or revenue rides along with the celebrated win and is discovered later in production as a mysterious degradation no one connects to the "successful" launch. The guardrail-aware rule is a conjunction: ship only if the primary improved AND no guardrail is breached — the primary tells you the feature did what you wanted, the guardrails tell you it did not do what you didn't want. On a fixture where engagement (primary) improved by 5 but latency rose 200ms past its 50ms budget and error rate rose 0.5 past its 0.1 limit, the primary-only rule ships while the guardrail-aware rule holds.
eli5: Imagine you're trying to make your car faster, and after some tinkering it does go faster — success! But you didn't notice that the same change made the brakes weak, the fuel gauge lie, and the doors stop locking. If you only looked at the speedometer, you'd proudly declare victory and drive off in a car that's now dangerous. The smart mechanic keeps a checklist of things that must not get worse — brakes, fuel, locks — and only signs off if the car got faster AND none of those got worse. Those "must not get worse" checks are guardrails. When you improve one thing, you have to make sure you didn't quietly break another, because the thing you were staring at getting better tells you nothing about the things you weren't watching.
---

## Why this module

Every intervention is a change to a system, and systems are coupled: pushing on one metric transmits force to others. A recommendation that boosts engagement may do so by loading more content, which raises latency; a checkout change that lifts conversion may increase support tickets; a growth feature may raise sign-ups while lowering revenue per user. The metric you chose to optimize is one output of a machine with many outputs, and moving it moves the others in ways you did not design and may not want.

The danger is that you are watching the one metric and not the others. Attention is selective by design in an experiment — you picked a primary metric, powered the test to detect a change in it, and framed the launch around it. That focus is what makes the side effects invisible: the experiment is set up to see the primary move and is not, unless you arrange it, set up to notice that something else moved too.

So a launch can be a genuine, statistically sound win on its primary metric and still be a net harm, because the harm landed on a metric outside the frame. Shipping on the primary alone codifies the blindness into the decision itself. This module scores an experiment with a primary win and several guardrails, one of which regressed, and shows the primary-only and guardrail-aware decisions diverging.

**Metrics are coupled, so optimizing one moves others; an experiment framed around a primary metric is blind to those side effects, so a real win on the primary can ship a real regression on a metric outside the frame.**

## Concepts

A guardrail metric is defined by two things beyond its value: a direction and a regression limit. The direction says which way is bad — latency and error rate are lower-is-better, revenue and retention are higher-is-better — and the limit says how far in the bad direction is tolerable before the launch should be blocked. Together they turn "keep an eye on latency" into a precise, automatable check: is the bad-direction move larger than the limit. That precision is what lets a guardrail gate a decision rather than merely inform a debate.

The decision rule is a conjunction, and the conjunction is the whole point. The primary check answers "did the feature do the good thing"; the guardrail checks answer "did it avoid the bad things"; and a launch must pass both, because a win purchased at the cost of a breached guardrail is frequently not a win at all. Replacing the conjunction with the primary alone drops the second clause entirely, so a breached guardrail cannot block anything — the rule has no term that even reads it.

It is worth naming why guardrails are the right tool rather than just "add the secondary metrics to the primary". You usually cannot combine latency, errors, revenue, and engagement into one comparable score — they are in different units and different importances — so the honest structure is not one weighted metric but one metric to improve and several to protect. The primary is optimized; the guardrails are constraints. That asymmetry — optimize one, constrain the rest — is exactly the guardrail pattern, and it is why a launch is a constrained win, not an unconstrained maximum.

<svg role="img" aria-label="The ship rule as an AND gate: the primary-improved check and the no-guardrail-breached check both feed one AND, and only both true yields ship" viewBox="0 0 440 120">
<rect x="20" y="25" width="150" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="95" y="41" fill="var(--ink)" font-size="9" text-anchor="middle">primary improved?</text>
<rect x="20" y="70" width="150" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="95" y="86" fill="var(--ink)" font-size="9" text-anchor="middle">no guardrail breached?</text>
<line x1="170" y1="37" x2="240" y2="52" stroke="var(--muted)"/>
<line x1="170" y1="82" x2="240" y2="68" stroke="var(--muted)"/>
<rect x="240" y="45" width="50" height="30" fill="var(--panel)" stroke="var(--ink)"/>
<text x="265" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">AND</text>
<line x1="290" y1="60" x2="350" y2="60" stroke="var(--muted)"/>
<rect x="350" y="48" width="70" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="385" y="64" fill="var(--ink)" font-size="9" text-anchor="middle">SHIP</text>
<text x="220" y="112" fill="var(--muted)" font-size="8" text-anchor="middle">primary-only drops the lower input — the gate can never see a breach</text>
</svg>
^ The ship decision is an AND of two checks; a primary-only rule deletes the lower input, so a breached guardrail can never block.

**A guardrail is a metric plus a direction plus a limit, which makes it a precise gate; the ship rule is the conjunction "primary improved AND no guardrail breached", because the launch must both achieve the good thing and avoid the bad ones — optimize one metric, constrain the rest.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/guardrail-inter-01. The fixture is an experiment's primary metric and three guardrails, each with a delta, a direction, and a regression limit.

```json filename=modules/evals-and-statistics/code/guardrail-inter-01/guardrail.json:3-5 COMPLETE
  "metrics": [
    {"name": "engagement", "delta": 5.0,   "higher_is_better": true,  "limit": 1.0,  "primary": true},
    {"name": "latency_ms", "delta": 200.0, "higher_is_better": false, "limit": 50.0, "primary": false},
```

A metric improved if it moved in its good direction.

```python filename=modules/evals-and-statistics/code/guardrail-inter-01/guardrail.py:34-36 COMPLETE
def improved(m):
    """Did the metric move in its good direction at all?"""
    return m["delta"] > 0 if m["higher_is_better"] else m["delta"] < 0
```

A guardrail is breached if it moved in its bad direction by more than its limit.

```python filename=modules/evals-and-statistics/code/guardrail-inter-01/guardrail.py:39-42 COMPLETE
def breached(m):
    """A guardrail is breached if it moved in its bad direction by more than its limit."""
    bad_move = -m["delta"] if m["higher_is_better"] else m["delta"]
    return bad_move > m["limit"]
```

Two helpers split the metrics into the one to optimize and the ones to protect.

```python filename=modules/evals-and-statistics/code/guardrail-inter-01/guardrail.py:45-50 COMPLETE
def primary(metrics):
    return next(m for m in metrics if m["primary"])


def guardrails(metrics):
    return [m for m in metrics if not m["primary"]]
```

First, the per-metric picture. Predict: engagement is a primary win, latency and error_rate breach their limits, revenue is fine. Run `--metrics`:

```text filename=guardrail.py --metrics
METRICS — each metric's move and whether it breaches its guardrail
--------------------------------------------------------------------
  metric       delta    better    limit   role       breached?
  engagement   5.0      higher    1.0     primary    -
  latency_ms   200.0    lower     50.0    guardrail  True
  error_rate   0.5      lower     0.1     guardrail  True
  revenue      0.2      higher    1.0     guardrail  False
--------------------------------------------------------------------
  a guardrail breaches when it moves the wrong way past its limit
```

The prediction holds. Engagement rose 5 (a win). Latency rose 200ms against a 50ms budget — breached. Error rate rose 0.5 against a 0.1 limit — breached. Revenue rose 0.2, a move in its good direction, so not breached. Two guardrails are red while the primary is green.

<svg role="img" aria-label="Four metrics: engagement improved (green), latency and error_rate breached their limits (red), revenue within limits (green)" viewBox="0 0 440 150">
<line x1="140" y1="20" x2="140" y2="130" stroke="var(--line)" stroke-dasharray="3 2"/>
<text x="140" y="145" fill="var(--muted)" font-size="8" text-anchor="middle">limit</text>
<text x="20" y="40" fill="var(--ink)" font-size="9">engagement</text>
<rect x="140" y="30" width="90" height="16" fill="var(--s1)"/>
<text x="240" y="42" fill="var(--s1)" font-size="8">win</text>
<text x="20" y="66" fill="var(--ink)" font-size="9">latency</text>
<rect x="140" y="56" width="150" height="16" fill="var(--s2)"/>
<text x="300" y="68" fill="var(--s2)" font-size="8">breached</text>
<text x="20" y="92" fill="var(--ink)" font-size="9">error_rate</text>
<rect x="140" y="82" width="130" height="16" fill="var(--s2)"/>
<text x="280" y="94" fill="var(--s2)" font-size="8">breached</text>
<text x="20" y="118" fill="var(--ink)" font-size="9">revenue</text>
<rect x="140" y="108" width="30" height="16" fill="var(--s1)"/>
<text x="180" y="120" fill="var(--s1)" font-size="8">ok</text>
</svg>
^ The primary is green and two guardrails cross their limit into the red — a mix a primary-only view never sees.

Now the decision. Run `--decide`:

```text filename=guardrail.py --decide
DECIDE — ship decision under each rule
------------------------------------------------------
  primary improved: True (engagement +5.0)
  guardrails breached: ['latency_ms', 'error_rate']
  primary-only rule    -> SHIP
  guardrail-aware rule -> HOLD
```

The two rules disagree, which is the whole lesson. The primary-only rule sees engagement up and ships — carrying the latency and error regressions into production with it. The guardrail-aware rule sees the same engagement win but also the two breaches, and holds. Same experiment, same data; the difference is only whether the decision looked at the guardrails.

<svg role="img" aria-label="Two decision rules on the same experiment: primary-only sees only engagement and ships; guardrail-aware sees engagement plus the breached guardrails and holds" viewBox="0 0 440 140">
<rect x="20" y="30" width="180" height="80" fill="var(--panel)" stroke="var(--s2)"/>
<text x="110" y="50" fill="var(--ink)" font-size="10" text-anchor="middle">primary-only</text>
<text x="110" y="70" fill="var(--muted)" font-size="8" text-anchor="middle">sees: engagement up</text>
<text x="110" y="98" fill="var(--s2)" font-size="11" text-anchor="middle">SHIP (harm rides along)</text>
<rect x="240" y="30" width="180" height="80" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="50" fill="var(--ink)" font-size="10" text-anchor="middle">guardrail-aware</text>
<text x="330" y="70" fill="var(--muted)" font-size="8" text-anchor="middle">sees: engagement up,</text>
<text x="330" y="82" fill="var(--muted)" font-size="8" text-anchor="middle">latency + errors breached</text>
<text x="330" y="102" fill="var(--s1)" font-size="11" text-anchor="middle">HOLD</text>
</svg>
^ The primary-only rule ships the regression because it never read the guardrails; the guardrail-aware rule holds on the same data.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the primary improved, that at least one guardrail is breached, that the primary-only rule ships, that the guardrail-aware rule holds, and that the two rules therefore disagree.

```python filename=modules/evals-and-statistics/code/guardrail-inter-01/guardrail.py:92-101 COMPLETE
    primary_improved = improved(p)
    print("  the primary metric improved = %s (%s %+.1f)" % (primary_improved, p["name"], p["delta"]))

    some_guardrail_breached = any(breached(g) for g in gr)
    print("  at least one guardrail is breached = %s (%s)" % (some_guardrail_breached, [g["name"] for g in gr if breached(g)]))

    primary_only_ships = primary_improved
    print("  primary-only rule ships = %s" % primary_only_ships)

    guardrail_aware_holds = not (primary_improved and not some_guardrail_breached)
    print("  guardrail-aware rule holds = %s" % guardrail_aware_holds)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the guardrail-aware rule ever ships a breached launch:

```text filename=guardrail.py --check
SELF-TEST — the primary improves while guardrails are breached; primary-only ships the harm, guardrail-aware holds
------------------------------------------------------------------------------------------------------------------------
  the primary metric improved = True (engagement +5.0)
  at least one guardrail is breached = True (['latency_ms', 'error_rate'])
  primary-only rule ships = True
  guardrail-aware rule holds = True
  the two rules disagree (one ships, one holds) = True
```

**The self-test pins the disagreement — the primary-only rule ships exactly the launch the guardrail-aware rule holds — proving the decisions diverge on a real primary win, not on a primary that failed.**

## Definition of done

You can explain why metrics are coupled and why an experiment framed around a primary metric is structurally blind to side effects on others.
You can define a guardrail metric by its three parts — value, direction, regression limit — and state what "breached" means.
You can state the ship rule as a conjunction (primary improved AND no guardrail breached) and explain why dropping the second clause is the bug.
You can explain why guardrails are constraints rather than terms in a single combined score, given the metrics' different units and importances.
You can give examples of a win on one metric that harms another (engagement vs latency, conversion vs support load, sign-ups vs revenue-per-user).

## Boss fight

Consider the statistics of the guardrails, not just their point estimates. A guardrail check compares a delta to a limit, but the delta is itself noisy, so you face two errors: a guardrail that truly regressed but whose noisy estimate landed inside the limit (a missed regression you ship), and a guardrail that is fine but whose noise pushed it past the limit (a false block that kills a good launch). This means guardrails need to be powered too — the experiment must be large enough to detect a meaningful regression in each guardrail, not just in the primary — and the limit should account for the confidence interval, not the point estimate alone. The lesson deepens: a guardrail is a hypothesis test like any other, and an underpowered guardrail gives false assurance, quietly passing regressions it could not have detected.

Now consider the multiple-comparisons interaction. Every guardrail you add is another test, so with enough guardrails, one will breach by chance even when nothing is wrong, and a strict "hold if any guardrail breaches" rule starts blocking good launches on noise. The resolution is not to drop guardrails but to treat them as a family: set the limits from the metrics' real tolerances (a guardrail should block on a regression that matters, not on any detectable move), and correct for the number of guardrails when the breach is a significance test rather than a fixed business threshold. The two hazards pull in opposite directions — too few or too-loose guardrails ship harm, too many or too-tight ones block good launches on noise — and calibrating them is the real work.

**Guardrails are noisy tests, so they must be powered (an underpowered guardrail passes regressions it cannot detect) and judged on their confidence interval, not the point estimate; and because each guardrail is another test, many of them breach by chance, so the limits must reflect real tolerances and the family must be corrected — too loose ships harm, too tight blocks good launches on noise.**

## External resources

Kohavi, Tang, and Xu's "Trustworthy Online Controlled Experiments" devotes substantial attention to guardrail (and "counter") metrics and how to set and monitor them.
Microsoft's and other experimentation platforms' documentation on guardrail metrics describes the optimize-one-constrain-the-rest structure and the powering of guardrail checks.
The topic's own modules on heterogeneous treatment effects and on practical significance cover adjacent ways a headline result can be misleading about a launch's true impact.
