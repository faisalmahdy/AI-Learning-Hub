---
id: pareto-inter-01
title: Choose a model on the quality-cost Pareto frontier, not by quality alone — quality-only ranking overpays and even prefers a dominated model
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: Picking a model is a two-objective decision — high quality, low cost — and the two trade off, but ranking by quality alone collapses it to one axis and makes two errors. First it overpays at the top: it always names the highest-quality model regardless of what that quality costs, and because quality has diminishing returns, the top model is often a small gain over the next at a large multiple of the cost — the worst value on the board. Second, and strictly irrational, a quality-only ranking can place a dominated model above an efficient one: a model is dominated when another is at least as good on quality and at least as cheap (strictly better on one axis), so choosing it is never rational, yet if it has higher quality than some cheaper efficient model, quality-ranking lists it higher. The Pareto frontier is the set of non-dominated models — those no other model beats on both axes — and every rational choice lies on it, with the point picked by how much quality per unit cost you are willing to buy. On a fixture of five models, D (quality 80, cost 12) is dominated by C (quality 88, cost 10) and should never be chosen, yet it outranks the efficient A on quality; and the top-quality model E costs 30 more than C for just 2 more quality points — 15 cost per quality point, far above its own average of 0.44. The frontier is A, B, C, E; the quality-only ranking is E, C, B, D, A, wrong at both the top and the dominated D.
eli5: Imagine choosing a bike, and you care about two things: how fast it is and how cheap it is. If you rank only by speed, you always pick the fastest bike no matter the price — even if it is only a hair faster than the next one but costs a fortune. Worse, ranking by speed can put a bike above another that is both slower AND more expensive than a third bike — a bike nobody should ever buy, listed ahead of a good cheap one, just because it happens to be a little fast. The smart way is to first cross off every bike that some other bike beats on both speed and price, then choose among the ones left over based on how much you are willing to pay for extra speed. Looking at only one number hides the deals and the duds.
---

## Why this module

Every model selection is really a choice on two axes: how good the model is, and what it costs to run — money, latency, tokens, whatever the scarce resource is. A leaderboard, though, is one column, sorted by a quality score, and the reflex is to read the winner off the top. That reflex quietly assumes cost does not matter, and it almost always does.

Collapsing two axes to one throws away exactly the information you need to make the tradeoff, and it fails in two separable ways. The first is overpaying: the top of a quality sort is whatever model scores highest, no matter how much its last increment of quality cost. Quality tends to saturate — the gap between the best and second-best is often tiny — so the quality-only winner is frequently a marginal gain at a large multiple of the price, which is to say the worst value on the list, chosen precisely because the ranking cannot see price.

The second failure is worse because it is not even a defensible tradeoff — it is choosing an option no rational actor should. When one model is both better and cheaper than another, the second model is dominated and never worth choosing. But a dominated model can still outscore some cheaper, efficient model on quality alone, and then the quality sort lists the dominated model above the efficient one. The ranking is not just miscalibrated on cost; it actively recommends a dud over a deal.

**Ranking models by quality alone drops the cost axis, so it crowns the costliest model for a marginal quality gain and can list a dominated model — one beaten on both quality and cost — above an efficient one.**

## Concepts

Put the models on a plane: cost on one axis, quality on the other. Now "better" has a direction — up and to the left, higher quality at lower cost — and the comparison between two models is about that direction. One model dominates another when it is at least as good on both axes and strictly better on one: it sits up-and-left of the other, winning outright. A model that some other model dominates is a dud; there is a strictly better option at no extra cost.

<svg role="img" aria-label="A scatter plot with cost on the horizontal axis and quality on the vertical. Models A, B, C, E lie along the upper-left boundary (the Pareto frontier), connected by a line. Model D sits below and right of C, inside the region C dominates, marked dominated." viewBox="0 0 440 160">
<line x1="45" y1="130" x2="415" y2="130" stroke="var(--line)"/>
<line x1="45" y1="20" x2="45" y2="130" stroke="var(--line)"/>
<text x="230" y="150" fill="var(--muted)" font-size="9" text-anchor="middle">cost (lower better) -&gt;</text>
<text x="18" y="75" fill="var(--muted)" font-size="9" text-anchor="middle" transform="rotate(-90 18 75)">quality -&gt;</text>
<path d="M55 120 L 80 60 L 150 45 L 400 30" fill="none" stroke="var(--s1)" stroke-dasharray="4 3"/>
<circle cx="55" cy="120" r="4" fill="var(--s1)"/><text x="55" y="112" fill="var(--s1)" font-size="8" text-anchor="middle">A</text>
<circle cx="80" cy="60" r="4" fill="var(--s1)"/><text x="80" y="52" fill="var(--s1)" font-size="8" text-anchor="middle">B</text>
<circle cx="150" cy="45" r="4" fill="var(--s1)"/><text x="150" y="37" fill="var(--s1)" font-size="8" text-anchor="middle">C</text>
<circle cx="400" cy="30" r="4" fill="var(--s1)"/><text x="400" y="22" fill="var(--s1)" font-size="8" text-anchor="middle">E</text>
<circle cx="175" cy="78" r="4" fill="var(--s2)"/><text x="192" y="82" fill="var(--s2)" font-size="8">D (dominated by C)</text>
<text x="230" y="110" fill="var(--muted)" font-size="8" text-anchor="middle">frontier: A, B, C, E</text>
</svg>
^ On the cost-quality plane the non-dominated models (A, B, C, E) form the upper-left frontier; D sits below-and-right of C, inside the region C dominates, so it is never the right choice.

The set of non-dominated models is the Pareto frontier: the models for which no other model is better on both axes. It is the whole menu of rational choices, because anything off the frontier is beaten outright by something on it. Selecting a model is choosing a point on the frontier, and where you land depends on your exchange rate — how much cost you are willing to pay for a unit of quality. There is no single "best"; there is a best-for-your-budget.

The quality-only ranking gets both the menu and the winner wrong. It includes dominated models (they have quality scores, so they sort somewhere), and it always tops out at the highest quality regardless of cost. Reading the top off a quality sort therefore answers a question nobody asked — "which is most capable at any price?" — while hiding the frontier, which is the answer to the question you actually have: "which is the best use of my budget?"

<svg role="img" aria-label="A comparison of two orderings. The quality-only ranking lists E, C, B, D, A top to bottom, with D (dominated) highlighted as ranked above A (efficient). The Pareto frontier lists A, B, C, E and excludes D entirely." viewBox="0 0 440 150">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">quality-only ranking</text>
<rect x="70" y="24" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="110" y="36" fill="var(--ink)" font-size="8" text-anchor="middle">E (costliest)</text>
<rect x="70" y="42" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="110" y="54" fill="var(--ink)" font-size="8" text-anchor="middle">C</text>
<rect x="70" y="60" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="110" y="72" fill="var(--ink)" font-size="8" text-anchor="middle">B</text>
<rect x="70" y="78" width="80" height="16" fill="var(--panel)" stroke="var(--s2)"/><text x="110" y="90" fill="var(--s2)" font-size="8" text-anchor="middle">D (dominated)</text>
<rect x="70" y="96" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="110" y="108" fill="var(--ink)" font-size="8" text-anchor="middle">A (efficient)</text>
<text x="110" y="126" fill="var(--s2)" font-size="7" text-anchor="middle">D ranked above A -- wrong</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">Pareto frontier</text>
<rect x="290" y="24" width="80" height="16" fill="var(--s1)"/><text x="330" y="36" fill="var(--ink)" font-size="8" text-anchor="middle">A</text>
<rect x="290" y="42" width="80" height="16" fill="var(--s1)"/><text x="330" y="54" fill="var(--ink)" font-size="8" text-anchor="middle">B</text>
<rect x="290" y="60" width="80" height="16" fill="var(--s1)"/><text x="330" y="72" fill="var(--ink)" font-size="8" text-anchor="middle">C</text>
<rect x="290" y="78" width="80" height="16" fill="var(--s1)"/><text x="330" y="90" fill="var(--ink)" font-size="8" text-anchor="middle">E</text>
<text x="330" y="110" fill="var(--s1)" font-size="7" text-anchor="middle">D excluded</text>
</svg>
^ The quality sort includes the dominated D and ranks it above the efficient A; the frontier drops D and presents only the rational choices.

**A model dominates another when it is at least as good on both axes and strictly better on one; the Pareto frontier is the non-dominated set — the whole menu of rational choices — and selection is picking a point on it by your quality-per-cost exchange rate, not reading the top off a quality sort.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/pareto-inter-01. The fixture is five models, each with a quality score and a cost.

```json filename=modules/evals-and-statistics/code/pareto-inter-01/pareto.json:3-9 COMPLETE
  "models": {
    "A": {"quality": 70, "cost": 1},
    "B": {"quality": 85, "cost": 3},
    "C": {"quality": 88, "cost": 10},
    "D": {"quality": 80, "cost": 12},
    "E": {"quality": 90, "cost": 40}
  }
```

Dominance is the whole idea in one predicate.

```python filename=modules/evals-and-statistics/code/pareto-inter-01/pareto.py:32-36 COMPLETE
def dominates(a, b):
    """a dominates b if a is at least as good on both axes and strictly better on one (higher quality, lower cost)."""
    at_least_as_good = a["quality"] >= b["quality"] and a["cost"] <= b["cost"]
    strictly_better = a["quality"] > b["quality"] or a["cost"] < b["cost"]
    return at_least_as_good and strictly_better
```

The dominated set and the frontier fall straight out of it.

```python filename=modules/evals-and-statistics/code/pareto-inter-01/pareto.py:39-47 COMPLETE
def dominated_set(models):
    """Models for which some other model dominates them -- never rational to choose."""
    return [n for n, m in models.items() if any(dominates(o, m) for k, o in models.items() if k != n)]


def frontier(models):
    """The Pareto frontier: the non-dominated models, ordered by cost."""
    dom = set(dominated_set(models))
    return sorted((n for n in models if n not in dom), key=lambda n: models[n]["cost"])
```

The quality-only ranking is the cost-blind ordering to compare against.

```python filename=modules/evals-and-statistics/code/pareto-inter-01/pareto.py:50-52 COMPLETE
def quality_ranking(models):
    """Models ranked by quality alone, best first -- the cost-blind ordering."""
    return sorted(models, key=lambda n: models[n]["quality"], reverse=True)
```

Before running it, predict: D at quality 80, cost 12 is beaten by C at quality 88, cost 10 on both axes, so D is dominated — yet D outscores A on quality, so a quality sort will rank D above A. Run `--models`:

```text filename=pareto.py --models
MODELS — quality (higher better), cost (lower better), value (quality/cost)
--------------------------------------------------------
  model   quality   cost   value    dominated?
  A       70        1      70.00    False
  B       85        3      28.33    False
  C       88        10     8.80     False
  D       80        12     6.67     True
  E       90        40     2.25     False
--------------------------------------------------------
  a dominated model is beaten on both axes -- it should never be chosen
```

The prediction holds. D is the one dominated model — C has higher quality (88 vs 80) and lower cost (10 vs 12), so C beats D outright. The value column (quality per unit cost) also exposes the overpay problem from the other side: A returns 70 quality-points per cost unit, E only 2.25 — the highest-quality model is the lowest value by a factor of 30. Every number a quality-only sort ignores is right here.

Now the two orderings side by side. Run `--frontier`:

```text filename=pareto.py --frontier
FRONTIER — the Pareto frontier vs the quality-only ranking
--------------------------------------------------------
  Pareto frontier (by cost): ['A', 'B', 'C', 'E']
  quality-only ranking     : ['E', 'C', 'B', 'D', 'A']
  dominated, excluded      : ['D']
  top-quality model E costs +30 for +2 quality over C -> 15.0 cost per quality point
--------------------------------------------------------
  quality-only picks the costliest and lists the dominated model above an efficient one
```

Both failures are visible. The quality ranking crowns E, the costliest model, for its 2-point edge over C that costs 30 extra units — 15 cost per quality point, when C's own average is about 0.11 and A's is under 0.02; the last two points of quality are the most expensive on the board by far. And the quality ranking lists D fourth, above A in fifth — placing the dominated dud above the efficient frontier model, exactly the irrational ordering. The frontier, by contrast, is A, B, C, E: D is gone, and what remains is the real menu, ordered by cost so you can pick your exchange rate.

<svg role="img" aria-label="A bar chart of cost per quality point. C's average is about 0.11, A's about 0.01, and the marginal cost of E over C is 15.0, towering over them, showing the top model's last quality points are far more expensive." viewBox="0 0 440 140">
<line x1="60" y1="115" x2="410" y2="115" stroke="var(--line)"/>
<text x="20" y="30" fill="var(--muted)" font-size="8">cost per</text>
<text x="20" y="42" fill="var(--muted)" font-size="8">quality pt</text>
<rect x="90" y="112" width="40" height="3" fill="var(--s1)"/><text x="110" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">A ~0.01</text>
<rect x="180" y="110" width="40" height="5" fill="var(--s1)"/><text x="200" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">C ~0.11</text>
<rect x="300" y="30" width="40" height="85" fill="var(--s2)"/><text x="320" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">E marginal 15.0</text>
<text x="320" y="24" fill="var(--s2)" font-size="8" text-anchor="middle">the top's last points</text>
</svg>
^ The marginal cost of E's quality over C (15 per point) dwarfs any model's average cost per quality point — the diminishing return a quality-only sort pays without seeing.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that a dominated model exists, that the Pareto frontier excludes every dominated model, that quality-only ranking crowns the costliest model, that it lists a dominated model above an efficient one, and that the top model's marginal cost per quality point exceeds its own average.

```python filename=modules/evals-and-statistics/code/pareto-inter-01/pareto.py:104-124 COMPLETE
    dominated_exists = len(dom) > 0
    print("  at least one model is dominated = %s (%s)" % (dominated_exists, dom))

    frontier_excludes_dominated = all(n not in f for n in dom)
    print("  the Pareto frontier excludes every dominated model = %s (frontier %s)" % (frontier_excludes_dominated, f))

    top = qr[0]
    quality_only_picks_costliest = top == max(models, key=lambda n: models[n]["cost"])
    print("  quality-only ranking crowns the costliest model = %s (%s)" % (quality_only_picks_costliest, top))

    # a dominated model ranks above a frontier model in the quality-only order
    quality_rank_prefers_dominated = any(
        qr.index(d) < qr.index(fr) for d in dom for fr in f if models[d]["quality"] > models[fr]["quality"]
    )
    print("  quality-only ranking lists a dominated model above an efficient one = %s" % quality_rank_prefers_dominated)

    below = [n for n in f if models[n]["quality"] < models[top]["quality"]]
    ref = max(below, key=lambda n: models[n]["quality"])
    marginal = (models[top]["cost"] - models[ref]["cost"]) / (models[top]["quality"] - models[ref]["quality"])
    top_avg = models[top]["cost"] / models[top]["quality"]  # top's average cost per quality point
    top_is_poor_value = marginal > top_avg
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the frontier ever admitted a dominated model or the quality sort ever stopped preferring the dud:

```text filename=pareto.py --check
SELF-TEST — a dominated model exists and outranks an efficient one under quality-only ranking; the frontier excludes it and the top model is poor value
----------------------------------------------------------------------------------------------------------------
  at least one model is dominated = True (['D'])
  the Pareto frontier excludes every dominated model = True (frontier ['A', 'B', 'C', 'E'])
  quality-only ranking crowns the costliest model = True (E)
  quality-only ranking lists a dominated model above an efficient one = True
  the top model's marginal cost per quality point exceeds its own average = True (15.0 > 0.44)
```

**The self-test checks the strictly-irrational failure specifically — that quality-only ranking lists a dominated model above an efficient one — so a pass certifies more than "it ignores cost"; it certifies the ranking recommends a choice that is wrong on both axes at once.**

## Definition of done

You can explain why model selection is a two-objective problem and what ranking by quality alone discards.
You can define dominance and the Pareto frontier, and say why every rational choice lies on the frontier.
You can explain the two failures of quality-only ranking: overpaying at the top and preferring a dominated model.
You can explain why there is no single "best" model, only a best-for-a-given-exchange-rate on the frontier.
You can compute a model's marginal cost per quality point and use it to spot diminishing returns at the top.

## Boss fight

Suppose your quality scores and costs each have error bars — quality is estimated from a finite eval, cost varies with the request mix. Reason about what that does to dominance. Dominance computed from point estimates can be an illusion: if C's quality is 88 ± 3 and D's is 80 ± 3, C probably dominates D, but if the intervals were 88 ± 10 and 80 ± 10 you could not be sure C is even better on quality, so calling D dominated would be over-confident. The rigorous version is probabilistic or interval dominance — A dominates B only if it does so accounting for the uncertainty — and near the frontier, where models are close, the error bars often overlap and the frontier becomes a fuzzy band rather than a sharp line. The lesson connects to the rest of the topic: the same measurement noise that makes a single eval run untrustworthy makes a razor-thin dominance claim untrustworthy, so a frontier should be drawn with the intervals, and a "dominated" verdict that rests on a difference smaller than the noise is not real.

Now the trap that makes the whole frontier the wrong tool: the axes have to be the ones that matter, measured how you will actually use them. Cost is not one number — a model can be cheap per token but verbose, cheap at low volume but rate-limited at scale, cheap to call but expensive in latency for an interactive product — so a frontier drawn on the wrong cost axis optimizes the wrong thing. And quality is rarely scalar either; a model that wins on average quality can lose on the one capability your product depends on, which a guardrail module addresses by gating on secondary metrics. The Pareto method is only as good as the axes: choose cost and quality measures that reflect the real deployment (cost at your volume and latency profile, quality on your task distribution), and treat the frontier as a decision aid over those, not a universal ranking. Dominance on the wrong axes is confident nonsense.

**Dominance from point estimates can be an artifact of measurement noise, so draw the frontier with error bars and distrust a razor-thin dominance claim; and the frontier is only as valid as its axes — cost and quality must be measured as you will actually deploy, or you optimize a frontier for the wrong problem.**

## External resources

Any multi-objective optimization or decision-analysis reference defines Pareto dominance, the Pareto frontier, and why non-dominated sets are the rational choice set.
Model and API comparison studies increasingly plot quality against cost or latency and report the frontier (for example, cost-vs-accuracy and latency-vs-quality plots), rather than a single quality leaderboard.
The topic's own module on gating a ship decision on guardrail metrics covers the neighboring multi-objective idea — refusing a model that regresses a secondary metric — which complements choosing among acceptable models on the frontier.
