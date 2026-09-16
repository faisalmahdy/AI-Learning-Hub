---
id: harness-inter-21
title: Cap the run's token budget, not just its step count — a few fat steps overrun the bill under the step limit
topic: agent-harness
level: intermediate
status: ready
time: 17 min
summary: An agent loop's iteration bound stops it after so many steps, but it counts steps, and steps are not equal in cost. Most append a small tool result; a few append a huge one — a whole file, a giant search dump — and cost far more in context tokens and dollars. So a run can stay well under its step limit while its token usage runs away: five steps, two of them fat, can blow a budget the twenty-step limit was nowhere near catching. The fix is a second, independent guard — a cumulative token or cost budget that stops the run when tokens reach the limit, whatever the step count. On a fixture with a 20-step limit and a 15000-token budget, steps costing 500, 500, 8000, 500, 9000, ... reach 18500 tokens after just 5 steps, so the token budget stops the run at step 5 while the iteration bound would have let it run to the end and cost far more; two fat steps carry 17000 of the 19500 total.
eli5: A taxi meter that only counts how many times you get in and out won't tell you the fare — one long ride costs more than ten short hops. If you only limit the number of stops, a couple of long detours can run up a huge bill while you're still well under your stop limit. You have to watch the money on the meter, not just the number of stops. An agent's token budget is the meter; the step limit is the stop counter.
---

## Why this module

Bounding how many times an agent loop turns says nothing about how much each turn costs, and the turns that blow the budget are exactly the few that append an enormous tool result.

The standard guard against a runaway loop is an iteration bound: stop after N steps. It is necessary, but it measures the wrong quantity. It counts steps, and steps are wildly unequal in cost — most append a small tool result and cost a few hundred tokens, but a few append a whole file, a giant search dump, a verbose API response, and cost thousands. Because the bound only counts turns, a run can sit comfortably at five steps, far under a twenty-step limit, while its context has ballooned and its bill has run away. The iteration bound is watching the step counter when the thing you actually care about — tokens spent, dollars spent, context consumed — is on a different meter entirely.

**The iteration bound counts steps, but steps vary enormously in token cost, so a run can stay under the step limit while a few fat tool results blow the token budget.**

The fix is a second, independent guard: a cumulative token (or cost) budget. Track the tokens the run has consumed and stop when they reach the limit, regardless of step count. Now a run that appends fat results trips the token budget early and halts, while a run of many small steps trips the iteration bound — each guard catches the failure the other cannot see. They are not redundant; they measure different quantities, and a robust loop enforces both, alongside the per-call timeout that bounds a single hung call. This module runs a loop under both guards and shows the token budget stop it long before the step bound would.

## Concepts

The **iteration bound** stops the loop after a fixed number of steps. It bounds how many times the loop turns — the right guard for a loop that will not converge, blind to how much each turn costs.

A **step's token cost** is mostly the tool result it appends to the context. It ranges from a few hundred tokens for a status check to many thousands for a file read or a large query result.

The **token (or cost) budget** stops the run when cumulative tokens reach a limit, whatever the step count. It bounds how much the loop costs — the guard the iteration bound cannot provide.

**The two guards measure different quantities.** Step count and token cost are only loosely related, so neither bound implies the other: a run can be under the step limit and over the token budget, or the reverse.

**Fat steps dominate the total.** Because a handful of large results carry most of the cost, the token budget usually trips on one of them — which is exactly the moment the step count is still low and the iteration bound is silent.

```python filename=modules/agent-harness/code/harness-inter-21/budget.py:42-61 COMPLETE
def cumulative(step_tokens):
    """Running total of tokens after each step."""
    total, out = 0, []
    for t in step_tokens:
        total += t
        out.append(total)
    return out


def stop_by_budget(step_tokens, max_tokens):
    """The 1-indexed step at which cumulative tokens first reach the budget, or None if never."""
    for i, c in enumerate(cumulative(step_tokens), start=1):
        if c >= max_tokens:
            return i
    return None


def stop_by_iterations(step_tokens, max_steps):
    """The step at which the iteration bound stops the run (it never sees token cost)."""
    return min(len(step_tokens), max_steps)
```

**A run needs a token budget in addition to a step limit, because the step limit bounds the number of turns while the token budget bounds their total cost, and a few fat tool results overrun the second while staying under the first.**

<svg role="img" aria-label="A step counter reads 5 of 20 while the token meter reads 18500 of 15000; the two meters disagree on whether to stop" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">two meters, two quantities</text>
  <text x="20" y="34" fill="var(--s1)" font-size="8">step counter</text>
  <rect x="20" y="40" width="120" height="14" fill="none" stroke="var(--grid)" stroke-width="1"/><rect x="20" y="40" width="30" height="14" fill="var(--s1)"/><text x="145" y="51" fill="var(--muted)" font-size="8">5 / 20 — fine</text>
  <text x="20" y="76" fill="var(--s2)" font-size="8">token meter</text>
  <rect x="20" y="82" width="120" height="14" fill="none" stroke="var(--grid)" stroke-width="1"/><rect x="20" y="82" width="120" height="14" fill="var(--s2)"/><rect x="140" y="82" width="28" height="14" fill="var(--s2)"/><text x="172" y="93" fill="var(--s2)" font-size="8">18500 / 15000 — over!</text>
  <text x="20" y="108" fill="var(--muted)" font-size="8">the step counter says keep going; the token meter says stop — only the second is right</text>
</svg>
^ At the same instant the step counter reads a comfortable 5 of 20 while the token meter has already overshot 15000 — the guards disagree because they measure different things, and only the token meter sees the overrun.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-21/budget.py

The fixture is a run's per-step token costs, a step limit, and a token budget.

```json filename=modules/agent-harness/code/harness-inter-21/budget.json:1-6 COMPLETE
{
  "_meta": "An agent loop's steps, each with the tokens it adds to the context (mostly the tool result it appends). max_steps is the iteration bound — the loop stops after that many steps. max_tokens is a separate token/cost budget — the loop should stop once cumulative tokens reach it. The point: the iteration bound counts STEPS, but steps are not equal in cost. A few steps that each append a huge tool result can blow the token budget (and the bill) long before the step count runs out, so the iteration bound never fires and the run overruns. step_tokens lists each step's token cost in order; the big results are the ones that dominate.",
  "step_tokens": [500, 500, 8000, 500, 9000, 400, 300, 300],
  "max_steps": 20,
  "max_tokens": 15000
}
```

Run `--run` to watch the tokens accumulate.

```text filename=--run
RUN — cumulative tokens per step (budget 15000, step limit 20)
----------------------------------------------------------
  step   step tokens   cumulative   note
  1         500           500
  2         500          1000
  3        8000          9000
  4         500          9500
  5        9000         18500  <- token budget hit
  6         400         18900
  7         300         19200
  8         300         19500
----------------------------------------------------------
  the budget is crossed at step 5, long before the 20-step iteration bound.
```

Steps 3 and 5 are the fat ones — 8000 and 9000 tokens, a big file read and a large query dump. By the end of step 5 the run has consumed 18500 tokens, past the 15000 budget, while the step count is 5, a quarter of the 20-step limit. The iteration bound sees five harmless-looking steps and does nothing; the token budget sees the meter cross 15000 and stops. If you had only the step bound, the run would sail on to whatever came next, spending tokens the whole way.

<svg role="img" aria-label="Cumulative tokens climb past the 15000 budget at step 5 while the step count is far below the 20-step limit" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">cumulative tokens per step</text>
  <line x1="30" y1="20" x2="30" y2="98" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="98" x2="290" y2="98" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="45" x2="290" y2="45" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 3"/><text x="235" y="43" fill="var(--s2)" font-size="7">budget 15000</text>
  <rect x="40" y="96" width="18" height="2" fill="var(--s1)"/><rect x="62" y="94" width="18" height="4" fill="var(--s1)"/><rect x="84" y="62" width="18" height="36" fill="var(--s1)"/><rect x="106" y="60" width="18" height="38" fill="var(--s1)"/><rect x="128" y="24" width="18" height="74" fill="var(--s2)"/>
  <rect x="150" y="22" width="18" height="76" fill="var(--grid)"/><rect x="172" y="21" width="18" height="77" fill="var(--grid)"/><rect x="194" y="20" width="18" height="78" fill="var(--grid)"/>
  <text x="120" y="16" fill="var(--s2)" font-size="7">step 5 crosses</text>
  <text x="150" y="112" fill="var(--muted)" font-size="7">steps 6–8 (grey) would run under the step bound alone</text>
</svg>
^ The cumulative line jumps past the dashed budget at step 5 on the second fat result; the grey bars beyond are the steps the step bound would still permit, each adding more cost.

## Build

The guards view computes each guard's stop point and what the step bound alone would let through.

```python filename=modules/agent-harness/code/harness-inter-21/budget.py:81-84 COMPLETE
    st, mt, ms = data["step_tokens"], data["max_tokens"], data["max_steps"]
    budget_step = stop_by_budget(st, mt)
    iter_step = stop_by_iterations(st, ms)
    tokens_if_iter_only = sum(st[:iter_step])
```

Which guard fires, and what does the other miss? Run `--guards`.

```text filename=--guards
GUARDS — which guard stops the run first
----------------------------------------------------------
  token budget stops at step 5  (cumulative 18500 >= 15000)
  iteration bound stops at step 8 (of 8 available steps)
  step bound alone would let 19500 tokens through (1.3x the budget)
----------------------------------------------------------
  the token budget fires 3 steps earlier and caps the cost the step bound ignores.
```

The token budget stops the run at step 5 with 18500 tokens consumed. The iteration bound never fires within this run — the loop runs out of steps at 8, still under its limit of 20 — so with only the step bound the run would spend all 19500 tokens, 1.3x the budget you meant to enforce. And 19500 is just this run; a real loop that keeps finding fat results under a generous step limit can spend many multiples of its intended budget before the step count catches up. The two guards fire on different runs: this one needed the token budget, a chatty run of tiny steps would need the iteration bound, and neither alone is enough.

<svg role="img" aria-label="The token budget stops at step 5; the iteration bound would allow the full run of 19500 tokens, 1.3 times the budget" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">tokens allowed through, by guard</text>
  <line x1="70" y1="20" x2="70" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="74" x2="285" y2="74" stroke="var(--grid)" stroke-width="1"/>
  <line x1="235" y1="20" x2="235" y2="74" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 3"/><text x="212" y="18" fill="var(--muted)" font-size="7">budget</text>
  <rect x="70" y="26" width="18" height="16" fill="var(--s1)"/><text x="92" y="38" fill="var(--muted)" font-size="8">token budget: stops at 15000</text>
  <rect x="70" y="50" width="210" height="16" fill="var(--s2)"/><text x="120" y="62" fill="var(--panel)" font-size="8">step bound alone: 19500 (1.3x)</text>
  <text x="70" y="92" fill="var(--muted)" font-size="8">the step bound lets the run overrun the dashed budget line</text>
</svg>
^ The token-budget bar stops at the budget line; the step-bound-only bar runs past it to 19500, the overrun the iteration bound cannot see.

## Definition of done

The self-test pins it: the token budget trips, it stops before the iteration bound, the step bound alone would overrun, the fat steps dominate, and the step count at the stop was well under its limit.

```python filename=modules/agent-harness/code/harness-inter-21/budget.py:101-115 COMPLETE
    budget_trips = budget_step is not None
    print("  the token budget is crossed during the run = %s (at step %d)" % (budget_trips, budget_step))

    budget_before_step_bound = budget_step < iter_step
    print("  the token budget stops the run before the iteration bound = %s (%d < %d)" % (budget_before_step_bound, budget_step, iter_step))

    step_bound_would_overrun = sum(st[:iter_step]) > mt
    print("  the step bound alone would blow the token budget = %s (%d > %d)" % (step_bound_would_overrun, sum(st[:iter_step]), mt))

    fat_steps = [t for t in st if t >= mt / 3]
    fat_steps_dominate = sum(fat_steps) > sum(t for t in st if t < mt / 3)
    print("  a few fat steps dominate the cost = %s (%d in %d fat steps vs %d in the rest)" % (fat_steps_dominate, sum(fat_steps), len(fat_steps), sum(t for t in st if t < mt / 3)))

    step_count_under_limit = budget_step < ms
    print("  at the stop, the step count was well under its limit = %s (%d < %d)" % (step_count_under_limit, budget_step, ms))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the step bound misses the overrun; the token budget stops it early; the fat steps dominate
--------------------------------------------------------------------------------------------------------
  the token budget is crossed during the run = True (at step 5)
  the token budget stops the run before the iteration bound = True (5 < 8)
  the step bound alone would blow the token budget = True (19500 > 15000)
  a few fat steps dominate the cost = True (17000 in 2 fat steps vs 2500 in the rest)
  at the stop, the step count was well under its limit = True (5 < 20)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  budget_trips=True  budget_before_step_bound=True  step_bound_would_overrun=True  fat_steps_dominate=True  step_count_under_limit=True
```

**Done means the gap is proven: the token budget stops the run at step 5 (18500 tokens) while the step count is a quarter of its 20-step limit, and two fat steps carry 17000 of the 19500 total — so the step bound alone would have let 1.3x the budget through.**

## Boss fight

The token budget stopped the overrun. Predict what the loop should do when it trips, and whether one global budget is the right shape. It is tempting to just hard-stop the run the instant the budget is hit.

A budget hit is a signal, not always a kill. Aborting mid-task wastes everything spent so far, so a good loop treats the budget as a soft threshold first: when it approaches, it can compact the context (dropping the fat results it no longer needs), summarize progress, or switch to finishing rather than exploring — and hard-stop only if that fails. The budget's job is to bound cost, and there is usually a cheaper move than throwing the whole run away, exactly as the fat results that blew it are often the ones safe to evict. The hard cap remains as the backstop, but hitting it should first trigger the loop to spend its remaining budget landing the plane, not to crash it.

The other question is shape. A single per-run token budget is the floor, but real systems layer budgets: a per-step cap (no single tool result may exceed so many tokens, so you truncate a giant file instead of ingesting it whole — the head-and-tail rule), a per-run budget (this module), and a per-user or per-day cost budget above that. Each catches overruns the others miss: the per-step cap stops one monster result, the per-run budget stops accumulation, the daily budget stops a runaway fleet of runs. And because the meter that matters is money, the budget should ultimately be denominated in cost, not raw tokens — different models and cached versus fresh tokens price differently, so a token count is a proxy for the dollar figure you actually cap. Layer the budgets, denominate in cost, and treat the limit as a trigger to wind down before it becomes a trigger to abort.

```python filename=modules/agent-harness/code/harness-inter-21/budget.py:59-61 COMPLETE
def stop_by_iterations(step_tokens, max_steps):
    """The step at which the iteration bound stops the run (it never sees token cost)."""
    return min(len(step_tokens), max_steps)
```

**Bound a run's cost with a cumulative token or dollar budget, not only a step count — steps vary too much in cost for the iteration bound to catch a few fat results — and layer it: a per-step cap to truncate one giant result, a per-run budget to stop accumulation, a per-day budget above that, treating each limit as a trigger to compact and wind down before it becomes a hard abort.**

## External resources

Agent framework documentation on run limits and cost controls (for example max-token, max-cost, or budget settings in orchestration libraries) — the productionized forms of the per-run budget alongside the step limit.

Provider usage and rate-limit dashboards and the token-counting endpoints — the tools for denominating a budget in real cost, accounting for per-model pricing and cached versus fresh tokens.

The companion "bound the agent loop and detect no-progress," "put a timeout on each tool call," and "cap a tool result with head and tail" modules — the iteration bound, the per-call timeout, and the per-step truncation that together with this per-run budget form the loop's cost and liveness guards.
