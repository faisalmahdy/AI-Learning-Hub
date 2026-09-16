#!/usr/bin/env python3
"""Bound the agent loop and detect no-progress -- or a stuck agent runs forever burning budget.

An agent loop calls a tool, reads the result, decides the next call, and repeats until the task
is done. The unspoken assumption is that it will finish. A productive agent does. A stuck one --
retrying a call that always fails, oscillating between two dead ends, waiting on a condition that
will never hold -- does not, and a loop with no stopping rule beyond 'task done' will run until
something external kills it, spending tokens and wall-clock the whole way.

Two rules make the loop safe. A step budget caps the total number of iterations, so the worst
case is bounded instead of unbounded -- but a budget alone still lets a stuck agent burn the
entire cap before giving up. A no-progress detector does better: track the best progress toward
the goal seen so far, and if it has not improved for `patience` steps, stop early and report the
agent as stuck. On a stuck agent the unbounded loop runs to a 1000-step safety ceiling, the
budgeted loop stops at its 50-step cap, and the progress-aware loop gives up after 8 steps and
names the stall; on a productive agent all three finish the moment the goal is reached, so the
detector never fires early. This builds all three and measures the steps each spends.

  --agents    each agent, its behavior, and where its progress toward the goal stalls
  --run       the unbounded, budgeted, and progress-aware loops on the stuck and productive agents
  --check     the stuck agent runs away unbounded; the budget caps it; the detector stops it early

The agent policies and loop limits are the fixture; every step count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "agents.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the agent policies (deterministic)

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


# ------------------------------------------------------------- the three loops

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


# ----------------------------------------------------------------- printing

def agents_view(data):
    cfg = data
    print("AGENTS — behavior and whether progress toward goal %d ever stalls" % cfg["goal"])
    print("-" * 66)
    for a in data["agents"]:
        # trace the first few states
        s = cfg["start"]
        trace = [s]
        for _ in range(cfg["goal"] + 2):
            s = step_state(a["kind"], s, cfg["goal"])
            trace.append(s)
        reaches = "reaches goal" if cfg["goal"] in trace else "NEVER reaches goal"
        print("  %-12s (%s)  states: %s  %s" % (a["name"], a["kind"], trace, reaches))
    print("-" * 66)
    print("  a productive agent's distance-to-goal keeps dropping; a stuck one's stalls.")


def run_view(data):
    print("RUN — steps spent by each loop (budget %d, ceiling %d, patience %d)"
          % (data["max_steps"], data["ceiling"], data["patience"]))
    print("-" * 66)
    print("  agent        unbounded            budgeted            progress-aware")
    for a in data["agents"]:
        k = a["kind"]
        u = run(k, data, bounded=False, progress_aware=False)
        b = run(k, data, bounded=True, progress_aware=False)
        p = run(k, data, bounded=True, progress_aware=True)
        print("  %-12s %-20s %-19s %s"
              % (a["name"], "%d (%s)" % u, "%d (%s)" % b, "%d (%s)" % p))
    print("-" * 66)
    print("  only the progress-aware loop stops a stuck agent early and names the stall.")


def check(data):
    print("SELF-TEST — the stuck agent runs away unbounded; the budget caps it; the detector stops it early")
    print("-" * 66)
    stuck, prod = "stuck", "productive"

    u = run(stuck, data, bounded=False, progress_aware=False)
    runaway = u[0] == data["ceiling"] and "runaway" in u[1]
    print("  unbounded loop runs away on the stuck agent = %s (%d steps, %s)" % (runaway, u[0], u[1]))

    b = run(stuck, data, bounded=True, progress_aware=False)
    budget_caps = b[0] == data["max_steps"]
    print("  the step budget caps it (but still burns the whole budget) = %s (%d steps)" % (budget_caps, b[0]))

    p = run(stuck, data, bounded=True, progress_aware=True)
    detector_early = p[0] < data["max_steps"] and "stuck" in p[1]
    print("  the progress-aware loop stops it early and flags the stall = %s (%d steps, %s)"
          % (detector_early, p[0], p[1]))

    pp = run(prod, data, bounded=True, progress_aware=True)
    no_false_trip = pp[1] == "done"
    print("  the detector does NOT false-trip on the productive agent = %s (%d steps, %s)"
          % (no_false_trip, pp[0], pp[1]))

    ok = runaway and budget_caps and detector_early and no_false_trip
    print("-" * 66)
    print("SELF-TEST %s  runaway=%s  budget_caps=%s  detector_early=%s  no_false_trip=%s"
          % ("PASS" if ok else "FAIL", runaway, budget_caps, detector_early, no_false_trip))
    return ok


def main():
    p = argparse.ArgumentParser(description="Bound the agent loop and detect no-progress.")
    p.add_argument("--agents", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("goal=%d  start=%d  max_steps=%d  ceiling=%d  patience=%d  file=%s  (policies and limits are a fixture)"
          % (data["goal"], data["start"], data["max_steps"], data["ceiling"], data["patience"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.agents:
        agents_view(data)
    elif args.run:
        run_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
