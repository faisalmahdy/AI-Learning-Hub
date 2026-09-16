---
id: confound-inter-01
title: A correlation can be a confounder's shadow — control for the common cause and check whether the association survives
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: Two things move together in the data, so it is tempting to say one drives the other — but a correlation between X and Y has three possible sources: X causes Y, Y causes X, or a third variable causes both. That third variable is a confounder, and when it is the real story the X–Y correlation is genuine in the data and entirely non-causal: intervening on X would do nothing to Y, because the link runs through the confounder, not between them. Ice-cream sales and drownings rise together, but ice cream drowns no one; hot weather independently drives both (people buy ice cream, and people swim), so the two effects of one cause look like a cause and an effect. The test for confounding is to control for the suspected common cause — look at the X–Y relationship within each level of the confounder, holding it fixed, not pooled across all levels. If X really affects Y, the association persists within groups; if the confounder is the whole story, it vanishes within groups, because the thing that was making both move is no longer varying. So "correlation is not causation" is a procedure: name the plausible common causes and check whether the association survives controlling for them — one that survives every plausible confounder is a candidate for causation, one that evaporates was confounded (and randomizing X, which breaks any confounder's link to X, is why experiments are the gold standard). On a fixture where ice cream and drownings are strongly associated pooled (above-median-ice-cream days have 4 more drownings), the association is 0 within each temperature group — holding weather fixed, ice cream does not track drownings, so the pooled correlation was temperature's shadow.
eli5: Imagine you notice that on days when lots of ice cream is sold, lots of people also drown, and you conclude ice cream is dangerous. But think about what's really going on: on hot days, people buy ice cream AND people go swimming (and some drown). The heat is causing both — the ice cream and the drownings are two separate results of the same hot day, not a cause and an effect of each other. Here's how to check: look only at hot days, all with about the same weather. If you compare hot days with more ice cream to hot days with less, do the drownings change? No — because once you're only looking at hot days, the ice cream isn't what's driving anything. The link disappears the moment you hold the weather still, which tells you the weather was the real cause all along.
---

## Why this module

"Correlation is not causation" is the most-repeated warning in statistics and the least often acted on, because it is usually stated as a caution rather than a method. Confounding is the mechanism behind most of the false causal claims the warning is meant to catch, and understanding it turns the caution into a concrete procedure you can run on any correlation. The core idea is that when X and Y move together, a third variable that causes both will produce exactly that pattern — a real, replicable correlation with no causal link between X and Y at all — and you can test for it.

The setup is a common cause. Some variable drives both X and Y, so their values rise and fall together as the common cause varies, and pooling all the data shows a strong X–Y correlation. But the correlation is the confounder's shadow: it exists only because the confounder is varying across the data, dragging both X and Y along. Nothing passes from X to Y.

The test follows directly from the mechanism: hold the confounder fixed and see if the correlation survives. This module takes the textbook ice-cream-and-drownings confound and measures the association pooled and within each level of the confounder.

**Before reading a correlation as causal, control for plausible common causes by examining the association within each level of the confounder — because a confounder that drives both variables produces a real but non-causal correlation that vanishes once the confounder is held fixed, while a genuine causal effect persists within groups.**

## Concepts

The fixture is days of data, each with ice-cream sales (x) and drownings (y), grouped by the confounder, temperature. On cold days both are low; on hot days both are high.

```json filename=modules/ai-for-science-and-data/code/confound-inter-01/confound.json:3-9 COMPLETE
  "x": "ice_cream",
  "y": "drownings",
  "confounder": "temperature",
  "groups": {
    "cold": [{"x": 10, "y": 1}, {"x": 30, "y": 1}],
    "hot": [{"x": 70, "y": 5}, {"x": 90, "y": 5}]
  }
```

The association measure is how much y tracks x: mean y on above-median-x points minus mean y on below-median-x points. Positive means high x goes with high y.

```python filename=modules/ai-for-science-and-data/code/confound-inter-01/confound.py:33-41 COMPLETE
def association(points):
    """Mean y on above-median-x points minus mean y on below-median-x points -- how much y tracks x."""
    xs = [p["x"] for p in points]
    med = statistics.median(xs)
    hi = [p["y"] for p in points if p["x"] > med]
    lo = [p["y"] for p in points if p["x"] < med]
    if not hi or not lo:
        return 0.0
    return statistics.mean(hi) - statistics.mean(lo)
```

The pooled association measures x against y across all days; the within-group associations measure it inside each temperature level, holding the confounder fixed.

```python filename=modules/ai-for-science-and-data/code/confound-inter-01/confound.py:44-53 COMPLETE
def all_points(groups):
    return [p for g in groups.values() for p in g]


def pooled_association(groups):
    return association(all_points(groups))


def within_group_associations(groups):
    return {name: association(pts) for name, pts in groups.items()}
```

<svg role="img" aria-label="A causal diagram: temperature points to both ice cream and drownings; ice cream and drownings have no arrow between them, only a dashed spurious correlation" viewBox="0 0 320 120">
  <rect x="120" y="10" width="80" height="22" fill="none" stroke="var(--ink)" stroke-width="1.5"/><text x="130" y="25" font-size="9" fill="var(--ink)">temperature</text>
  <rect x="20" y="80" width="80" height="22" fill="none" stroke="var(--s1)" stroke-width="1.2"/><text x="34" y="95" font-size="8.5" fill="var(--ink)">ice cream</text>
  <rect x="220" y="80" width="80" height="22" fill="none" stroke="var(--s2)" stroke-width="1.2"/><text x="236" y="95" font-size="8.5" fill="var(--ink)">drownings</text>
  <line x1="140" y1="32" x2="70" y2="78" stroke="var(--ink)" stroke-width="1.5"/>
  <line x1="180" y1="32" x2="250" y2="78" stroke="var(--ink)" stroke-width="1.5"/>
  <path d="M 100 96 Q 160 116 220 96" fill="none" stroke="var(--muted)" stroke-width="1.2" stroke-dasharray="4 3"/>
  <text x="120" y="115" font-size="8" fill="var(--muted)">spurious correlation (no arrow)</text>
</svg>
^ Temperature causes both ice cream and drownings; there is no arrow between ice cream and drownings. The dashed correlation between them is real in the data but non-causal — it exists only because their common cause varies. Holding temperature fixed removes the varying cause, and the dashed link disappears.

**A confounder produces the exact statistical signature of causation — a strong, replicable correlation — while the causal arrow it implies does not exist, which is why a correlation alone can never establish it.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the causal-inference step of a data analysis, reduced to four days so every association is checkable by hand.

Run `--pooled` to see the correlation across all days.

```text filename=confound.py --pooled
  ice_cream=10   drownings=1   (cold)
  ice_cream=30   drownings=1   (cold)
  ice_cream=70   drownings=5   (hot)
  ice_cream=90   drownings=5   (hot)
  pooled association (above-median vs below-median ice_cream): +4 more drownings
```

Pooled, the pattern is stark: the two low-ice-cream days have 1 drowning each, the two high-ice-cream days have 5 each. Above-median-ice-cream days average 4 more drownings than below-median days. Read causally, this says selling ice cream causes drownings — a strong, clean, replicable association pointing the wrong way.

Now `--control` holds temperature fixed.

```text filename=confound.py --control
  cold  : ice_cream ranges 10-30, drownings association = +0
  hot   : ice_cream ranges 70-90, drownings association = +0
  holding temperature fixed, ice_cream does not track drownings
```

Within the cold days, ice cream varies from 10 to 30 and drownings stay at 1 — association 0. Within the hot days, ice cream varies from 70 to 90 and drownings stay at 5 — association 0. Once the weather is held fixed, ice-cream sales have no relationship with drownings at all. The entire pooled association of +4 came from temperature: hot days simply had more of both. Controlling for the confounder made the correlation vanish, which is the signature of a spurious, non-causal association.

**The pooled +4 association collapses to 0 within every temperature group — ice cream does not track drownings once the weather is fixed, so the correlation was temperature's shadow, not a causal effect.**

## Build

The self-test asserts the confounding structure: the pooled association is large, it is 0 within every group, and the confounder drives both x and y.

```python filename=modules/ai-for-science-and-data/code/confound-inter-01/confound.py:87-97 COMPLETE
    pooled_association_large = abs(pooled) >= 3
    print("  the pooled association is large = %s (+%.0f more %s on high-%s days)" % (pooled_association_large, pooled, data["y"], data["x"]))

    within_all_zero = all(abs(a) < 1e-9 for a in within.values())
    print("  the association is 0 within every %s group = %s (%s)" % (data["confounder"], within_all_zero, {k: round(v, 1) for k, v in within.items()}))

    confounder_drives_x = statistics.mean(p["x"] for p in groups["hot"]) > statistics.mean(p["x"] for p in groups["cold"])
    print("  the confounder drives x (hot days have higher %s) = %s" % (data["x"], confounder_drives_x))

    confounder_drives_y = statistics.mean(p["y"] for p in groups["hot"]) > statistics.mean(p["y"] for p in groups["cold"])
    print("  the confounder drives y (hot days have higher %s) = %s" % (data["y"], confounder_drives_y))
```

<svg role="img" aria-label="Pooled association bar of +4 shrinking to 0 bars within the cold and hot groups" viewBox="0 0 320 110">
  <text x="10" y="18" font-size="8.5" fill="var(--muted)">ice_cream → drownings association</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">pooled</text>
  <rect x="90" y="32" width="160" height="16" fill="var(--s2)"/><text x="254" y="45" font-size="8" fill="var(--ink)">+4</text>
  <text x="10" y="68" font-size="8.5" fill="var(--s1)">within cold</text>
  <rect x="90" y="58" width="2" height="16" fill="var(--s1)"/><text x="98" y="71" font-size="8" fill="var(--ink)">0</text>
  <text x="10" y="94" font-size="8.5" fill="var(--s1)">within hot</text>
  <rect x="90" y="84" width="2" height="16" fill="var(--s1)"/><text x="98" y="97" font-size="8" fill="var(--ink)">0</text>
</svg>
^ The pooled association is a large +4; within each temperature group it is 0. The bar collapsing to nothing when the confounder is held fixed is the visual signature of a confounded (non-causal) correlation.

Running the check confirms every clause, including that controlling removes the association and there is no causal effect.

```text filename=confound.py --check
  the pooled association is large = True (+4 more drownings on high-ice_cream days)
  the association is 0 within every temperature group = True ({'cold': 0, 'hot': 0})
  the confounder drives x (hot days have higher ice_cream) = True
  the confounder drives y (hot days have higher drownings) = True
  controlling for the confounder removes the association = True (pooled +4 -> within ~0)
  x does not causally affect y (no within-group effect) = True
```

**The check ties the large pooled association to a confounder that drives both variables and shows it vanishing on control — the correlation is real and non-causal, exactly the pattern confounding produces.**

## Definition of done

Two properties close it. Controlling for the confounder must remove the association (the pooled effect vanishes within groups), and that vanishing must license the causal conclusion — x does not affect y, because holding the confounder fixed leaves no within-group effect. Together they distinguish a confounded correlation from a genuine effect: a real cause would survive the control.

```python filename=modules/ai-for-science-and-data/code/confound-inter-01/confound.py:99-103 COMPLETE
    control_removes_association = abs(max(within.values(), key=abs)) < abs(pooled)
    print("  controlling for the confounder removes the association = %s (pooled +%.0f -> within ~0)" % (control_removes_association, pooled))

    not_causal = within_all_zero
    print("  x does not causally affect y (no within-group effect) = %s" % not_causal)
```

Three clarifications keep the method sound. First, controlling reveals confounding only for confounders you actually measure and condition on — an unmeasured common cause leaves a spurious correlation that no amount of stratifying your data can remove, which is the fundamental limit of observational causal inference and why you must reason about what confounders might exist, not just adjust for the ones in your table. Second, this is distinct from two related traps: unlike Simpson's paradox (where controlling reverses the direction of the association) here it merely vanishes, and unlike collider bias (where controlling for a common effect creates a spurious association) here controlling for a common cause removes one — you condition on confounders (common causes) and must not condition on colliders (common effects), so knowing which variable is which matters. Third, the gold-standard way to defeat confounding is not to measure and adjust but to randomize: assigning x at random breaks every confounder's link to x at once (measured or not), so a surviving x–y association cannot be a confounder's shadow — which is the whole reason randomized experiments outrank observational studies for causal claims. Where randomization is impossible, the honest observational analyst controls for every plausible confounder and reports the causal claim as conditional on no unmeasured ones remaining.

<svg role="img" aria-label="Two diagrams: a confounder with arrows out to X and Y (control it), and a collider with arrows in from X and Y (do not control it)" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8" fill="var(--s1)">confounder (common cause) — control it</text>
  <text x="60" y="40" font-size="8" fill="var(--ink)">C</text>
  <text x="20" y="72" font-size="8" fill="var(--ink)">X</text><text x="100" y="72" font-size="8" fill="var(--ink)">Y</text>
  <line x1="60" y1="44" x2="28" y2="66" stroke="var(--ink)" stroke-width="1"/>
  <line x1="66" y1="44" x2="98" y2="66" stroke="var(--ink)" stroke-width="1"/>
  <text x="30" y="92" font-size="7" fill="var(--muted)">arrows OUT → condition</text>
  <text x="185" y="16" font-size="8" fill="var(--s2)">collider (common effect) — do NOT control it</text>
  <text x="235" y="72" font-size="8" fill="var(--ink)">C</text>
  <text x="195" y="40" font-size="8" fill="var(--ink)">X</text><text x="275" y="40" font-size="8" fill="var(--ink)">Y</text>
  <line x1="203" y1="44" x2="233" y2="66" stroke="var(--ink)" stroke-width="1"/>
  <line x1="277" y1="44" x2="241" y2="66" stroke="var(--ink)" stroke-width="1"/>
  <text x="195" y="92" font-size="7" fill="var(--muted)">arrows IN → conditioning creates bias</text>
</svg>
^ A confounder's arrows point out to X and Y — conditioning on it removes the spurious link. A collider's arrows point in from X and Y — conditioning on it creates one. Same word "control", opposite effect, so which variable you adjust for depends on the causal direction.

**Done means controlling for the confounder removes the association and licenses "not causal" — the vanishing-within-groups signature of confounding, defeated definitively only by randomization, and distinct from a colliders-and-reversals family it must not be confused with.**

## Boss fight

An analyst reports that employees who attended an optional leadership training were promoted at three times the rate of those who did not, and recommends making the training mandatory to boost promotions company-wide. Before spending the budget, what confounding concern would you raise, and how would you check whether the training actually causes promotions?

The obvious confounder is that the training was optional, so the employees who attended chose to — and the kind of employee who signs up for optional leadership training (ambitious, already high-performing, well-connected, favored by their manager) is exactly the kind of employee who gets promoted anyway, training or not. Ambition/ability is a common cause driving both attendance and promotion, so the 3× promotion rate could be entirely that confounder's shadow, with the training contributing nothing causal; making it mandatory would then boost promotions by zero while costing the budget. To check observationally, control for the plausible confounders: compare promotion rates of attendees and non-attendees within groups matched on the pre-training signals of ambition and ability — prior performance ratings, tenure, past promotion velocity, manager. If the attendee advantage shrinks toward zero once you hold those fixed, the correlation was confounded (selection into the training), and the training does not cause promotions; if a promotion advantage survives controlling for every plausible confounder, the training is a candidate cause worth more investigation. But the definitive test is to randomize: assign the training to a random subset of employees (or randomly encourage attendance) and compare promotion rates — randomization breaks the link between attendance and the ambition/ability confounder, measured or not, so a promotion difference in the randomized trial is a real causal effect. The recommendation to spend the budget should wait on either a control-for-confounders analysis that survives, or ideally a randomized pilot, because the reported 3× is exactly the pattern self-selection produces without any causal effect.

## External resources

Judea Pearl and Dana Mackenzie, *The Book of Why*, and Pearl's work on causal diagrams — the modern framework distinguishing confounders (common causes, which you control for) from colliders (common effects, which you must not), and why the ice-cream-and-drownings confound is the canonical example.

Any introductory epidemiology or causal-inference text (e.g. Hernán and Robins, *Causal Inference: What If*) on confounding, adjustment, and why randomization defeats unmeasured confounding — the rigorous treatment of the control-for-common-causes procedure and its fundamental observational limit.
