"""Break the loop when the agent stops making progress -- a step budget alone lets a stuck agent burn its whole allowance repeating one doomed call.

An agent harness runs a loop: the model proposes a tool call, the harness executes it and feeds the observation back, and the model proposes the next one. The obvious safety valve is a step budget -- stop after N steps so a runaway agent cannot loop forever. That cap prevents the infinite case, but it is a blunt instrument: it does not notice that the agent stopped getting anywhere, only that it ran out of turns. So an agent that gets stuck -- calling the same tool with the same arguments and receiving the same error every time -- spends the ENTIRE remaining budget on a call it has already learned does nothing, and only stops because it hit the wall, not because anything was resolved. The user waits for eight steps of a doomed read; the budget was spent, and none of it moved the task forward.

The missing signal is PROGRESS. A step budget counts steps; it does not ask whether the steps are doing anything. A stuck agent has a signature the budget ignores: consecutive steps whose action AND observation are identical -- the same call producing the same result, which by definition adds no new information. Watching for that signature -- a run of identical (action, observation) pairs longer than some window -- lets the harness detect the loop the moment it forms and break out, rather than grinding to the budget. The budget still backstops the truly pathological case; loop detection handles the common one, where the agent is not infinite, just stuck.

The catch, which keeps this honest, is that exact-match detection only catches loops that repeat IDENTICALLY. A livelock whose state drifts each step -- an agent that re-reads the same file but appends an incrementing note to its scratchpad, so no two steps are byte-identical -- slips past an equality check even though it is making no real progress. Catching those needs a semantic notion of progress (did the task state actually change?), not string equality. So loop detection is a cheap, high-value filter for the common stuck case, not a complete solution to non-termination.

The rule: detect a no-progress loop by watching for a run of consecutive steps with identical (action, observation) pairs and break out of the agent loop when it exceeds a window, instead of relying only on a step budget, because a step budget stops the agent only when it runs out of turns -- letting a stuck agent burn its whole allowance repeating one doomed call -- whereas loop detection stops it the moment it stops making progress.

On this fixture the budget is 8 steps and the agent reads a config successfully, then gets stuck reading a missing file, getting the identical 'error: not found' each time. Budget-only runs all 8 steps (4 wasted on the loop). Loop detection with a window of 3 identical steps breaks at the fourth step, saving the remaining 4. This computes both.

  --trace     the agent's steps and where consecutive identical (action, observation) pairs begin to repeat
  --detect    budget-only vs loop detection: steps executed, steps saved, and why each one stopped
  --check     the agent stalls in an identical-step loop; budget-only runs to the cap while loop detection breaks early and saves steps

trace, max_steps, and stall_window are the fixture; the stall index, steps executed, and steps saved are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "loopstall.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run_budget_only(trace, max_steps):
    """A step-budget harness: execute steps until the cap. Returns steps executed and why it stopped."""
    executed = min(len(trace), max_steps)
    return executed, "hit step budget (%d)" % max_steps


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


# ----------------------------------------------------------------- printing

def trace_view(data):
    trace, window = data["trace"], data["stall_window"]
    print("TRACE — the agent's steps (window %d identical = stall)" % window)
    print("-" * 66)
    print("  step  action                observation          repeat?")
    prev = None
    run = 0
    for i, step in enumerate(trace):
        sig = (step["action"], step["observation"])
        if sig == prev:
            run += 1
        else:
            run = 1
            prev = sig
        mark = "run %d" % run if run > 1 else "-"
        print("  %-4d  %-20s  %-19s  %s" % (i, step["action"], step["observation"], mark))
    print("-" * 66)
    stall = detect_stall(trace, window)
    print("  first stall (>= %d identical) at step %s" % (window, stall))


def detect_view(data):
    trace, max_steps, window = data["trace"], data["max_steps"], data["stall_window"]
    b_exec, b_why = run_budget_only(trace, max_steps)
    d_exec, d_why = run_with_detection(trace, max_steps, window)
    print("DETECT — budget-only vs loop detection")
    print("-" * 62)
    print("  budget-only:     %d steps executed — %s" % (b_exec, b_why))
    print("  loop detection:  %d steps executed — %s" % (d_exec, d_why))
    print("-" * 62)
    print("  steps saved by detection = %d (of the %d-step budget)" % (b_exec - d_exec, max_steps))


def check(data):
    print("SELF-TEST — the agent stalls in an identical-step loop; budget-only runs to the cap while loop detection breaks early and saves steps")
    print("-" * 132)
    trace, max_steps, window = data["trace"], data["max_steps"], data["stall_window"]
    b_exec, _ = run_budget_only(trace, max_steps)
    d_exec, _ = run_with_detection(trace, max_steps, window)
    stall = detect_stall(trace, window)

    agent_is_stalled = stall is not None
    print("  the trace contains a no-progress loop (>= %d identical steps) = %s (first at step %s)" % (window, agent_is_stalled, stall))

    budget_only_runs_to_cap = b_exec == min(len(trace), max_steps)
    print("  budget-only runs to the step cap = %s (%d steps)" % (budget_only_runs_to_cap, b_exec))

    detection_breaks_early = d_exec < b_exec
    print("  loop detection breaks before the cap = %s (%d < %d steps)" % (detection_breaks_early, d_exec, b_exec))

    steps_saved = b_exec - d_exec
    detection_saves_steps = steps_saved > 0
    print("  loop detection saves steps = %s (%d steps not wasted on the loop)" % (detection_saves_steps, steps_saved))

    first_step_is_progress = trace[0]["observation"] != trace[1]["observation"]
    progress_not_flagged = stall is not None and stall > 0
    print("  the initial progress step is not flagged as a stall = %s (stall starts at step %s, not 0)" % (progress_not_flagged and first_step_is_progress, stall))

    loop_is_identical = trace[stall]["action"] == trace[stall - 1]["action"] and trace[stall]["observation"] == trace[stall - 1]["observation"]
    print("  the looped steps are byte-identical (truly no new information) = %s" % loop_is_identical)

    ok = agent_is_stalled and budget_only_runs_to_cap and detection_breaks_early and detection_saves_steps and (progress_not_flagged and first_step_is_progress) and loop_is_identical
    print("-" * 132)
    print("SELF-TEST %s  agent_is_stalled=%s  budget_only_runs_to_cap=%s  detection_breaks_early=%s  detection_saves_steps=%s  progress_not_flagged=%s  loop_is_identical=%s"
          % ("PASS" if ok else "FAIL", agent_is_stalled, budget_only_runs_to_cap, detection_breaks_early, detection_saves_steps, progress_not_flagged and first_step_is_progress, loop_is_identical))
    return ok


def main():
    p = argparse.ArgumentParser(description="Loop / no-progress detection: detect a stall by watching for a run of consecutive steps with identical (action, observation) pairs and break out of the agent loop when it exceeds a window, instead of relying only on a step budget, because a step budget stops the agent only when it runs out of turns -- letting a stuck agent burn its whole allowance repeating one doomed call -- whereas loop detection stops it the moment it stops making progress.")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--detect", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("max_steps=%d  stall_window=%d  trace_len=%d  file=%s  (the trace, budget, and window are a fixture)"
          % (data["max_steps"], data["stall_window"], len(data["trace"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trace:
        trace_view(data)
    elif args.detect:
        detect_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
