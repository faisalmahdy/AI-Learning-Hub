---
id: harness-inter-20
title: Put a timeout on each tool call — or one hung tool blocks the whole loop no iteration bound can rescue
topic: agent-harness
level: intermediate
status: ready
time: 17 min
summary: An agent loop has two ways to run forever and they need two different guards. The loop-iteration bound stops an agent that keeps stepping without progress — but it is blind to a single tool call that hangs, because a hung call never returns control to the loop, so the loop never counts an iteration or runs its no-progress check. The guard for a hung call is a per-call timeout: give every tool call a deadline, and if it has not returned by then, cancel it and hand the loop a timeout observation the agent can read like any other tool error. The effective duration of any call becomes min(its real duration, the timeout), which bounds the loop's wall-clock time. On a fixture of three calls at 2, 5, and 6 seconds and one that hangs at 600, no timeout makes the loop wait 613 seconds; an 8-second per-call timeout leaves the fast calls untouched, cancels the hang at 8, and cuts the total to 21 seconds.
eli5: If you tell a friend "call each of these four people and come tell me what they said," and one number just rings forever, your friend is stuck on the phone and never comes back — no matter how many times you told them "don't make more than four calls." The rule that helps is different: "if anyone doesn't pick up within eight seconds, hang up and move on." Now one dead number costs eight seconds instead of the whole afternoon.
---

## Why this module

A loop that bounds how many times it iterates is helpless against a single step that never finishes iterating, because the bound only gets to act between steps and a hung call never ends its step.

An agent loop can run forever two different ways. One is an agent that keeps *stepping* — calling tools, reading results, calling more — without ever converging; the fix is a loop-iteration bound with a no-progress check that stops it after so many steps. The other is a single tool call that *hangs*: a wedged subprocess, a socket read with no deadline, an endpoint that takes the request and never answers. The call never returns control to the loop, so the loop never advances to its next iteration, never runs its no-progress check, never does anything at all. The iteration bound is counting iterations that will never complete. The agent is not looping — it is frozen inside one call — and no loop-level guard can see in.

**The loop-iteration bound acts only between steps, so it cannot rescue a step that never returns; a hung tool call is a different failure that needs its own guard.**

That guard is a per-call timeout. Give every tool call a deadline; if it has not returned by then, cancel it and hand the loop a timeout *observation* — an error result the agent reads and reacts to, exactly like any other tool error — instead of blocking. Now the worst a single call can cost is the timeout, the loop regains control, and a wedged tool degrades into a recoverable error rather than a frozen agent. This module runs a loop with one hanging call and shows the timeout cap the damage and hand control back.

## Concepts

A **tool call's duration** is how long it takes to return. Most are fast; the dangerous ones are the calls that, under some condition, never return at all.

The **loop-iteration bound** caps how many steps the agent takes and checks for no progress. It is essential — but it only runs *between* tool calls, so it is blind to what happens *inside* one.

A **hung call** never returns, so it never yields control back to the loop. The iteration bound cannot fire because the iteration never completes; the agent is stuck at one point, not looping.

A **per-call timeout** gives each call a deadline and cancels it if it exceeds it. The call's effective duration becomes `min(real duration, timeout)`, so no single call can cost more than the timeout.

A **timeout observation** is what the cancelled call returns: an error result the agent can read and act on — retry, try another tool, report the failure — so the loop continues instead of freezing.

```python filename=modules/agent-harness/code/harness-inter-20/timeout.py:42-44 COMPLETE
def effective(secs, timeout):
    """A call under a per-call timeout runs for min(its duration, the timeout)."""
    return min(secs, timeout)
```

**The iteration bound and the per-call timeout guard different failures — a runaway loop and a frozen call — and you need both, because each is invisible to the other's mechanism.**

<svg role="img" aria-label="The iteration bound checks between steps; a hung call never reaches the next between-step check, so only a per-call timeout inside the step can cancel it" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">the loop: call → check → call → check ...</text>
  <rect x="20" y="24" width="40" height="18" fill="var(--s1)"/><text x="26" y="37" fill="var(--panel)" font-size="7">call 1</text>
  <circle cx="72" cy="33" r="5" fill="var(--grid)"/><text x="66" y="52" fill="var(--muted)" font-size="7">check</text>
  <rect x="86" y="24" width="40" height="18" fill="var(--s1)"/><text x="92" y="37" fill="var(--panel)" font-size="7">call 2</text>
  <circle cx="138" cy="33" r="5" fill="var(--grid)"/><text x="132" y="52" fill="var(--muted)" font-size="7">check</text>
  <text x="20" y="74" fill="var(--muted)" font-size="8">iteration bound fires at a check (between calls)</text>
  <rect x="20" y="82" width="40" height="18" fill="var(--s2)"/><text x="26" y="95" fill="var(--panel)" font-size="7">call 3</text>
  <text x="64" y="95" fill="var(--s2)" font-size="10">↻ hangs — no next check ever reached</text>
  <text x="20" y="114" fill="var(--muted)" font-size="8">only a timeout INSIDE call 3 can cancel it and reach the next check</text>
</svg>
^ The iteration bound only fires at the checks between calls; a call that hangs never reaches the next check, so nothing between-steps can rescue it — the timeout must live inside the call.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-20/timeout.py

The fixture is a loop of four tool calls, one of which hangs.

```json filename=modules/agent-harness/code/harness-inter-20/timeout.json:1-4 COMPLETE
{
  "_meta": "A loop of tool calls, each with how long it takes in seconds. `hang` models a call that never usefully returns (a wedged subprocess, a network read with no deadline) as a very large duration. The loop runs the calls in order. Without a per-call timeout, the loop waits the full duration of every call, so the hang blocks it for effectively forever. With a per-call timeout of `timeout_s`, each call is cancelled once it exceeds the limit and returns a timeout observation, so its effective time is min(duration, timeout_s) and the loop moves on. Note this is a DIFFERENT guard from the loop-iteration bound: the iteration bound stops an agent that keeps stepping without progress, but a single hung call never even returns control to the loop, so only a per-call timeout can rescue it.",
  "calls": [
    {"id": "read_file", "secs": 2},
```

The effective duration caps at the timeout, a call is timed out when it exceeds it, and the loop's total is the sum of effective durations.

```python filename=modules/agent-harness/code/harness-inter-20/timeout.py:47-54 COMPLETE
def timed_out(secs, timeout):
    """A call is cancelled (timed out) when its real duration exceeds the timeout."""
    return secs > timeout


def total_time(calls, timeout):
    """Loop wall-clock time. timeout=None means no per-call timeout (wait the full duration of each)."""
    return sum(c["secs"] if timeout is None else effective(c["secs"], timeout) for c in calls)
```

Run `--run` to see each call under an 8-second timeout.

```text filename=--run
RUN — real vs effective duration under a 8s per-call timeout
--------------------------------------------------------------
  call         real   effective   outcome
  read_file       2      2        completed
  search          5      5        completed
  fetch_url       6      6        completed
  hang          600      8        TIMED OUT (observation)
```

The three fast calls finish at 2, 5, and 6 seconds — all under the 8-second limit, so the timeout never touches them. The hang would run for 600 seconds; the timeout cancels it at 8 and returns a timeout observation. The agent now has an error result it can react to — retry the fetch, pick another tool, or report that the resource is unreachable — instead of the loop sitting frozen inside a call that will never come back.

<svg role="img" aria-label="Three fast calls finish under the timeout; the hang at 600 seconds is cut to 8 by the per-call timeout" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">duration per call (bars clipped at the 8s timeout line)</text>
  <line x1="70" y1="20" x2="70" y2="100" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="56" y="18" fill="var(--muted)" font-size="7">8s</text>
  <text x="6" y="32" fill="var(--muted)" font-size="8">read</text><rect x="70" y="26" width="18" height="10" fill="var(--s1)"/>
  <text x="6" y="48" fill="var(--muted)" font-size="8">search</text><rect x="70" y="42" width="45" height="10" fill="var(--s1)"/>
  <text x="6" y="64" fill="var(--muted)" font-size="8">fetch</text><rect x="70" y="58" width="54" height="10" fill="var(--s1)"/>
  <text x="6" y="80" fill="var(--muted)" font-size="8">hang</text><rect x="70" y="74" width="8" height="10" fill="var(--s2)"/><rect x="78" y="74" width="207" height="10" fill="var(--grid)"/><text x="120" y="82" fill="var(--muted)" font-size="7">would run to 600s →</text>
  <text x="70" y="114" fill="var(--muted)" font-size="8">the timeout clips only the hang; the fast calls sit entirely left of the line</text>
</svg>
^ The three fast bars end left of the dashed 8-second line and run in full; the hang's bar is clipped at the line, its 600-second tail (grey) never executed.

## Build

The point is the loop's total time. Run `--total`.

```text filename=--total
TOTAL — loop wall-clock time with no timeout vs a 8s per-call timeout
--------------------------------------------------------------
  no timeout:        613 s   (the hang dominates)
  per-call timeout:   21 s   (worst call capped at 8)
```

Without a timeout the loop waits 613 seconds — 2 + 5 + 6 + 600 — and 600 of those are the single hung call; the useful work is 13 seconds drowned by one wedged tool. With the 8-second per-call timeout the total falls to 21 seconds: the three fast calls unchanged, plus 8 for the cancelled hang. The timeout did not just save time, it changed the failure mode — an unbounded freeze became a bounded, observable error the loop survives. And the bound holds for any call: no matter how badly a tool wedges, it costs at most the timeout.

<svg role="img" aria-label="Loop total time is 613 seconds without a timeout and 21 seconds with an 8-second per-call timeout" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">loop wall-clock time (seconds)</text>
  <line x1="30" y1="24" x2="30" y2="88" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="88" x2="290" y2="88" stroke="var(--grid)" stroke-width="1"/>
  <rect x="30" y="30" width="255" height="18" fill="var(--s2)"/><text x="150" y="43" fill="var(--panel)" font-size="8">no timeout: 613 s</text>
  <rect x="30" y="60" width="9" height="18" fill="var(--s1)"/><text x="44" y="73" fill="var(--muted)" font-size="8">per-call timeout: 21 s</text>
  <text x="30" y="99" fill="var(--muted)" font-size="8">one hung call is the whole difference between a 21s loop and a 613s freeze</text>
</svg>
^ The no-timeout bar stretches to 613 seconds, almost all of it the hang; the timeout bar is a sliver at 21 — the guard erases the freeze.

## Definition of done

The self-test pins the behavior: the hang would block, the timeout caps every call, fast calls are untouched, exactly the hang times out, and the total is bounded.

```python filename=modules/agent-harness/code/harness-inter-20/timeout.py:91-103 COMPLETE
    hang_would_block = hang["secs"] > 10 * t
    print("  the hung call would block far past the timeout = %s (%d > %d)" % (hang_would_block, hang["secs"], 10 * t))

    timeout_caps_each = all(effective(c["secs"], t) <= t for c in calls)
    print("  every call's effective time is capped at the timeout = %s (max %d <= %d)" % (timeout_caps_each, max(effective(c["secs"], t) for c in calls), t))

    fast_calls_untouched = all(effective(c["secs"], t) == c["secs"] and not timed_out(c["secs"], t) for c in fast)
    print("  calls under the limit complete untouched = %s (%s)" % (fast_calls_untouched, [c["id"] for c in fast]))

    only_hang_times_out = [c["id"] for c in calls if timed_out(c["secs"], t)] == [hang["id"]]
    print("  exactly the hung call times out = %s" % only_hang_times_out)

    timeout_bounds_total = total_time(calls, t) < total_time(calls, None) and total_time(calls, t) <= len(calls) * t
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the hang would block; the timeout caps each call; fast calls untouched; only the hang is cut
--------------------------------------------------------------------------------------------------------
  the hung call would block far past the timeout = True (600 > 80)
  every call's effective time is capped at the timeout = True (max 8 <= 8)
  calls under the limit complete untouched = True (['read_file', 'search', 'fetch_url'])
  exactly the hung call times out = True
  the timeout bounds the loop's total time = True (21 < 613, and <= 4*8)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  hang_would_block=True  timeout_caps_each=True  fast_calls_untouched=True  only_hang_times_out=True  timeout_bounds_total=True
```

**Done means the guard is proven selective and bounding: only the hung call is cancelled (the 2/5/6-second calls run in full), every call's effective time is at most the 8-second limit, and the loop's total is bounded to 21 seconds instead of 613.**

## Boss fight

The timeout rescued the loop. Predict the two ways to set it wrong — too short and too long — and whether a per-call timeout alone is enough. It is tempting to pick one global timeout and apply it to every tool.

Too short and you cancel calls that were about to succeed: a large file read or a slow-but-legitimate search that needs twelve seconds gets killed at eight, turned into a spurious timeout observation, and the agent retries or gives up on work that would have completed. Too long and the guard barely helps — a five-minute timeout on a call that hangs still costs five minutes each time. The right timeout is per-tool, sized to that tool's real latency distribution with headroom: a local file read gets a short deadline, a web fetch a longer one, a heavy build longer still. One global number cannot fit tools whose honest durations span three orders of magnitude, so the timeout belongs to the tool, not the loop.

The deeper point is that a timeout must actually *cancel*, not just stop waiting. If you implement it by abandoning the call — moving on while the wedged subprocess or socket keeps running in the background — you have bounded the loop's perceived time but leaked a resource, and enough leaked calls exhaust file descriptors or threads and wedge the whole agent a different way. A real timeout cancels the underlying work: kills the process, closes the socket, cancels the task. And the timeout is one guard among several — it bounds a single call, the iteration bound bounds the number of calls, and a total budget bounds the whole run; a robust harness composes all three, because each is blind to the failure the others catch.

```python filename=modules/agent-harness/code/harness-inter-20/timeout.py:47-49 COMPLETE
def timed_out(secs, timeout):
    """A call is cancelled (timed out) when its real duration exceeds the timeout."""
    return secs > timeout
```

**Give each tool call a per-tool timeout that actually cancels the underlying work and returns a timeout observation the loop can read — sized to that tool's real latency, not one global number — and compose it with the iteration bound and a total run budget, because a hung call, a runaway loop, and an overspent run are three different failures no single guard catches.**

## External resources

The `asyncio.wait_for` and `subprocess` timeout documentation (or your language's equivalent) — the mechanics of attaching a deadline to a call and, crucially, cancelling the underlying task rather than merely abandoning the wait.

Production agent frameworks' per-tool timeout and cancellation settings — how real harnesses let each tool declare its own deadline and what they return to the model when one fires.

The companion "bound the agent loop and detect no-progress" and "cap the sub-agent recursion depth" modules — the iteration and recursion guards that sit beside the per-call timeout; together they bound a call, a loop, and a tree.
