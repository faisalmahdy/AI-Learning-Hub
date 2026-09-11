#!/usr/bin/env python3
"""A saga compensates the COMPLETED steps in reverse -- not abort, not compensate-all.

A multi-step workflow with real side effects cannot be rolled back by a database
transaction: once a subagent has held a seat or charged a card, that effect is out in
the world. The saga pattern handles this by pairing every forward action with a
compensating action that undoes it, and, when a step fails, running the compensations
for the steps that ALREADY COMPLETED -- in reverse order -- to unwind the work.

Two failures bracket the correct behavior. Abort-only: on failure, stop and do nothing
else, which leaves orphaned side effects (a seat held and a card charged for a ticket
that was never issued). Compensate-all: run the compensation for every declared step,
including the one that failed and any never reached, which OVER-compensates -- refunding
a charge that never happened, driving the ledger negative. The correct saga compensates
exactly the completed prefix, reversed. This measures all three against a shared effect
ledger that should return to zero.

  --forward     run the workflow forward; watch it fail partway and list completed steps
  --run         the full saga: forward until failure, then compensate completed in reverse
  --compare     final state under abort-only, compensate-all, and the correct saga
  --check       correct saga fully reverts; abort orphans effects; compensate-all over-reverts

Stdlib only. Deterministic.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "saga.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- state helpers

def apply_effect(state, effect, sign=1):
    """Add (sign=+1) or undo (sign=-1) an effect to the running ledger."""
    for field, delta in effect.items():
        state[field] += sign * delta


def run_forward(steps, state):
    """Apply forward actions until one fails. Returns the list of COMPLETED steps."""
    completed = []
    for step in steps:
        if step["fails"]:
            break  # the failing step's effect never lands
        apply_effect(state, step["effect"], sign=1)
        completed.append(step)
    return completed


# ------------------------------------------------------------- the three policies

def saga_correct(data):
    """Forward until failure, then compensate the COMPLETED steps in REVERSE order."""
    state = copy.deepcopy(data["initial_state"])
    completed = run_forward(data["steps"], state)
    for step in reversed(completed):  # unwind in reverse
        apply_effect(state, step["effect"], sign=-1)
    return state, completed


def saga_abort_only(data):
    """The bug: on failure, stop. Completed steps' effects are left orphaned."""
    state = copy.deepcopy(data["initial_state"])
    run_forward(data["steps"], state)
    return state


def saga_compensate_all(data):
    """The bug: compensate EVERY declared step, even the failed/never-run ones."""
    state = copy.deepcopy(data["initial_state"])
    run_forward(data["steps"], state)
    for step in reversed(data["steps"]):  # compensates issue_ticket too -- it never ran
        apply_effect(state, step["effect"], sign=-1)
    return state


def is_reverted(state, initial):
    return state == initial


# ----------------------------------------------------------------- printing

def forward_view(data):
    state = copy.deepcopy(data["initial_state"])
    completed = run_forward(data["steps"], state)
    failed = [s["name"] for s in data["steps"] if s["fails"]]
    print("FORWARD — run the workflow until a step fails")
    print("-" * 66)
    print("  completed: %s" % [s["name"] for s in completed])
    print("  failed at: %s" % failed)
    print("  state after forward (effects committed): %s" % state)
    print("-" * 66)
    print("  the completed steps left real side effects that must be unwound.")


def run_view(data):
    state, completed = saga_correct(data)
    print("RUN — the correct saga: compensate completed steps in reverse")
    print("-" * 66)
    print("  compensated (reverse of completed): %s" % [s["name"] for s in reversed(completed)])
    print("  final state: %s" % state)
    print("  fully reverted to initial? %s" % is_reverted(state, data["initial_state"]))
    print("-" * 66)
    print("  every completed effect undone; the failed step needed no compensation.")


def compare_view(data):
    init = data["initial_state"]
    abort = saga_abort_only(data)
    comp_all = saga_compensate_all(data)
    correct, _ = saga_correct(data)
    print("COMPARE — final state under three failure policies (should return to %s)" % init)
    print("-" * 66)
    print("  abort-only:      %s   reverted=%s  (orphaned effects)" % (abort, is_reverted(abort, init)))
    print("  compensate-all:  %s   reverted=%s  (over-compensated)" % (comp_all, is_reverted(comp_all, init)))
    print("  correct saga:    %s   reverted=%s" % (correct, is_reverted(correct, init)))
    print("-" * 66)
    print("  only compensating the COMPLETED prefix, reversed, returns to the initial state.")


def check(data):
    print("SELF-TEST — correct saga fully reverts; abort orphans; compensate-all over-reverts")
    print("-" * 66)
    init = data["initial_state"]

    correct, completed = saga_correct(data)
    reverts = is_reverted(correct, init)
    print("  correct saga returns to the initial state = %s (%s)" % (reverts, correct))

    abort = saga_abort_only(data)
    abort_orphans = not is_reverted(abort, init)
    print("  abort-only leaves orphaned effects = %s (%s)" % (abort_orphans, abort))

    comp_all = saga_compensate_all(data)
    over_reverts = not is_reverted(comp_all, init)
    print("  compensate-all over-compensates the un-run step = %s (%s)" % (over_reverts, comp_all))

    # The correct saga compensates exactly the completed steps, not the failed one.
    failed_names = {s["name"] for s in data["steps"] if s["fails"]}
    only_completed = all(s["name"] not in failed_names for s in completed)
    print("  the failed step is never compensated = %s (compensated %d of %d steps)"
          % (only_completed, len(completed), len(data["steps"])))

    ok = reverts and abort_orphans and over_reverts and only_completed
    print("-" * 66)
    print("SELF-TEST %s  reverts=%s  abort_orphans=%s  over_reverts=%s  only_completed=%s"
          % ("PASS" if ok else "FAIL", reverts, abort_orphans, over_reverts, only_completed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Saga compensation for a failing multi-step workflow.")
    p.add_argument("--forward", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%d  file=%s  (workflow and effects are a fixture)" % (len(data["steps"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.forward:
        forward_view(data)
    elif args.run:
        run_view(data)
    elif args.compare:
        compare_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
