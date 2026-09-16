---
id: harness-inter-16
title: Return a tool error as an observation — or one transient failure aborts the loop and discards the work
topic: agent-harness
level: intermediate
status: ready
time: 19 min
summary: A sequential agent runs a plan step by step, each step a tool call feeding the next. Tools fail transiently all the time — a timeout, a rate limit, a flaky socket — and recover on a retry. What the harness does with that failure is the design choice. The naive harness lets the tool's exception propagate: the loop unwinds at the failing step, and every step that already succeeded is thrown away because the caller sees only failure. The fix is to treat a tool error as data — catch it and return it to the agent as an observation, the same way a result is returned — so the agent can retry, try another tool, or report a specific failure. On a four-step plan where step 2 fails once then succeeds, the raising harness aborts with one step done; the recovering harness retries step 2 and finishes all four.
eli5: Imagine following a recipe where one jar is briefly stuck. If you throw out the whole meal the moment the jar resists, you waste everything you already cooked. If instead you note "jar stuck, try again," you open it on the second twist and finish the dish. A good agent treats a tool that fails as a note to act on, not a reason to burn the kitchen down.
---

## Why this module

Tools fail for reasons that have nothing to do with the agent's plan, and a harness that treats every failure as fatal throws away good work over a momentary blip.

A sequential agent is a loop: run a step, feed its result to the next, repeat. Real tools fail transiently — a network timeout, a rate limit, a connection reset — and the same call succeeds moments later. The naive harness lets that failure propagate as an exception. The loop unwinds, the run ends at the failing step, and the caller receives an error. The steps that already completed are gone: their work is discarded because the only thing returned is the failure. A one-second blip on step 2 costs you the completed step 1 and the steps 3 and 4 that never ran.

**A raised exception is control flow that unwinds the loop; a tool failure should be data the loop can act on.**

The fix is to catch the failure and return it to the agent as an observation — "the tool failed with X" — exactly as a successful result is returned. Now the agent has a choice: retry with backoff up to a cap, switch tools, or report a specific, localized failure instead of an opaque stack trace. This module runs a raising harness and a recovering harness on one transient failure and measures what each keeps.

## Concepts

The **plan** is a list of steps run in order. Each step is a tool call. A step marked transient fails on its first attempt and succeeds on a retry — the model for a timeout or rate limit that clears.

The **raising harness** attempts each step once and lets an exception propagate. On the transient step it aborts, returning the steps completed so far and a failure status. Because the return is a failure, a caller treats the whole run as failed — the completed steps are wasted.

The **recovering harness** wraps each tool call: on failure it does not raise, it records the error as an observation and retries the step, up to `max_retries` extra attempts. A transient failure is absorbed by one retry; a permanent failure (retries exhausted) becomes a clean, localized `FAILED at <step>` rather than a stack trace.

The distinction being tested is not "does the tool fail" — it fails identically in both. It is what survives the failure: the raising harness ends with one step done, the recovering harness with all four, and only the transient step needed more than one attempt.

**Returning an error as an observation turns a failure from a loop-ending event into a decision the agent gets to make.**

The two harnesses see the identical failure; the fork is whether it travels as an exception up the stack or as a message back into the loop.

<svg role="img" aria-label="A tool failure branches two ways: as an exception it unwinds and ends the run; as an observation it re-enters the loop as a retry decision" viewBox="0 0 300 130" width="300" height="130">
  <rect x="115" y="10" width="70" height="20" fill="none" stroke="var(--line)" stroke-width="1"/>
  <text x="123" y="24" fill="var(--muted)" font-size="8">tool fails</text>
  <line x1="150" y1="30" x2="70" y2="55" stroke="var(--s1)" stroke-width="1.5"/>
  <line x1="150" y1="30" x2="230" y2="55" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="20" y="70" fill="var(--s1)" font-size="8">raise → unwind</text>
  <text x="185" y="70" fill="var(--s2)" font-size="8">observe → decide</text>
  <rect x="30" y="80" width="80" height="20" fill="none" stroke="var(--s1)" stroke-width="1"/>
  <text x="40" y="94" fill="var(--s1)" font-size="8">run ends</text>
  <rect x="180" y="80" width="95" height="20" fill="none" stroke="var(--s2)" stroke-width="1"/>
  <text x="188" y="94" fill="var(--s2)" font-size="8">retry / reroute</text>
  <text x="185" y="118" fill="var(--muted)" font-size="8">↩ back into the loop</text>
</svg>
^ One failure, two fates: an exception unwinds the loop and ends the run; an observation flows back in and becomes the agent's next decision.

There is a boundary: recovery must be bounded. Retrying forever on a permanent error is its own failure mode, which is why the retry has a cap. Recovery means "give the agent the error and a bounded chance to act," not "hide the error and loop."

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-16/recover.py

The fixture is a four-step plan; step 2 (`fetch_data`) is the transient one.

```json filename=modules/agent-harness/code/harness-inter-16/plan.json:1-11 COMPLETE
{
  "_meta": "A sequential agent plan: steps run in order, each is a tool call. fails_first marks a step whose tool fails on its first attempt but succeeds if retried (a transient error -- a timeout, a rate limit, a flaky network). max_retries is how many extra attempts the recovering harness will give a failing step. The question: what happens to the already-completed steps when step 2 fails?",
  "steps": [
    {"name": "read_config", "fails_first": false},
    {"name": "fetch_data", "fails_first": true},
    {"name": "transform", "fails_first": false},
    {"name": "write_output", "fails_first": false}
  ],
  "max_retries": 2
}
```

The two harnesses differ only in how they treat a failing step. The raising one returns at the first failure; the recovering one retries within a cap and returns the error as a status only if the retries are exhausted.

```python filename=modules/agent-harness/code/harness-inter-16/recover.py:40-64 COMPLETE
def run_raise(steps):
    """Naive harness: a tool exception propagates, so the loop aborts at the first failure."""
    done = []
    for s in steps:
        if s["fails_first"]:                       # one attempt only; the exception unwinds the loop
            return done, "ABORTED at %s" % s["name"]
        done.append(s["name"])
    return done, "DONE"


def run_recover(steps, max_retries):
    """Recovering harness: a tool error is returned as an observation and the step is retried up to the cap."""
    done, attempts = [], {}
    for s in steps:
        attempt = 0
        while True:
            attempt += 1
            failed = s["fails_first"] and attempt == 1   # transient: fails only on the first attempt
            if not failed or attempt >= 1 + max_retries:
                break
        attempts[s["name"]] = attempt
        if s["fails_first"] and attempt == 1:            # never recovered within the cap
            return done, attempts, "FAILED at %s" % s["name"]
        done.append(s["name"])
    return done, attempts, "DONE"
```

The `--run` view drives both on the same plan and prints what each finished and where it stopped.

```python filename=modules/agent-harness/code/harness-inter-16/recover.py:69-80 COMPLETE
def run_view(data):
    steps, mr = data["steps"], data["max_retries"]
    rd, rstatus = run_raise(steps)
    cd, _, cstatus = run_recover(steps, mr)
    print("RUN — sequential plan of %d steps (step 2 fails transiently)" % len(steps))
    print("-" * 64)
    print("  raising harness:    done %s" % rd)
    print("                      status: %s" % rstatus)
    print("  recovering harness: done %s" % cd)
    print("                      status: %s" % cstatus)
    print("-" * 64)
    print("  the raise unwinds the loop at step 2; the recover retries and continues.")
```

Run `--run` and put the two side by side.

```text filename=--run
RUN — sequential plan of 4 steps (step 2 fails transiently)
----------------------------------------------------------------
  raising harness:    done ['read_config']
                      status: ABORTED at fetch_data
  recovering harness: done ['read_config', 'fetch_data', 'transform', 'write_output']
                      status: DONE
----------------------------------------------------------------
  the raise unwinds the loop at step 2; the recover retries and continues.
```

The raising harness ends with one step done and an abort status — `read_config` succeeded, but that work is now stranded behind a failure the caller sees as total. The recovering harness completes all four steps and reports DONE, having absorbed the same transient failure with a single retry.

<svg role="img" aria-label="Raising harness completes step 1 then aborts at step 2; recovering harness completes all four steps" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="22" fill="var(--muted)" font-size="9">raise</text>
  <rect x="55" y="12" width="45" height="18" fill="var(--s2)"/>
  <text x="60" y="25" fill="var(--panel)" font-size="8">config</text>
  <rect x="102" y="12" width="45" height="18" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="108" y="25" fill="var(--s1)" font-size="8">fetch ✗</text>
  <text x="152" y="25" fill="var(--muted)" font-size="8">— aborted, 3 steps lost</text>
  <line x1="10" y1="45" x2="290" y2="45" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="72" fill="var(--muted)" font-size="9">recover</text>
  <rect x="55" y="62" width="45" height="18" fill="var(--s2)"/>
  <text x="60" y="75" fill="var(--panel)" font-size="8">config</text>
  <rect x="102" y="62" width="45" height="18" fill="var(--s2)"/>
  <text x="106" y="75" fill="var(--panel)" font-size="8">fetch↻</text>
  <rect x="149" y="62" width="45" height="18" fill="var(--s2)"/>
  <text x="152" y="75" fill="var(--panel)" font-size="8">transf</text>
  <rect x="196" y="62" width="45" height="18" fill="var(--s2)"/>
  <text x="201" y="75" fill="var(--panel)" font-size="8">write</text>
  <text x="55" y="105" fill="var(--muted)" font-size="8">all 4 done; only fetch needed a retry (↻)</text>
</svg>
^ Same transient failure on step 2: the raising harness strands the completed step and never reaches the last two; the recovering harness retries and finishes the plan.

## Build

The `--attempts` view shows the recovering harness did not retry everything — only the step that actually failed.

```text filename=--attempts
ATTEMPTS — attempts per step in the recovering harness (cap 2 retries)
----------------------------------------------------------------
  read_config  1 attempt(s)
  fetch_data   2 attempt(s)   <- retried after a transient error
  transform    1 attempt(s)
  write_output 1 attempt(s)
----------------------------------------------------------------
  only the transient step needed a retry; the rest passed first try.
```

Three steps ran once; `fetch_data` ran twice. Recovery is targeted — the harness spends an extra attempt only where the error occurred, not a blanket re-run of the plan. That is the difference between "return the error to the agent" and "restart from scratch," which would re-execute `read_config` and any side effects it had.

<svg role="img" aria-label="Bar of attempts per step: read_config 1, fetch_data 2, transform 1, write_output 1" viewBox="0 0 300 120" width="300" height="120">
  <line x1="90" y1="10" x2="90" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <line x1="90" y1="95" x2="285" y2="95" stroke="var(--grid)" stroke-width="1"/>
  <rect x="95" y="18" width="70" height="12" fill="var(--s2)"/>
  <text x="10" y="28" fill="var(--muted)" font-size="8">read_config</text>
  <text x="170" y="28" fill="var(--muted)" font-size="8">1</text>
  <rect x="95" y="38" width="140" height="12" fill="var(--s1)"/>
  <text x="10" y="48" fill="var(--muted)" font-size="8">fetch_data</text>
  <text x="240" y="48" fill="var(--muted)" font-size="8">2</text>
  <rect x="95" y="58" width="70" height="12" fill="var(--s2)"/>
  <text x="10" y="68" fill="var(--muted)" font-size="8">transform</text>
  <text x="170" y="68" fill="var(--muted)" font-size="8">1</text>
  <rect x="95" y="78" width="70" height="12" fill="var(--s2)"/>
  <text x="10" y="88" fill="var(--muted)" font-size="8">write_output</text>
  <text x="170" y="88" fill="var(--muted)" font-size="8">1</text>
</svg>
^ Attempts per step: only the transient step consumed a retry; recovery is localized, not a re-run of the whole plan.

## Definition of done

The self-test pins the outcomes: the raising harness aborts early and reports failure despite completed work, the recovering harness finishes all steps, it retried exactly the transient step, and every other step passed first try.

```python filename=modules/agent-harness/code/harness-inter-16/recover.py:102-115 COMPLETE
    raise_aborts_early = len(rd) < len(steps)
    print("  the raising harness stops before the end = %s (%d of %d steps)" % (raise_aborts_early, len(rd), len(steps)))

    raise_discards_completed = rstatus != "DONE" and len(rd) >= 1
    print("  the raising harness reports failure though %d step(s) succeeded = %s (%r)" % (len(rd), raise_discards_completed, rstatus))

    recover_completes_all = len(cd) == len(steps) and cstatus == "DONE"
    print("  the recovering harness finishes every step = %s (%d of %d, %r)" % (recover_completes_all, len(cd), len(steps), cstatus))

    failing = next(s["name"] for s in steps if s["fails_first"])
    recover_retried_transient = attempts[failing] > 1
    print("  the recovering harness retried the transient step = %s (%s took %d attempts)" % (recover_retried_transient, failing, attempts[failing]))

    others_passed_first = all(attempts[s["name"]] == 1 for s in steps if not s["fails_first"])
    print("  every non-failing step passed on the first attempt = %s" % others_passed_first)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the raising harness aborts early and discards completed work; the recovering one finishes
----------------------------------------------------------------------------------------------------
  the raising harness stops before the end = True (1 of 4 steps)
  the raising harness reports failure though 1 step(s) succeeded = True ('ABORTED at fetch_data')
  the recovering harness finishes every step = True (4 of 4, 'DONE')
  the recovering harness retried the transient step = True (fetch_data took 2 attempts)
  every non-failing step passed on the first attempt = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  raise_aborts_early=True  raise_discards_completed=True  recover_completes_all=True  recover_retried_transient=True  others_passed_first=True
```

**Done means the recovery is provable and targeted: the recovering harness completed 4 of 4 steps while the raising one completed 1 of 4, and only the transient step consumed an extra attempt.**

## Boss fight

The recovering harness retries within a cap. Predict what happens if `fetch_data` is not transient but permanently broken — the endpoint is gone, not slow. It is tempting to think recovery saves you here too.

It does not, and the cap is why the design is safe rather than reckless. A permanent failure exhausts `max_retries` and the harness returns `FAILED at fetch_data` — a specific, localized status the agent can report or route around, not an infinite retry loop and not a bare stack trace. Recovery is not "never fail"; it is "fail with information the agent can use." Set every `fails_first` step to a tool that always fails and the recovering harness stops after the cap with a clear message, having still preserved the steps that ran before it.

The mirror-image mistake is retrying the wrong class of error. A transient error (timeout, rate limit) deserves a retry; a deterministic error (bad arguments, permission denied) will fail identically every attempt, so retrying it just burns the budget the bounded loop was meant to protect. A real harness inspects the error before retrying — retry the transient, surface the deterministic — which is exactly why the error must be returned as data the agent can classify, not swallowed.

```python filename=modules/agent-harness/code/harness-inter-16/recover.py:50-64 COMPLETE
def run_recover(steps, max_retries):
    """Recovering harness: a tool error is returned as an observation and the step is retried up to the cap."""
    done, attempts = [], {}
    for s in steps:
        attempt = 0
        while True:
            attempt += 1
            failed = s["fails_first"] and attempt == 1   # transient: fails only on the first attempt
            if not failed or attempt >= 1 + max_retries:
                break
        attempts[s["name"]] = attempt
        if s["fails_first"] and attempt == 1:            # never recovered within the cap
            return done, attempts, "FAILED at %s" % s["name"]
        done.append(s["name"])
    return done, attempts, "DONE"
```

**Return the tool error as an observation and bound the recovery: a transient failure becomes a retry, a permanent one becomes a localized report, and neither unwinds the work that already succeeded.**

## External resources

The Anthropic and OpenAI tool-use guides — both return a tool error to the model as a tool-result message (an `is_error` result), the exact "error as observation" pattern, so the model can decide the next action.

The ReAct paper (Yao et al., 2022) — reasoning-and-acting interleaves observations back into the agent's context; a tool error is just another observation the agent reasons over, which is why it must be data, not an exception.

The AWS builder's-library article on timeouts, retries, and backoff — which errors are safe to retry, why the retry needs a cap, and how a bounded retry differs from a retry storm (the boss-fight boundary).
