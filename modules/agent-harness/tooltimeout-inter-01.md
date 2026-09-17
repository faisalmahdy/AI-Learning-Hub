---
id: tooltimeout-inter-01
title: Wrap every tool call in a per-call timeout — one hung tool freezes the whole agent, and no step budget catches it
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent loop's tools are I/O — a network request, a subprocess, a database query, another model — and any of them can hang: a socket with no timeout, a deadlocked lock, a dependency that is down but holding the connection open. The naive loop dispatches the call and blocks on its return, so a call that never returns blocks the loop forever. The agent is not crashed and not oscillating; it is wedged on one call. The subtle part is that the two usual runaway guards do not fire: the loop-iteration bound and the tool-call budget both count completed steps, and this step never completes, so the run just stops making progress — silently, with no error and no result. On the fixture a three-call plan (read_config 20 ms, call_flaky_api which never returns, write_output 30 ms) run with no timeout finishes c1, blocks on c2 forever, and never reaches c3: completed = False, wedged on c2. The fix is a per-call timeout, a watchdog around each dispatch: if the tool has not returned within the budget, abort the wait and hand the loop a timeout error for that call, exactly as if the tool had raised. With a 100 ms budget, c1 finishes normally, c2 is aborted at 100 ms and recorded as a timeout error, c3 finishes normally, and the run completes in 150 ms — bounded by n_calls times the timeout (150 ≤ 300) — with every step accounted for and the two within-budget calls untouched. The rule: an iteration cap bounds how many steps an agent takes, but only a per-call timeout bounds how long a single step can take, and without the second an agent inherits the availability of its least reliable tool.
eli5: Imagine a cook working through a recipe, one step at a time, who will not start the next step until the current one is truly done. If one step is "wait for the delivery to arrive" and the delivery never comes, the cook stands at the door forever — not quitting, not doing anything else, just waiting. A rule like "don't do more than twenty steps" doesn't help, because the cook never finishes even this one step to count it. The fix is a kitchen timer on every step: if the delivery hasn't come in five minutes, the timer rings, the cook writes down "delivery failed", and moves on to the next step. Quick steps finish before the timer and are untouched; only the stuck step gets cut off. Now the cook always keeps moving, no matter which supplier lets them down.
---

## Why this module

Agents are built to be bounded. You add an iteration cap so the loop cannot run forever, a tool-call budget so it cannot spend forever, maybe a wall-clock deadline for the whole run. It feels like the runaway cases are covered.

They are not, because all of those guards count things that happen between tool calls, and the most common way an agent dies is inside one. A tool that hangs — no response, no error, the connection just open — stops the loop at the dispatch, before control ever returns to the place where budgets are checked. The agent is alive, the process is running, and nothing is happening.

**An iteration cap bounds how many steps an agent takes; only a per-call timeout bounds how long one step can take — and the second is the one a hung tool defeats.**

## Concepts

The agent loop has a shape: the model proposes a call, the harness dispatches it, waits for the result, appends the observation, and asks the model for the next call. The wait is a blocking call — the harness hands control to the tool and does not get it back until the tool returns.

That handoff is the vulnerability. If the tool returns quickly, control comes back and the loop continues. If the tool is slow, the loop is slow. If the tool never returns, the loop never continues — the harness is parked inside the dispatch, holding a thread, waiting on something that will not arrive.

The reason the usual guards miss this is worth stating precisely. An iteration bound checks a counter at the top of each loop iteration; a tool-call budget decrements after each call returns. Both live in the loop body, and the loop body only runs between calls. A call that never returns never yields control back to the loop body, so neither guard is ever evaluated. They bound completed steps, and a wedged step is not a completed step.

A per-call timeout lives somewhere else: around the dispatch itself. It starts a clock when the call begins and, if the budget elapses before the tool returns, it abandons the wait and synthesizes a failure result — a timeout error — as though the tool had raised. Now control returns to the loop with an error in hand, and every downstream mechanism works again: the model can retry, pick another tool, or report the failure, and the budgets resume counting. The timeout is a ceiling on one call, not a delay: a call that finishes early returns early and is not touched.

**Budgets and iteration caps run in the loop body between calls; a per-call timeout runs around the call, which is the only place that can rescue control from a tool that never returns it.**

<svg role="img" aria-label="The agent loop as a cycle: model proposes a call, harness dispatches, waits for the result, appends the observation, back to the model. The iteration cap and budget are marked on the loop body; the 'wait' arrow is marked as the block point where a hung tool never returns, which the loop-body guards cannot see." viewBox="0 0 520 170">
<rect x="0" y="0" width="520" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">where each guard sits in the loop</text>
<rect x="40" y="60" width="90" height="30" fill="none" stroke="var(--line)"></rect>
<text x="52" y="79" fill="var(--ink)" font-size="10">model plans</text>
<text x="135" y="72" fill="var(--muted)" font-size="14">&#8594;</text>
<rect x="160" y="60" width="90" height="30" fill="none" stroke="var(--line)"></rect>
<text x="168" y="79" fill="var(--ink)" font-size="10">dispatch call</text>
<text x="255" y="72" fill="var(--s1)" font-size="14">&#8594;</text>
<rect x="280" y="60" width="90" height="30" fill="none" stroke="var(--s1)"></rect>
<text x="298" y="79" fill="var(--s1)" font-size="10">WAIT</text>
<text x="375" y="72" fill="var(--muted)" font-size="14">&#8594;</text>
<rect x="400" y="60" width="100" height="30" fill="none" stroke="var(--line)"></rect>
<text x="408" y="79" fill="var(--ink)" font-size="10">append result</text>
<text x="40" y="120" fill="var(--muted)" font-size="10">iteration cap + budget checked here (loop body, between calls)</text>
<text x="280" y="120" fill="var(--s1)" font-size="10">hung tool blocks HERE</text>
<text x="280" y="136" fill="var(--s1)" font-size="10">only a per-call timeout wraps this step</text>
</svg>
^ The runaway guards live in the loop body and only run between calls; the wait is the one place a tool can refuse to return, and it is outside every guard except a timeout wrapped around the dispatch.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/agent-harness/code/tooltimeout-inter-01/tooltimeout.py

The plan is three calls, the middle one a flaky API that never returns.

```json filename=modules/agent-harness/code/tooltimeout-inter-01/tooltimeout.json:3-8 COMPLETE
  "timeout_ms": 100,
  "plan": [
    {"id": "c1", "tool": "read_config", "duration_ms": 20},
    {"id": "c2", "tool": "call_flaky_api", "duration_ms": null},
    {"id": "c3", "tool": "write_output", "duration_ms": 30}
  ]
```

A duration of null means the call never returns — it hangs whoever blocks on it.

```python filename=modules/agent-harness/code/tooltimeout-inter-01/tooltimeout.py:28-30 COMPLETE
def hangs(call):
    """A call with no return duration never returns -- it hangs the caller that blocks on it."""
    return call["duration_ms"] is None
```

The no-timeout loop dispatches each call and blocks on it, so the hung call ends the run.

```python filename=modules/agent-harness/code/tooltimeout-inter-01/tooltimeout.py:33-41 COMPLETE
def run_no_timeout(plan):
    """Dispatch each call and block on its return; a hung call wedges the loop and later steps never run."""
    elapsed, outcomes = 0, []
    for call in plan:
        if hangs(call):
            return {"completed": False, "elapsed": None, "wedged_at": call["id"], "outcomes": outcomes}
        elapsed += call["duration_ms"]
        outcomes.append({"id": call["id"], "outcome": "ok", "ms": call["duration_ms"]})
    return {"completed": True, "elapsed": elapsed, "wedged_at": None, "outcomes": outcomes}
```

```text filename=tooltimeout.py --notimeout
NO-TIMEOUT — dispatch each call and block on its return
----------------------------------------------------------------
  c1 read_config      20 ms    -> ok
  c2 call_flaky_api   hangs    -> BLOCKS FOREVER
  c3 write_output     30 ms    -> never reached
----------------------------------------------------------------
  run completed = False   wedged on c2   (c3 never ran)
```

c1 runs, c2 blocks forever, and c3 — a call that would have taken 30 ms — never runs at all. The run reports completed = False, but a real agent does not even get to report that: it is parked in the dispatch, holding a thread, indefinitely. No iteration cap fires, because the loop body never runs again to check one.

The per-call timeout bounds each dispatch by the budget instead.

```python filename=modules/agent-harness/code/tooltimeout-inter-01/tooltimeout.py:44-54 COMPLETE
def run_with_timeout(plan, timeout_ms):
    """Bound each call by the timeout; an over-budget call is aborted and recorded as a timeout error."""
    elapsed, outcomes = 0, []
    for call in plan:
        if hangs(call) or call["duration_ms"] > timeout_ms:
            elapsed += timeout_ms
            outcomes.append({"id": call["id"], "outcome": "timeout", "ms": timeout_ms})
        else:
            elapsed += call["duration_ms"]
            outcomes.append({"id": call["id"], "outcome": "ok", "ms": call["duration_ms"]})
    return {"completed": True, "elapsed": elapsed, "wedged_at": None, "outcomes": outcomes}
```

```text filename=tooltimeout.py --timeout
TIMEOUT — bound each call by 100 ms; over-budget calls become timeout errors
----------------------------------------------------------------
  c1 OK       at 20 ms
  c2 TIMEOUT  at 100 ms
  c3 OK       at 30 ms
----------------------------------------------------------------
  run completed = True   total elapsed = 150 ms   (bounded by 3 x 100)
```

c2 is aborted at the 100 ms budget and recorded as a timeout error, so the loop gets control back and runs c3. The run completes in 150 ms, and c1 and c3 — both well inside the budget — ran to their real durations, not the ceiling.

<svg role="img" aria-label="Two timelines. No-timeout: c1 runs 20 ms, then c2 extends off the right edge with an arrow marked 'forever' and c3 never appears. Timeout: c1 runs 20 ms, c2 is cut at 100 ms with a timeout mark, then c3 runs 30 ms, total 150 ms." viewBox="0 0 520 170">
<rect x="0" y="0" width="520" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">no-timeout wedges on c2; timeout caps c2 and reaches c3</text>
<text x="12" y="46" fill="var(--muted)" font-size="10">no timeout</text>
<rect x="90" y="36" width="30" height="16" fill="var(--s2)"></rect>
<text x="94" y="48" fill="var(--panel)" font-size="9">c1</text>
<rect x="120" y="36" width="260" height="16" fill="var(--s1)"></rect>
<text x="126" y="48" fill="var(--panel)" font-size="9">c2 blocks</text>
<text x="384" y="48" fill="var(--s1)" font-size="14">&#8594; forever</text>
<text x="12" y="96" fill="var(--muted)" font-size="10">per-call</text>
<rect x="90" y="86" width="30" height="16" fill="var(--s2)"></rect>
<text x="94" y="98" fill="var(--panel)" font-size="9">c1</text>
<rect x="120" y="86" width="100" height="16" fill="var(--s1)"></rect>
<text x="126" y="98" fill="var(--panel)" font-size="9">c2 cut 100</text>
<rect x="220" y="86" width="45" height="16" fill="var(--s2)"></rect>
<text x="226" y="98" fill="var(--panel)" font-size="9">c3</text>
<text x="272" y="98" fill="var(--muted)" font-size="9">done, 150 ms</text>
</svg>
^ The timeout turns c2's unbounded block into a fixed 100 ms cut, which is the only reason c3 ever runs — the fast calls c1 and c3 keep their real durations.

## Build

The self-test states the full contrast: the no-timeout run hangs, and the timeout run completes, stays bounded, surfaces the hung call as an error, and does not touch the fast calls.

```python filename=modules/agent-harness/code/tooltimeout-inter-01/tooltimeout.py:100-104 COMPLETE
    timeout_bounds_total = wt["elapsed"] <= len(plan) * t
    print("  timeout run total is bounded by n_calls x timeout = %s (%d <= %d)" % (timeout_bounds_total, wt["elapsed"], len(plan) * t))

    hung_becomes_error = any(o["outcome"] == "timeout" for o in wt["outcomes"] if o["id"] == nt["wedged_at"])
    print("  the hung call is surfaced as a timeout error, not a freeze = %s" % hung_becomes_error)
```

```text filename=tooltimeout.py --check
SELF-TEST — the no-timeout run hangs while the timeout run completes, bounds its total time, surfaces the hung call as an error, and leaves the fast calls untouched
----------------------------------------------------------------------------------------------------------------
  no-timeout run does not complete (wedged on c2) = True
  timeout run completes = True (elapsed 150 ms)
  timeout run total is bounded by n_calls x timeout = True (150 <= 300)
  the hung call is surfaced as a timeout error, not a freeze = True
  calls within budget run to completion, not aborted = True (2 fast calls)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  notimeout_hangs=True  timeout_completes=True  timeout_bounds_total=True  hung_becomes_error=True  fast_untouched=True
```

<svg role="img" aria-label="A comparison: no-timeout run completes 1 of 3 steps and does not finish; per-call-timeout run completes all 3 steps and finishes in 150 ms." viewBox="0 0 460 150">
<rect x="0" y="0" width="460" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">steps completed (plan has 3)</text>
<line x1="60" y1="120" x2="430" y2="120" stroke="var(--line)"></line>
<line x1="60" y1="42" x2="430" y2="42" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="434" y="45" fill="var(--muted)" font-size="9">3</text>
<rect x="110" y="94" width="70" height="26" fill="var(--s1)"></rect>
<text x="108" y="88" fill="var(--s1)" font-size="10">no-timeout: 1 (hung)</text>
<rect x="290" y="42" width="70" height="78" fill="var(--s2)"></rect>
<text x="292" y="36" fill="var(--s2)" font-size="10">timeout: 3</text>
</svg>
^ Without a per-call timeout the agent completes one step and stops; with it, all three complete — the hung call costs a bounded 100 ms instead of the whole run.

**fast_untouched is the clause that keeps the timeout honest: it must abort only the over-budget call, or a too-tight budget turns every slow-but-fine tool into a spurious failure.**

## Definition of done

You can explain why an iteration cap and a tool-call budget both fail to stop a hung tool: they are checked in the loop body, which only runs between calls, and a hung call never returns control to the loop body.

You can place the timeout correctly — around the dispatch, not in the loop body — and say what result it synthesizes when it fires (a timeout error, indistinguishable to the loop from the tool raising).

You can give the bound a per-call timeout puts on the whole run (n_calls times the timeout) and contrast it with the no-timeout run's bound (none — it is the availability of the least reliable tool).

You can name the tension in choosing the budget: too high and a hung tool still costs a long stall, too low and legitimately slow tools are aborted as failures.

## Boss fight

Your agent calls a search tool that usually returns in 200 ms, and once a day the search backend has an incident and the tool stops responding entirely. On those days the agent runs "freeze" — the process is up, no errors in the logs, no output — until someone restarts them. The iteration cap is 30 and the tool-call budget is 50; neither ever trips.

First: explain, in terms of where each guard is evaluated, why a cap of 30 and a budget of 50 both sit at zero usage while the agent is frozen. What number is actually stuck, and where?

Then: add a per-call timeout. Picking the value forces a real tradeoff — the tool's normal latency is 200 ms but its p99 is 1.5 s under load. Set the budget at 300 ms and name what breaks on a busy day; set it at 3 s and name what you have given back on an incident day. What information would let you choose well, and why is one fixed number for all tools the wrong shape?

Finally: a timeout that fires leaves a question the loop must answer — is the operation actually cancelled, or just abandoned? For a search (read-only) versus a charge_card (side effect), state what "the call timed out" lets the agent safely do next, and why abandoning a wait is not the same as cancelling the work the tool may still be doing on the other side.

## External resources

Every HTTP client library documents a per-request timeout (connect and read) precisely because a socket with no timeout blocks forever — the agent-level per-call timeout is the same guard one layer up, covering tools that are not HTTP.

The distinction between abandoning a wait and cancelling the work behind it is the subject of structured-concurrency writing (for example Trio's cancellation model); it is what the boss fight's read-only-versus-side-effect question turns on.
