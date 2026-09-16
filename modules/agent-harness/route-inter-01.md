---
id: route-inter-01
title: Route easy steps to a cheap model and hard steps to a strong one — or you overpay for quality you didn't need everywhere
topic: agent-harness
level: intermediate
status: ready
time: 16 min
summary: Most steps an agent takes are easy — a lookup, a format, an obvious tool call — and a few are hard. Run everything on the strong, expensive model and it handles both, but you pay the strong price on every trivial step, and most steps are trivial, so the bill is dominated by quality you did not need. Run everything on the cheap model and the bill collapses, but the cheap model fails the hard steps and a handful of botched hard steps can wreck a run. Routing pays for quality only where it matters: classify each step's difficulty, send easy steps to the cheap model (nearly as good there anyway) and escalate only the hard ones to the strong model. Because easy steps dominate, the cheap model does most of the calls at a fraction of the price while the strong model is reserved for the minority that need it. On a fixture of 80 easy and 20 hard steps where cheap costs 1 and strong costs 10, always-strong scores 0.964 for a cost of 1000, always-cheap costs 100 but scores only 0.84, and routing costs 280 while scoring 0.94 — within about two points of strong at 28% of its cost.
eli5: If you're doing a hundred chores and only a few are tricky, you don't hire the expensive expert for every single one — you do the easy ones yourself and call the expert only for the hard few. You finish almost as well as if the expert did everything, for a small fraction of the cost. Doing every chore yourself would be cheap but you'd botch the tricky ones; hiring the expert for all of them would nail everything but cost a fortune on chores anyone could do.
---

## Why this module

An agent's steps are not equally hard, but a single-model policy treats them as if they were — paying the top model's price on every trivial step, or accepting the cheap model's failures on the few that are genuinely hard.

Watch what an agent actually does across a run and the steps sort into two piles of very unequal size. The large pile is easy: read a field, reformat a value, call a tool whose arguments are obvious from the context, summarize a short passage. The small pile is hard: choose a plan under ambiguity, write a subtle piece of code, make a judgment where the right answer is not obvious. A strong model handles both piles well, but it charges the same premium rate for the trivial step as for the hard one, and since the trivial pile is much bigger, most of your bill buys capability the easy steps never needed. Flip to the cheap model and the bill drops by an order of magnitude, but the cheap model that breezes through easy steps stumbles on the hard ones, and in an agent a few wrong hard steps — a bad plan, a broken tool call — can derail everything downstream. One model for everything is either overpriced or underpowered.

**Agent steps vary in difficulty but a single-model policy does not, so always-strong overpays for quality on the easy majority while always-cheap underperforms on the hard minority — the model should match the step, not the run.**

Routing matches the model to the step. Classify each step's difficulty and dispatch accordingly: the easy steps, where the cheap model is nearly as accurate as the strong one, go to the cheap model; only the hard steps escalate to the strong model. The economics work because the piles are unequal — the cheap model absorbs the large easy pile at a fraction of the price, and the strong model is spent only on the small hard pile where its premium actually buys something. The run captures almost all of the strong model's accuracy for a fraction of its cost, because you bought the expensive judgment precisely and only where it mattered. This is the model-cascade pattern — cheap first, expensive on escalation — and this module computes the cost and accuracy of all three policies.

## Concepts

**A single-model policy** runs every step on one model: its cost is the step count times that model's per-call price, and its accuracy is the model's accuracy averaged over the step mix.

```python filename=modules/agent-harness/code/route-inter-01/route.py:46-51 COMPLETE
def single_model(steps, model):
    """Cost and accuracy of running every step on one model."""
    n = total_steps(steps)
    cost = n * model["cost"]
    correct = steps["easy"] * model["acc_easy"] + steps["hard"] * model["acc_hard"]
    return cost, correct / n
```

**Routing** dispatches by difficulty: easy steps to the cheap model, hard steps to the strong one. Its cost and accuracy each mix the two models along the step split.

```python filename=modules/agent-harness/code/route-inter-01/route.py:54-59 COMPLETE
def routed(steps, cheap, strong):
    """Cost and accuracy of sending easy steps to `cheap` and hard steps to `strong`."""
    n = total_steps(steps)
    cost = steps["easy"] * cheap["cost"] + steps["hard"] * strong["cost"]
    correct = steps["easy"] * cheap["acc_easy"] + steps["hard"] * strong["acc_hard"]
    return cost, correct / n
```

**The win comes from the unequal mix.** Because easy steps dominate, most calls go to the cheap model, so routing's cost sits near always-cheap while its accuracy sits near always-strong.

<svg role="img" aria-label="A router splits the workload: 80 easy steps go to the cheap model, 20 hard steps to the strong model" viewBox="0 0 300 100" width="300" height="100">
  <rect x="6" y="40" width="70" height="22" fill="none" stroke="var(--line)"/><text x="12" y="54" fill="var(--ink)" font-size="8">100 steps</text>
  <polygon points="76,51 92,45 92,57" fill="var(--line)"/>
  <rect x="96" y="40" width="46" height="22" fill="none" stroke="var(--muted)"/><text x="100" y="54" fill="var(--ink)" font-size="8">router</text>
  <line x1="142" y1="46" x2="180" y2="26" stroke="var(--s1)"/><line x1="142" y1="56" x2="180" y2="76" stroke="var(--s2)"/>
  <rect x="182" y="16" width="110" height="22" fill="var(--s1)"/><text x="188" y="30" fill="var(--panel)" font-size="8">80 easy → cheap (×1)</text>
  <rect x="182" y="66" width="110" height="22" fill="var(--s2)"/><text x="188" y="80" fill="var(--panel)" font-size="8">20 hard → strong (×10)</text>
  <text x="6" y="96" fill="var(--muted)" font-size="8">the cheap model takes the easy majority; the strong model is reserved for the hard minority</text>
</svg>
^ The router sends the 80 easy steps to the cheap model and the 20 hard steps to the strong one, so most calls run at the cheap price and the strong model is spent only where it is needed.

**Route each step to the cheapest model that handles it well: the cheap model on the easy majority, the strong model on the hard minority, so cost tracks the cheap model and accuracy tracks the strong one.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/route-inter-01/route.py

The fixture is 80 easy and 20 hard steps, a cheap model (cost 1, weak on hard) and a strong one (cost 10, strong on both).

```json filename=modules/agent-harness/code/route-inter-01/route.json:3-5 COMPLETE
  "steps": {"easy": 80, "hard": 20},
  "cheap": {"acc_easy": 0.95, "acc_hard": 0.40, "cost": 1},
  "strong": {"acc_easy": 0.98, "acc_hard": 0.90, "cost": 10}
```

Run `--route` to price and score each policy.

```text filename=--route
ROUTE — cost and accuracy of each model policy (80 easy, 20 hard)
----------------------------------------------------------
  policy          cost    accuracy
  always-cheap    100     0.840
  always-strong   1000    0.964
  routed          280     0.940
```

Three policies, three points on the cost-accuracy plane. Always-cheap costs 100 — the floor — but scores only 0.840, because it fails 60% of the hard steps (0.40 accuracy on the 20 hard steps drags the average down). Always-strong scores 0.964, the ceiling, but costs 1000, since it pays the strong model's price of 10 on all 100 steps including the 80 easy ones where the cheap model would have done nearly as well. Routing costs 280 and scores 0.940. That 280 is 80 easy steps at cost 1 plus 20 hard steps at cost 10 — the cheap model carried 80% of the calls. And the 0.940 is the cheap model's 0.95 on the easy steps plus the strong model's 0.90 on the hard ones: it kept the strong model's accuracy exactly where accuracy was at risk. Routing landed near the accuracy ceiling at a cost far closer to the floor, which is the whole point of matching the model to the step.

<svg role="img" aria-label="On a cost-accuracy plot, always-cheap is low cost low accuracy, always-strong is high cost high accuracy, and routed sits near strong's accuracy at low cost" viewBox="0 0 300 104" width="300" height="104">
  <line x1="30" y1="88" x2="290" y2="88" stroke="var(--grid)"/><line x1="30" y1="14" x2="30" y2="88" stroke="var(--grid)"/>
  <text x="2" y="20" fill="var(--muted)" font-size="7">accuracy</text><text x="250" y="102" fill="var(--muted)" font-size="7">cost →</text>
  <circle cx="52" cy="70" r="4" fill="var(--s2)"/><text x="40" y="64" fill="var(--muted)" font-size="7">cheap (100, .84)</text>
  <circle cx="278" cy="24" r="4" fill="var(--s2)"/><text x="210" y="20" fill="var(--muted)" font-size="7">strong (1000, .964)</text>
  <circle cx="98" cy="30" r="4.5" fill="var(--s1)"/><text x="106" y="30" fill="var(--s1)" font-size="7">routed (280, .94)</text>
  <line x1="98" y1="30" x2="278" y2="24" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <text x="30" y="100" fill="var(--muted)" font-size="8">routed sits high (near strong's accuracy) and left (near cheap's cost)</text>
</svg>
^ Always-cheap is cheap and inaccurate, always-strong is accurate and expensive, and routed sits high on accuracy but far left on cost — close to the strong model's quality at a small fraction of its price.

## Build

How good is the trade, exactly? Run `--savings`.

```text filename=--savings
SAVINGS — routing vs the two one-model policies
------------------------------------------------------------
  vs always-strong:  cost 1000 -> 280  (72% cheaper), accuracy 0.964 -> 0.940
  vs always-cheap:   cost 100 -> 280  (2x),           accuracy 0.840 -> 0.940
------------------------------------------------------------
  routing buys most of strong's accuracy for a fraction of its cost, by spending only where it helps.
```

Against always-strong, routing is 72% cheaper and gives up 0.024 of accuracy — a rounding error against a nearly-fourfold cost cut. Against always-cheap, routing costs about 3× more but buys 0.10 of accuracy, turning a run that fails one hard step in six into one that mostly succeeds. Which comparison matters depends on where your pain is: if the bill is the problem, routing recovers most of the cheap policy's savings while fixing its accuracy; if quality is the problem, routing recovers most of the strong policy's accuracy while slashing its cost. The lever behind all of it is the step mix — the more the workload skews toward easy steps, the closer routing's cost gets to the cheap floor while its accuracy stays near the strong ceiling, because the expensive model is invoked on an ever-smaller slice. Routing is not a compromise between the two policies; it is a strictly better point on the plane for any workload where cheap-is-good-enough steps dominate and the two models genuinely differ on the hard ones.

<svg role="img" aria-label="Routing cuts cost from 1000 to 280 versus always-strong while accuracy falls only from 0.964 to 0.940" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">routing vs always-strong</text>
  <text x="6" y="32" fill="var(--muted)" font-size="8">cost</text>
  <rect x="50" y="24" width="230" height="12" fill="var(--s2)"/><text x="222" y="34" fill="var(--panel)" font-size="7">strong 1000</text>
  <rect x="50" y="38" width="64" height="12" fill="var(--s1)"/><text x="118" y="48" fill="var(--muted)" font-size="7">routed 280 (−72%)</text>
  <text x="6" y="70" fill="var(--muted)" font-size="8">accuracy</text>
  <rect x="50" y="62" width="222" height="12" fill="var(--s2)"/><text x="200" y="72" fill="var(--panel)" font-size="7">strong .964</text>
  <rect x="50" y="76" width="216" height="12" fill="var(--s1)"/><text x="196" y="86" fill="var(--panel)" font-size="7">routed .940</text>
  <text x="6" y="95" fill="var(--muted)" font-size="7">a 72% cost cut for a 0.024 accuracy dip — the bars barely differ on accuracy</text>
</svg>
^ Routing cuts cost from 1000 to 280 (−72%) against always-strong while accuracy drops only from 0.964 to 0.940 — a large cost saving for a negligible accuracy loss.

## Definition of done

The self-test pins the three-way comparison: always-cheap underperforms, always-strong overpays, routing stays near strong's accuracy at far less cost and beats cheap's accuracy.

```python filename=modules/agent-harness/code/route-inter-01/route.py:100-113 COMPLETE
    cheap_underperforms = ca < ra - 0.05
    print("  always-cheap is far less accurate (it fails hard steps) = %s (%.3f vs routed %.3f)" % (cheap_underperforms, ca, ra))

    strong_overpays = sc > rc
    print("  always-strong costs more than routing = %s (%d > %d)" % (strong_overpays, sc, rc))

    routed_near_strong = sa - ra < 0.05
    print("  routing stays within a few points of strong's accuracy = %s (%.3f vs %.3f)" % (routed_near_strong, ra, sa))

    routed_much_cheaper = rc < sc / 2
    print("  routing costs far less than always-strong = %s (%d < %d)" % (routed_much_cheaper, rc, sc))

    routed_beats_cheap_accuracy = ra > ca
    print("  routing is more accurate than always-cheap = %s (%.3f > %.3f)" % (routed_beats_cheap_accuracy, ra, ca))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — always-cheap fails hard steps; always-strong overpays; routing nears strong's accuracy at a fraction of the cost
--------------------------------------------------------------------------------------------------------------------------
  always-cheap is far less accurate (it fails hard steps) = True (0.840 vs routed 0.940)
  always-strong costs more than routing = True (1000 > 280)
  routing stays within a few points of strong's accuracy = True (0.940 vs 0.964)
  routing costs far less than always-strong = True (280 < 1000)
  routing is more accurate than always-cheap = True (0.940 > 0.840)
```

**Done means the cascade is proven a better point than either one-model policy: always-cheap costs 100 but scores only 0.840 (failing hard steps), always-strong scores 0.964 but costs 1000, and routing scores 0.940 — within 0.024 of strong — for a cost of 280, a 72% saving over always-strong while beating always-cheap's accuracy by 0.10.**

## Boss fight

Predict the two costs the tidy numbers hide — the classifier that decides difficulty, and the escalation that never happens. It is tempting to assume a free, perfect difficulty router.

The first trap is that routing needs a difficulty classifier, and that classifier is neither free nor perfect. Something has to decide, before the step runs, whether it is easy or hard — and that decision costs a call (often to a small model) and adds latency to every step, eating into the savings. Worse, it makes mistakes in both directions, and the two mistakes are not symmetric. Routing a truly-hard step to the cheap model (a missed escalation) is the expensive error: the cheap model fails it, and in an agent that failure propagates. Routing a truly-easy step to the strong model (an over-escalation) only wastes a little money. So the classifier should be tuned to escalate when unsure — a false "hard" costs cents, a false "easy" costs a derailed run — and its accuracy, its cost, and its latency all have to be counted in the real comparison, which this fixture's perfect, free router omits. The cascade wins only if the router is cheap and biased toward caution.

```python filename=modules/agent-harness/code/route-inter-01/route.py:42-43 COMPLETE
def total_steps(steps):
    return steps["easy"] + steps["hard"]
```

The second trap is that difficulty is often not knowable in advance, which is why real cascades escalate on *evidence*, not on prediction. For many steps you cannot tell they are hard until the cheap model has tried and produced a low-confidence, self-contradictory, or verification-failing answer. The stronger pattern is therefore to run the cheap model first and escalate to the strong model only when the cheap result fails a check — a validator, a confidence threshold, a second-opinion disagreement — so the strong model is invoked precisely on the steps the cheap model actually flubbed, not on a guess about which those will be. That costs an extra cheap call on escalated steps (you pay cheap, then strong) but removes the need for a separate upfront classifier and routes on ground truth instead of prediction. The trade between predict-then-route and try-then-escalate depends on how reliably difficulty can be judged in advance and how expensive a wasted cheap attempt is. Either way, the accuracy and cost that matter are the end-to-end ones — including the router or the retried attempts — not the idealized per-step table.

**Route agent steps to the cheapest capable model — cheap on the easy majority, strong on the hard minority — to capture near-strong accuracy at a fraction of the cost, but count the difficulty router's own cost, latency, and errors (biasing it to escalate, since a missed hard step is far costlier than an over-escalation), and prefer escalating on evidence — run cheap first, escalate when a check fails — when difficulty cannot be reliably predicted in advance, because the real win is the end-to-end cost and accuracy, not the idealized per-step numbers.**

## External resources

Writing on LLM model cascades and routing (for example FrugalGPT and router/cascade systems) — the strategies for predicting difficulty, escalating on confidence, and the measured cost-accuracy trade-offs on real workloads.

Any reference on the economics of mixed-capability inference — how the cost saving scales with the fraction of easy steps and the price ratio between models, and how classifier error shifts the break-even point.

The companion "cap the run's token budget, not just its step count" and "prune the tool menu" modules — token budgeting caps total spend where routing lowers per-step spend, and both are part of running an agent economically rather than at maximum capability on every call.
