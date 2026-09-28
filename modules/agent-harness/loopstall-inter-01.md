---
id: loopstall-inter-01
title: Break the loop when the agent stops making progress — a step budget alone lets a stuck agent burn its whole allowance
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent harness runs a loop — the model proposes a tool call, the harness executes it and feeds back the observation, the model proposes the next. The obvious safety valve is a step budget: stop after N steps so a runaway agent cannot loop forever. That prevents the infinite case but is blunt: it counts steps without asking whether the steps are doing anything. So an agent that gets stuck — calling the same tool with the same arguments and receiving the same error every time — spends its entire remaining budget on a call it has already learned does nothing, and stops only because it hit the wall, not because anything was resolved. The missing signal is progress. A stuck agent has a signature the budget ignores: consecutive steps whose action and observation are identical, the same call producing the same result, which by definition adds no new information. Watching for a run of identical (action, observation) pairs longer than a window lets the harness detect the loop the moment it forms and break out, with the budget still backstopping the truly pathological case. The honest limit: exact-match detection catches only loops that repeat identically — a livelock whose state drifts each step (an incrementing scratchpad note) slips past an equality check and needs a semantic notion of progress instead. On a fixture with an 8-step budget where the agent reads a config successfully then gets stuck reading a missing file (identical 'error: not found' each time), budget-only runs all 8 steps (4 wasted on the loop) while loop detection with a window of 3 breaks at the fourth step, saving the remaining 4.
eli5: Imagine giving someone a to-do list and saying "you can make at most eight attempts." If they get stuck — trying to open a door that is locked, jiggling the same handle the same way and getting the same nothing — the eight-attempt rule does not help them notice they are stuck; it just lets them jiggle the handle eight times and then quit because they ran out of tries. A smarter rule watches for repetition: if you do the exact same thing and get the exact same result a few times in a row, you are clearly not getting anywhere, so stop now instead of burning the rest of your tries. It will not catch someone who keeps changing tiny things while still going in circles — that is harder to spot — but for the plain "doing the identical thing over and over" case, it saves a lot of wasted effort.
---

## Why this module

Every agent harness needs a way to stop. The model proposes an action, the harness runs it and hands back what happened, and the model proposes the next — and without a limit, a model that has decided the answer is "try again" will try again forever. So harnesses carry a step budget: a hard cap on how many turns the loop may run. It is necessary, and it is not sufficient, and the gap between those two is where a stuck agent quietly wastes an entire budget while the user waits.

The step budget's blindness is specific: it counts steps, not progress. It knows the agent has taken six turns; it has no idea whether those six turns accomplished anything or were the same doomed call six times. So the common failure — an agent calling `read` on a file that does not exist, getting `error: not found`, and concluding it should call `read` on that file again — runs all the way to the cap. Every step consumed a tool execution and a model turn and produced information the agent already had. The budget stopped it, eventually, but only because it ran out of turns, not because it noticed the wheels were spinning.

The signal the budget ignores is sitting right there in the trace: consecutive steps whose action and observation are byte-identical. Identical action, identical result, means the step added nothing — the definition of no progress. This module runs the same stuck trace under a budget-only harness and a loop-detecting one and measures the wasted steps.

**Detect a no-progress loop by watching for a run of consecutive steps with identical (action, observation) pairs and break out when it exceeds a window, instead of relying only on a step budget, because a step budget stops the agent only when it runs out of turns — letting a stuck agent burn its whole allowance repeating one doomed call — whereas loop detection stops it the moment it stops making progress.**

## Concepts

The fixture is a trace of agent steps under an 8-step budget. Step 0 is real progress — the agent reads a config and gets three keys back. Then it gets stuck: it reads a file that does not exist and receives the identical `error: not found` on every subsequent step. The `stall_window` of 3 says how many consecutive identical steps count as a stall.

```json filename=modules/agent-harness/code/loopstall-inter-01/loopstall.json:14-19 COMPLETE
  "max_steps": 8,
  "stall_window": 3,
  "trace": [
    {"action": "read(config.yaml)", "observation": "ok: 3 keys"},
    {"action": "read(missing.yaml)", "observation": "error: not found"},
    {"action": "read(missing.yaml)", "observation": "error: not found"},
```

A budget-only harness is trivial: it runs steps until the cap and stops because it hit the cap, learning nothing about whether the run was productive.

```python filename=modules/agent-harness/code/loopstall-inter-01/loopstall.py:47-51 COMPLETE
def run_budget_only(trace, max_steps):
    """A step-budget harness: execute steps until the cap. Returns steps executed and why it stopped."""
    executed = min(len(trace), max_steps)
    return executed, "hit step budget (%d)" % max_steps
```

Loop detection is the added signal: scan the trace keeping a running count of how many times the current (action, observation) pair has repeated consecutively, and report the first step where that count reaches the window. A different action or a different observation resets the count — so genuine progress never accumulates toward a false stall.

```python filename=modules/agent-harness/code/loopstall-inter-01/loopstall.py:54-79 COMPLETE
def detect_stall(trace, window):
    """Find the first step at which `window` consecutive identical (action, observation) pairs have occurred."""
    prev = None
    run = 0
    for i, step in enumerate(trace):
        sig = (step["action"], step["observation"])
        if sig == prev:
            run += 1
        else:
            run = 1
            prev = sig
        if run >= window:
            return i
    return None


def run_with_detection(trace, max_steps, window):
    """A harness that breaks on a detected stall, backstopped by the budget. Returns steps executed and why it stopped."""
    stall_at = detect_stall(trace, window)
    if stall_at is not None and stall_at + 1 <= max_steps:
        return stall_at + 1, "broke on no-progress loop at step %d" % stall_at
    return run_budget_only(trace, max_steps)
```

<svg role="img" aria-label="Eight steps in a row; step 0 distinct, steps 1 through 7 identical, with a marker at step 3 where three consecutive identical steps trigger the break" viewBox="0 0 330 120">
  <rect x="14" y="40" width="30" height="26" fill="var(--s1)"/>
  <text x="24" y="57" font-size="10" fill="var(--panel)">0</text>
  <rect x="50" y="40" width="30" height="26" fill="var(--s2)"/>
  <text x="61" y="57" font-size="10" fill="var(--panel)">1</text>
  <rect x="86" y="40" width="30" height="26" fill="var(--s2)"/>
  <text x="97" y="57" font-size="10" fill="var(--panel)">2</text>
  <rect x="122" y="40" width="30" height="26" fill="var(--s2)" stroke="var(--ink)" stroke-width="2"/>
  <text x="133" y="57" font-size="10" fill="var(--panel)">3</text>
  <rect x="158" y="40" width="30" height="26" fill="var(--muted)"/>
  <rect x="194" y="40" width="30" height="26" fill="var(--muted)"/>
  <rect x="230" y="40" width="30" height="26" fill="var(--muted)"/>
  <rect x="266" y="40" width="30" height="26" fill="var(--muted)"/>
  <text x="20" y="32" font-size="8" fill="var(--muted)">progress</text>
  <text x="55" y="32" font-size="8" fill="var(--s2)">identical run begins</text>
  <line x1="137" y1="70" x2="137" y2="90" stroke="var(--ink)" stroke-width="1"/>
  <text x="98" y="102" font-size="8.5" fill="var(--ink)">break here (3rd identical)</text>
  <text x="158" y="102" font-size="8.5" fill="var(--muted)">4 steps budget-only would still run</text>
</svg>
^ Step 0 is distinct (progress). Steps 1–2 begin an identical run; at step 3 the run reaches the window of 3 and the harness breaks. The four grey steps are what budget-only runs and loop detection skips.

**Loop detection reads the one thing the budget cannot — whether consecutive steps are identical — so it stops on absence of progress rather than on exhaustion of turns.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the agent-loop control step of a harness, reduced to an eight-step trace so every repeat count and stopping point is checkable by hand.

Run `--trace` to see the steps and where the identical run builds.

```text filename=loopstall.py --trace
  step  action                observation          repeat?
  0     read(config.yaml)     ok: 3 keys           -
  1     read(missing.yaml)    error: not found     -
  2     read(missing.yaml)    error: not found     run 2
  3     read(missing.yaml)    error: not found     run 3
  4     read(missing.yaml)    error: not found     run 4
  5     read(missing.yaml)    error: not found     run 5
  6     read(missing.yaml)    error: not found     run 6
  7     read(missing.yaml)    error: not found     run 7
  first stall (>= 3 identical) at step 3
```

Step 0 stands alone — a different action and a different observation, so its repeat count is nothing. Step 1 starts the doomed run but is itself the first of its kind (repeat count 1, shown as `-`). By step 3 the run reaches 3, the window, and the stall is declared. Every step after that is more of the same — the run count climbs to 7 — which is exactly the wasted work a budget-only harness would grind through.

Now `--detect` compares the two harnesses.

```text filename=loopstall.py --detect
  budget-only:     8 steps executed — hit step budget (8)
  loop detection:  4 steps executed — broke on no-progress loop at step 3
  steps saved by detection = 4 (of the 8-step budget)
```

Budget-only runs all eight steps and stops for the only reason it knows — it hit the cap. Loop detection runs four (steps 0 through 3) and stops because it recognized the loop. Four steps saved, which here is half the budget, and each saved step is a tool execution and a model turn the user does not wait through.

**The two harnesses stop at the same doomed outcome; they differ only in whether the agent repeated a known-useless call four more times before stopping.**

## Build

The self-test asserts both that the stall exists and that detection acts on it — a fix is only meaningful if the naive method genuinely wastes the steps. So it confirms the loop is present, that budget-only runs to the cap, and that detection breaks early.

```python filename=modules/agent-harness/code/loopstall-inter-01/loopstall.py:118-129 COMPLETE
    agent_is_stalled = stall is not None
    print("  the trace contains a no-progress loop (>= %d identical steps) = %s (first at step %s)" % (window, agent_is_stalled, stall))

    budget_only_runs_to_cap = b_exec == min(len(trace), max_steps)
    print("  budget-only runs to the step cap = %s (%d steps)" % (budget_only_runs_to_cap, b_exec))

    detection_breaks_early = d_exec < b_exec
    print("  loop detection breaks before the cap = %s (%d < %d steps)" % (detection_breaks_early, d_exec, b_exec))

    steps_saved = b_exec - d_exec
    detection_saves_steps = steps_saved > 0
    print("  loop detection saves steps = %s (%d steps not wasted on the loop)" % (detection_saves_steps, steps_saved))
```

<svg role="img" aria-label="Two bars: budget-only executes 8 steps with 4 shaded as wasted, loop detection executes 4 steps with none wasted" viewBox="0 0 330 120">
  <text x="10" y="34" font-size="9" fill="var(--muted)">budget-only</text>
  <rect x="10" y="40" width="140" height="20" fill="var(--s1)"/>
  <rect x="150" y="40" width="140" height="20" fill="var(--s2)"/>
  <text x="60" y="54" font-size="8.5" fill="var(--panel)">4 useful</text>
  <text x="185" y="54" font-size="8.5" fill="var(--panel)">4 wasted on loop</text>
  <text x="10" y="86" font-size="9" fill="var(--muted)">loop detection</text>
  <rect x="10" y="92" width="140" height="20" fill="var(--s1)"/>
  <text x="52" y="106" font-size="8.5" fill="var(--panel)">4 steps, then break</text>
</svg>
^ Both harnesses do the same four useful steps. Budget-only adds four wasted loop steps to reach the cap; loop detection stops at the break and does none of them.

Running the check confirms every clause, including that the first progress step is not mistaken for a stall and that the looped steps are truly identical.

```text filename=loopstall.py --check
  the trace contains a no-progress loop (>= 3 identical steps) = True (first at step 3)
  budget-only runs to the step cap = True (8 steps)
  loop detection breaks before the cap = True (4 < 8 steps)
  loop detection saves steps = True (4 steps not wasted on the loop)
  the initial progress step is not flagged as a stall = True (stall starts at step 3, not 0)
  the looped steps are byte-identical (truly no new information) = True
```

**The check pins that detection breaks on the loop and not on the progress step — so it saves the wasted steps without cutting off an agent that is actually getting somewhere.**

## Definition of done

Two properties close it, and one of them exists specifically to guard against a detector that is too eager. The first is that detection saves steps — it breaks before the cap on a genuine loop. The second is that the initial progress step is not flagged: a stall must start at a repeated step, not at the first distinct action, or the detector would kill productive agents that happen to take a similar-looking first step.

```python filename=modules/agent-harness/code/loopstall-inter-01/loopstall.py:132-138 COMPLETE
    first_step_is_progress = trace[0]["observation"] != trace[1]["observation"]
    progress_not_flagged = stall is not None and stall > 0
    print("  the initial progress step is not flagged as a stall = %s (stall starts at step %s, not 0)" % (progress_not_flagged and first_step_is_progress, stall))

    loop_is_identical = trace[stall]["action"] == trace[stall - 1]["action"] and trace[stall]["observation"] == trace[stall - 1]["observation"]
    print("  the looped steps are byte-identical (truly no new information) = %s" % loop_is_identical)
```

The honest limit is worth stating plainly, because exact-match detection is cheap precisely because it is shallow. It catches only loops that repeat identically. An agent caught in a livelock whose state drifts — re-reading the same file but appending an incrementing note to a scratchpad each time, so no two steps are byte-identical — slips right past an equality check while making no real progress. Catching those needs a semantic notion of progress (did the task state actually change?), not string equality, and that is a harder, model-specific judgment. So loop detection is the right cheap filter for the common stuck case, sitting under the step budget rather than replacing it — the budget still backstops the drifting-livelock and truly-runaway cases the equality check cannot see.

<svg role="img" aria-label="Two rows: an identical loop where every step matches and is caught, and a drifting livelock where steps differ slightly and slip past exact-match detection" viewBox="0 0 330 130">
  <text x="10" y="24" font-size="9" fill="var(--muted)">identical loop — caught</text>
  <rect x="10" y="30" width="34" height="22" fill="var(--s2)"/>
  <rect x="48" y="30" width="34" height="22" fill="var(--s2)"/>
  <rect x="86" y="30" width="34" height="22" fill="var(--s2)"/>
  <text x="20" y="45" font-size="8.5" fill="var(--panel)">err</text>
  <text x="58" y="45" font-size="8.5" fill="var(--panel)">err</text>
  <text x="96" y="45" font-size="8.5" fill="var(--panel)">err</text>
  <text x="128" y="45" font-size="8.5" fill="var(--s1)">match → break</text>
  <text x="10" y="86" font-size="9" fill="var(--muted)">drifting livelock — slips past</text>
  <rect x="10" y="92" width="34" height="22" fill="var(--s1)"/>
  <rect x="48" y="92" width="34" height="22" fill="var(--s1)"/>
  <rect x="86" y="92" width="34" height="22" fill="var(--s1)"/>
  <text x="16" y="107" font-size="8.5" fill="var(--panel)">n=1</text>
  <text x="54" y="107" font-size="8.5" fill="var(--panel)">n=2</text>
  <text x="92" y="107" font-size="8.5" fill="var(--panel)">n=3</text>
  <text x="128" y="107" font-size="8.5" fill="var(--muted)">never byte-equal → equality check misses</text>
</svg>
^ Exact-match detection catches the top row (every step identical) but not the bottom: a livelock that changes a byte each step — an incrementing counter — never produces two equal steps, so the equality check never fires and the budget must backstop it.

**Done means detection saves the wasted steps on an identical loop while leaving the progress step alone — a cheap, high-value filter under the step budget, not a complete answer to non-termination.**

## Boss fight

Your agent has a generous 25-step budget and a loop detector that breaks on three identical steps. A user reports the agent "hangs for a minute and then gives up" on a task where it is trying to fix a failing test. You pull the trace and find it ran the full 25 steps: it edited the test file, ran the tests, saw the same failure, edited the file again, ran the tests, saw the same failure — 25 steps of edit-then-test, never the same two steps in a row. Why did the loop detector never fire, and what would you add to catch this without also killing agents that are genuinely iterating?

The detector never fired because no two consecutive steps were identical — the actions alternate between edit and run, and even the two edits differ in their diff, so the (action, observation) pairs are never byte-equal across a window. The agent is in a livelock: making changes, but the changes do not move the test from failing to passing, so it makes no real progress while looking busy. Exact-match detection is blind to this by construction. What catches it is a progress signal above string equality — track the observation that actually matters (the test result: still failing on the identical assertion) across steps, and treat "the failing assertion has not changed in N cycles" as a stall even when the intervening actions differ. The guard against over-eagerness is to key the progress signal on the task's own success criterion, not on surface activity: an agent that is genuinely iterating shows the failure changing (a different assertion, a new error, fewer failures), and that variation resets the stall counter, while an agent stuck on the identical failure does not. You keep the cheap identical-step detector for the common case and add a task-level progress check for the drifting one.

## External resources

The ReAct paper (Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models") — the reasoning-and-acting loop this harness implements, and a good frame for why agents get stuck repeating actions when their reasoning does not incorporate the observation that the last action failed.

The LangGraph and AutoGen documentation on recursion limits and loop control — production agent frameworks' takes on step budgets, cycle detection, and termination conditions, showing how the cheap identical-step filter here fits alongside the deeper progress checks real systems layer on top.
