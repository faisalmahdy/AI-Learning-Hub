---
id: harness-inter-06
title: Bound the agent loop and detect no-progress — or a stuck agent runs forever burning budget
topic: agent-harness
level: intermediate
status: ready
time: 5-8h
summary: An agent loop calls a tool, reads the result, decides the next call, and repeats until the task is done — on the unspoken assumption it will finish, which a stuck agent (retrying a call that always fails, oscillating between dead ends) never does, so a loop whose only stopping rule is "task done" runs until something external kills it. Two rules make it safe: a step budget caps total iterations, and a no-progress detector tracks the best progress toward the goal and stops early if it has not improved for a patience window. On a stuck agent the unbounded loop runs to a 1000-step ceiling, the budgeted loop stops at its 50-step cap but still burns the whole budget, and the progress-aware loop gives up after 8 steps and names the stall — while on a productive agent all three finish in 8 steps, so the detector never false-trips. A budget bounds the waste; the detector plus the budget bounds it tightly and reports why, the difference between an agent that fails cheaply and one that spins in silence.
eli5: Imagine sending someone to fetch water, but the well is dry. A careless plan says "come back when you have water" — so they stand at the dry well forever. A slightly better plan says "give up after fifty tries" — better, but they still waste fifty trips. The best plan says "if you haven't gotten any closer in a few tries, stop and tell me it's dry" — so they quit after a handful and you learn the well is empty. Bounding how long to try, and noticing when you're making no progress, is what keeps a helper from getting stuck forever.
---

## Why this module

Every agent loop has the same skeleton: look at the state, choose a tool call, run it, fold the result back in, and go again until the task is finished. That last clause hides an assumption that the task *will* finish, and it is the one that fails in production. Agents get stuck — a tool call fails the same way every time and the agent keeps retrying it, two states alternate forever, a condition it waits on never becomes true. In all of these the "task done" test never fires, and a loop with no other stopping rule iterates until it hits a rate limit, a timeout, or a human noticing the bill, burning tokens on every wasted turn.

The first and cheapest fix is a step budget: a hard cap on iterations. With it, the worst case goes from unbounded to bounded — a stuck agent stops after N steps instead of never — and it is the floor every loop should have. But a budget alone is blunt: a stuck agent still burns the entire budget before giving up, and gives up with no explanation, just "out of steps," which looks the same whether it was close or spinning uselessly from step one.

The better fix layers a no-progress detector on top. The idea is to measure progress toward the goal and remember the best you have seen; if the best has not improved for a patience window of steps, the agent is not working toward the goal, it is stuck, so stop early and say so. This module builds all three loops — unbounded, budgeted, and progress-aware — and runs them on a stuck agent and a productive one. On the stuck agent the unbounded loop runs to a 1000-step ceiling, the budget stops it at 50, and the detector stops it at 8 with the reason "no progress"; on the productive agent all three finish in 8 steps and the detector never fires early. Everything runs offline against an agent fixture, stdlib Python 3, `$0.00`. The instinct to unlearn is that an agent loop ends when the task is done. It ends when the task is done *or* the budget is spent *or* progress has stalled — and only the last of those turns a silent runaway into a cheap, explained failure.

## Concepts

Named here so you can find them again; each is built below.

- **Agent loop** — call a tool, read the result, decide the next call, repeat until done.
- **Step budget** — a hard cap on iterations; bounds the worst case from infinite to finite.
- **Progress** — a measure of how close the state is to the goal; for a stuck agent it stalls.
- **No-progress detector** — stop early when the best progress has not improved for a patience window.
- **Patience** — how many stalled steps to tolerate before declaring the agent stuck.
- **Runaway** — a loop with no bound spending budget until something external kills it.

## Worked example

Source: the termination logic of an agent loop — the rules that decide when to stop iterating. The agent policies stand in for real agents: one making steady progress, one stuck retrying a dead end. The state-toward-goal is an abstraction of any progress signal (tests passing, subgoals closed, distance to a target).

Script and fixture: `modules/agent-harness/code/harness-inter-06/` — `terminate.py`, and `agents.json`, two agents and the loop limits. Every command runs from there.

### Two agents: one progresses, one stalls

The agents are deterministic policies over a state that should move toward the goal.

```
# terminate.py:40-52 — COMPLETE (a productive policy advances; a stuck one never does)
def step_state(kind, state, goal):
    """Where the agent's state goes next. 'productive' advances; 'stuck' never gets closer."""
    if kind == "productive":
        return min(state + 1, goal)            # advances one toward the goal each step
    if kind == "stuck":
        return state                           # fixed point: never moves, never reaches goal
    if kind == "oscillating":
        return goal - 1 if state != goal - 1 else goal - 2   # bounces, never reaches goal
    raise ValueError(kind)


def distance(state, goal):
    return abs(goal - state)
```

The productive agent moves one step closer to the goal each iteration; the stuck agent sits at a fixed point, never getting closer; the oscillating one bounces between two states that are both short of the goal. Look at their traces:

```
# $ python3 terminate.py --agents
#   solver       (productive)  states: [0, 1, 2, 3, 4, 5, 6, 7, 8, 8, 8]  reaches goal
#   looper       (stuck)  states: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  NEVER reaches goal
```

run: 2026-08-27 · deterministic; policies and limits are a fixture · goal 8 · `python3 terminate.py --agents`

The solver's state climbs 0, 1, 2, … to the goal of 8 and stops; the looper's state never leaves 0. The "task done" test — state equals goal — fires for the solver and never for the looper, so a loop that stops only on that test finishes the solver and runs the looper forever. The difference the loop needs to notice is not that the looper is failing tool calls; it is that the looper is making no progress, which is visible in the state trace long before any external limit.

### The loop, with two switches

One loop implements all three variants; `bounded` sets the cap, `progress_aware` adds the detector.

```
# terminate.py:57-77 — COMPLETE (the loop: goal test, no-progress detector, and the cap)
def run(kind, cfg, bounded, progress_aware):
    """Run the loop; returns (steps, outcome). bounded caps steps; progress_aware stops on a stall."""
    goal = cfg["goal"]
    max_steps = cfg["max_steps"] if bounded else cfg["ceiling"]
    patience = cfg["patience"]

    state = cfg["start"]
    best = distance(state, goal)
    since_improved = 0
    for step in range(1, max_steps + 1):
        state = step_state(kind, state, goal)
        d = distance(state, goal)
        if d < best:
            best, since_improved = d, 0
        else:
            since_improved += 1
        if state == goal:
            return step, "done"
        if progress_aware and since_improved >= patience:
            return step, "stuck (no progress)"
    return max_steps, ("ceiling hit (runaway)" if not bounded else "budget exhausted")
```

<svg viewBox="0 0 700 170" role="img" aria-label="An agent loop iteration with three exits. After each step, check: state equals goal? exit done. Then: progress stalled for patience steps? exit stuck. Then: step count over budget? exit budget-exhausted. Otherwise loop again. A plain loop has only the first exit.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">three exits from the loop — a plain loop has only the first</text>
    <rect x="30" y="60" width="70" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="65" y="79" text-anchor="middle" fill="var(--ink)" font-size="8">step</text>
    <line x1="100" y1="75" x2="130" y2="75" stroke="var(--ink)"></line>
    <rect x="130" y="58" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="175" y="79" text-anchor="middle" fill="var(--acc-ink)" font-size="8">state=goal?</text>
    <line x1="175" y1="92" x2="175" y2="118" stroke="var(--s1)"></line><rect x="140" y="118" width="70" height="24" fill="var(--s1)"></rect><text x="175" y="134" text-anchor="middle" fill="var(--panel)" font-size="8">done</text>
    <line x1="220" y1="75" x2="250" y2="75" stroke="var(--ink)"></line>
    <rect x="250" y="58" width="110" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="305" y="75" text-anchor="middle" fill="var(--acc-ink)" font-size="8">stalled ≥ patience?</text>
    <line x1="305" y1="92" x2="305" y2="118" stroke="var(--s2)"></line><rect x="265" y="118" width="80" height="24" fill="var(--s2)"></rect><text x="305" y="134" text-anchor="middle" fill="var(--panel)" font-size="8">stuck</text>
    <line x1="360" y1="75" x2="390" y2="75" stroke="var(--ink)"></line>
    <rect x="390" y="58" width="100" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="440" y="75" text-anchor="middle" fill="var(--acc-ink)" font-size="8">step &gt; budget?</text>
    <line x1="440" y1="92" x2="440" y2="118" stroke="var(--muted)"></line><rect x="395" y="118" width="90" height="24" fill="var(--muted)"></rect><text x="440" y="134" text-anchor="middle" fill="var(--panel)" font-size="7">budget exhausted</text>
    <path d="M 490 75 Q 560 75 560 40 Q 560 20 65 20 Q 40 20 40 55" fill="none" stroke="var(--line)"></path><text x="300" y="16" fill="var(--muted)" font-size="7"> </text>
    <text x="500" y="79" fill="var(--muted)" font-size="7">else loop</text>
  </g>
</svg>
^ Each iteration checks three exits in turn: the goal (the only one a plain loop has), the no-progress stall, and the step budget. Add the middle and right checks and a stuck agent can no longer run forever.

The three stopping conditions are the three `return`s. The goal test (`state == goal`) is the one everyone writes. The no-progress test (`since_improved >= patience`) is the detector: `best` tracks the closest the agent has ever come, and `since_improved` counts steps since that improved — when it crosses `patience`, the agent has spent a whole window getting no closer, so it is stuck. And the final return is the cap: a bounded loop calls it "budget exhausted," an unbounded one runs to the ceiling and calls it "runaway." Run all three on both agents:

```
# $ python3 terminate.py --run
#   agent        unbounded            budgeted            progress-aware
#   solver       8 (done)             8 (done)            8 (done)
#   looper       1000 (ceiling hit (runaway)) 50 (budget exhausted) 8 (stuck (no progress))
```

run: 2026-08-27 · deterministic · `python3 terminate.py --run`

The solver row is identical across all three — 8 steps, done — because a productive agent reaches the goal before any limit matters, so the safeguards are invisible when not needed. The looper row is the whole point. Unbounded, it runs 1000 steps to the ceiling (a stand-in for "forever") and reports a runaway. Budgeted, it stops at 50, having wasted every one of those steps. Progress-aware, it stops at 8 — the patience window — and reports "stuck (no progress)," a cheap, explained failure the caller can act on. Same stuck agent; the difference is 1000 versus 50 versus 8 wasted steps, and whether the loop can say why it quit.

<svg viewBox="0 0 700 200" role="img" aria-label="A bar chart of steps wasted by the stuck agent under three loops. Unbounded: a bar running off the chart to 1000, labeled runaway. Budgeted: a bar to 50, labeled budget exhausted. Progress-aware: a short bar to 8, labeled stuck detected. The productive agent finishes at 8 under all three.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">steps spent on the STUCK agent — lower and explained is better</text>
    <line x1="60" y1="150" x2="660" y2="150" stroke="var(--line)"></line>
    <rect x="90" y="40" width="80" height="110" fill="var(--s2)"></rect><text x="130" y="34" text-anchor="middle" fill="var(--s2)" font-size="8">1000</text><text x="130" y="166" text-anchor="middle" fill="var(--muted)" font-size="7">unbounded</text><text x="130" y="178" text-anchor="middle" fill="var(--s2)" font-size="7">runaway</text>
    <rect x="300" y="95" width="80" height="55" fill="var(--muted)"></rect><text x="340" y="89" text-anchor="middle" fill="var(--muted)" font-size="8">50</text><text x="340" y="166" text-anchor="middle" fill="var(--muted)" font-size="7">budgeted</text><text x="340" y="178" text-anchor="middle" fill="var(--muted)" font-size="7">budget exhausted</text>
    <rect x="510" y="136" width="80" height="14" fill="var(--s1)"></rect><text x="550" y="130" text-anchor="middle" fill="var(--s1)" font-size="8">8</text><text x="550" y="166" text-anchor="middle" fill="var(--muted)" font-size="7">progress-aware</text><text x="550" y="178" text-anchor="middle" fill="var(--s1)" font-size="7">stuck detected</text>
    <text x="90" y="60" fill="var(--panel)" font-size="7">(off chart →</text>
  </g>
</svg>
^ The stuck agent costs 1000 steps unbounded, 50 with a budget, and 8 with the detector — and only the detector names the failure ("stuck") instead of reporting a bare limit. The budget bounds the waste; the detector minimizes and explains it.

### The detector does not false-trip

A safeguard that stopped good agents early would be worse than none — so the crucial check is that the detector leaves the productive agent alone.

The check that the detector leaves a healthy agent alone is one line — the productive run must exit as `done`:

```
# terminate.py:133-136 — COMPLETE (the detector must not false-trip on a productive agent)
    pp = run(prod, data, bounded=True, progress_aware=True)
    no_false_trip = pp[1] == "done"
    print("  the detector does NOT false-trip on the productive agent = %s (%d steps, %s)"
          % (no_false_trip, pp[0], pp[1]))
```

<svg viewBox="0 0 700 180" role="img" aria-label="Two lines of distance-to-goal over steps. The productive agent's distance falls steadily from 8 to 0, so best-so-far improves every step and the stall counter stays at 0. The stuck agent's distance stays flat at 8, so best-so-far never improves and the stall counter climbs to the patience threshold of 8, where the detector fires.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">distance to goal per step: productive falls, stuck stays flat</text>
    <line x1="60" y1="140" x2="640" y2="140" stroke="var(--line)"></line>
    <line x1="60" y1="30" x2="60" y2="140" stroke="var(--line)"></line>
    <text x="52" y="44" text-anchor="end" fill="var(--muted)" font-size="7">8</text><text x="52" y="140" text-anchor="end" fill="var(--muted)" font-size="7">0</text>
    <line x1="90" y1="40" x2="620" y2="40" stroke="var(--s2)"></line><text x="440" y="34" fill="var(--s2)" font-size="8">stuck: flat → stall counter climbs to patience → fires</text>
    <polyline points="90,40 158,53 226,66 294,79 362,92 430,105 498,118 566,131 620,140" fill="none" stroke="var(--s1)"></polyline><text x="300" y="128" fill="var(--s1)" font-size="8">productive: improves every step → counter stays 0</text>
    <text x="60" y="160" fill="var(--muted)" font-size="8">the detector fires only where best-so-far stops improving — never on the falling line</text>
  </g>
</svg>
^ The productive agent's distance falls every step, resetting the stall counter, so it exits only at the goal; the stuck agent's distance never drops, so the stall counter climbs to the patience threshold and the detector fires. The detector keys on the flat line, not the falling one.

The productive agent improves its distance every step, so `since_improved` resets to 0 each iteration and never reaches `patience`; the loop exits only through the goal test, at step 8, exactly as an unguarded loop would. The detector fires only when progress genuinely stalls — invisible when things go well, decisive when they go wrong — which is exactly the property a safeguard must have.

**An agent loop must stop on the task being done, a step budget, or stalled progress — because a stuck agent never satisfies the done test and a budget alone still burns its whole cap; a no-progress detector tracking the best progress toward the goal stops the stuck agent in 8 steps with a named stall instead of 1000, while never firing early on a productive agent that improves every step.**

### The self-test

The `--check` mode plants the bug — a loop with no bound — and proves the ladder of fixes: unbounded runs away, the budget caps it (but wastes the cap), the detector stops it early and flags it, and the detector does not false-trip on the productive agent.

```
# $ python3 terminate.py --check
#   unbounded loop runs away on the stuck agent = True (1000 steps, ceiling hit (runaway))
#   the step budget caps it (but still burns the whole budget) = True (50 steps)
#   the progress-aware loop stops it early and flags the stall = True (8 steps, stuck (no progress))
#   the detector does NOT false-trip on the productive agent = True (8 steps, done)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 terminate.py --check`

The `detector_early` and `no_false_trip` lines are the pair that justifies the detector over a bare budget: it stops the stuck agent far sooner (8 versus 50) *and* leaves the productive agent untouched. A detector that achieved the first by being trigger-happy would fail the second, cutting off slow-but-real progress — so the test insists on both, which separates a real no-progress signal from an impatient one.

```
# terminate.py:120-127 — COMPLETE (unbounded runs away; the budget caps it at max_steps)
    u = run(stuck, data, bounded=False, progress_aware=False)
    runaway = u[0] == data["ceiling"] and "runaway" in u[1]
    print("  unbounded loop runs away on the stuck agent = %s (%d steps, %s)" % (runaway, u[0], u[1]))

    b = run(stuck, data, bounded=True, progress_aware=False)
    budget_caps = b[0] == data["max_steps"]
    print("  the step budget caps it (but still burns the whole budget) = %s (%d steps)" % (budget_caps, b[0]))
```

### The running tally

| loop | stuck agent: steps | stuck agent: outcome | productive agent |
|---|---|---|---|
| unbounded | 1000 | runaway (hit ceiling) | 8, done |
| budgeted | 50 | budget exhausted | 8, done |
| progress-aware | 8 | stuck (no progress) | 8, done |

Read the stuck-agent columns down the rows: the step count falls 1000 → 50 → 8 as each safeguard is added, and the outcome goes from an unexplained runaway to a bare limit to a named stall. The productive column never changes — all three finish in 8 — the signature of a good safeguard: it costs nothing when the agent is healthy and cuts the waste when it is not. A budget is the mandatory floor; the detector turns "stopped, reason unknown" into "stopped, stuck," and an agent that fails cheaply and explains itself is one you can operate.

### What we did not settle

This is the core termination discipline; production loops add more. The progress signal here is a clean scalar distance; real progress is fuzzier — a subgoal count, a test pass rate, an LLM-judged "closer?" — and a noisy signal needs a patience window wide enough not to trip on a temporary plateau. A stuck agent detected early should often escalate — replan, change strategy, or ask a human — so the detector is a trigger for intervention, not only termination. Oscillation is a subtler stall than a fixed point, and detecting cycles complements the best-progress-stalls signal. And budgets compose across levels — a per-call timeout, a per-task step budget, a per-session token budget — with `ship-inter-05` the same discipline for time. The invariant: an agent loop needs a stopping rule beyond success, and the best one measures progress and explains its stop.

## Build

The build in one paragraph: give every agent loop a hard step budget so its worst case is bounded rather than infinite, and layer a no-progress detector on top — track the best progress toward the goal and stop early, with a named "stuck" outcome, when it has not improved for a patience window — so a stuck agent fails in a handful of steps with an explanation instead of burning the whole budget silently. Choose a progress signal for your task, set patience wide enough to tolerate real plateaus, escalate (replan or ask a human) rather than merely stopping when useful, and compose the step budget with per-call timeouts and a token budget.

We opened on the two agents. The number that proves the fix is the steps the stuck agent spends under each loop:

```
# modules/agent-harness/code/harness-inter-06/ — COMPLETE, run from that directory
$ python3 terminate.py --run
  looper       1000 (ceiling hit (runaway)) 50 (budget exhausted) 8 (stuck (no progress))
```

Now build your own. Take a real agent loop and a task, define a progress signal, and run a genuinely stuck agent through an unbounded loop, a budgeted one, and a progress-aware one. Your number to beat is not success rate; it is **the steps a stuck agent wastes and whether the stop is explained — the detector should stop it in a small multiple of your patience with a named stall, while a productive agent finishes untouched**. Confirm the detector does not false-trip on real progress. Bring back the stuck agent's step counts under all three. Good luck.

## Definition of done

- [ ] An agent loop stopping on the task-done test
- [ ] A step budget capping total iterations (bounded vs an unbounded ceiling)
- [ ] A progress signal (distance to goal) and a best-so-far tracker
- [ ] A no-progress detector stopping early after a patience window with no improvement
- [ ] Confirmation an unbounded loop runs away on a stuck agent and a budget caps it
- [ ] Confirmation the detector stops the stuck agent early with a named stall
- [ ] Confirmation the detector does not false-trip on a productive agent
- [ ] `python3 terminate.py --check` printing SELF-TEST PASS: runaway, budget_caps, detector_early, no_false_trip
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why is "stop when the task is done" an insufficient stopping rule for an agent loop?
2. What does a step budget guarantee, and what does it still fail to do well on a stuck agent?
3. How does the no-progress detector decide the agent is stuck? What do `best` and the patience window track?
4. Why does the self-test insist the detector not false-trip on the productive agent?
5. Your own loop ran a stuck agent three ways. How many steps did it waste under each, and was the stop explained?

## External resources

- Agent-framework documentation on max-iterations / recursion limits (e.g. LangChain's max_iterations, or any ReAct loop's step cap) — my summary: the step-budget floor every framework ships and why; read it for the mandatory bound this module starts from.
- Writing on agent loop design and "stuck" detection in autonomous agents — my summary: heuristics for recognizing no-progress (repeated actions, cycling states, stalled subgoals) and escalating; read it for progress signals richer than the scalar distance here.
- This hub, *ship-inter-05* (propagate the deadline to each hop) — read it for the same bounding discipline applied to time rather than steps, the other budget an agent loop must respect.
