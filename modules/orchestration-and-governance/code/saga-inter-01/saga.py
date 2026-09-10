"""Undo a failed multi-step transaction with compensating actions, in reverse -- a saga stays consistent without the locks two-phase commit holds.

A transaction that spans several services -- reserve a flight, reserve a hotel, charge a card -- must not leave a half-finished mess: a flight and hotel reserved but never paid for is money and inventory leaking. Two-phase commit solves this by making every participant lock its resources and wait for a global commit, which is atomic but blocks (a coordinator crash freezes the participants holding locks). A SAGA takes the opposite approach: run the steps one at a time, each committing immediately with no lock held, and if a later step fails, UNDO the completed steps by running a compensating action for each. No step waits on the others; consistency is restored by compensation, not prevented by locking.

The mechanism has two rules. Forward: execute the steps in order, each fully committing before the next begins. On failure: for every step that already completed, run its compensating action -- and run them in REVERSE order, because later steps may depend on earlier ones, so you unwind newest-first (cancel the hotel before cancelling the flight, the mirror of how you booked). The step that failed is not compensated, because it never completed; only the successful steps need undoing. When the compensations finish, the system is back to a consistent state with none of the partial effects left behind.

The contrast with the naive alternative is the point. A pipeline that just runs steps until one fails and stops leaves every completed step's effect in place -- the orphaned flight and hotel reservations -- because it has no notion of undo. The saga's compensating actions are exactly that notion: an explicit inverse for each step, invoked on failure to clean up. This is what lets a saga be lock-free and non-blocking where 2PC is not.

The cost is real and worth stating: a saga is only eventually consistent. Between a step completing and its compensation running, the partial effect is visible -- the reservation exists, the money may be held -- so other observers can see an intermediate state 2PC's locks would have hidden. And every step needs a compensating action that is actually possible: you can cancel a reservation or refund a charge, but some effects (an email sent, a missile launched) cannot be truly undone, only mitigated. Sagas fit where steps are individually committable and reversible; 2PC fits where you need strict atomicity and can tolerate locking.

The rule: run a multi-step distributed transaction as a saga -- commit each step immediately and, on failure, undo the completed steps by running their compensating actions in reverse order -- rather than holding locks across all steps (2PC), because compensation restores consistency without blocking, at the cost of eventual (not immediate) consistency and a requirement that every step have a real compensating action.

On this fixture the trip books reserve_flight, reserve_hotel, then charge_card fails. The naive pipeline leaves the flight and hotel reserved (2 orphaned effects); the saga runs cancel_hotel then cancel_flight, leaving no orphans. This computes both.

  --run        the forward execution: which steps complete and where it fails
  --compensate the compensating actions the saga runs (reverse order) vs the orphans the naive pipeline leaves
  --check      the naive pipeline leaves partial effects; the saga compensates the completed steps in reverse and leaves none

steps and fails_at are the fixture; the completed set, orphans, and compensation sequence are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "saga.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def completed_steps(steps, fails_at):
    """The steps that ran successfully -- those before the failing one."""
    out = []
    for s in steps:
        if s["name"] == fails_at:
            break
        out.append(s)
    return out


def naive_orphans(steps, fails_at):
    """Naive pipeline: stops at failure, leaving the completed steps' effects in place."""
    return [s["name"] for s in completed_steps(steps, fails_at)]


def saga_compensations(steps, fails_at):
    """Saga: compensating actions for the completed steps, in reverse order."""
    return [s["compensate"] for s in reversed(completed_steps(steps, fails_at))]


# ----------------------------------------------------------------- printing

def run_view(data):
    steps, fails = data["steps"], data["fails_at"]
    print("RUN — forward execution of the saga")
    print("-" * 54)
    for s in steps:
        status = "FAILS" if s["name"] == fails else ("done" if s in completed_steps(steps, fails) else "not reached")
        print("  %-16s %s" % (s["name"], status))
    print("-" * 54)
    print("  completed before failure: %s" % [s["name"] for s in completed_steps(steps, fails)])


def compensate_view(data):
    steps, fails = data["steps"], data["fails_at"]
    print("COMPENSATE — naive orphans vs saga compensation")
    print("-" * 60)
    print("  naive (no undo): leaves %d orphaned effect(s): %s" % (len(naive_orphans(steps, fails)), naive_orphans(steps, fails)))
    print("  saga compensations (reverse order): %s" % saga_compensations(steps, fails))
    print("  saga orphaned effects after compensation: 0")
    print("-" * 60)
    print("  the failing step (%s) is not compensated -- it never completed" % fails)


def check(data):
    print("SELF-TEST — the naive pipeline leaves partial effects; the saga compensates the completed steps in reverse and leaves none")
    print("-" * 124)
    steps, fails = data["steps"], data["fails_at"]
    completed = completed_steps(steps, fails)
    comps = saga_compensations(steps, fails)

    fails_partway = 0 < len(completed) < len(steps)
    print("  the transaction fails after some steps completed = %s (%d of %d done)" % (fails_partway, len(completed), len(steps)))

    naive_leaves_partial = len(naive_orphans(steps, fails)) > 0
    print("  the naive pipeline leaves orphaned effects = %s (%s)" % (naive_leaves_partial, naive_orphans(steps, fails)))

    saga_compensates_all_completed = len(comps) == len(completed)
    print("  the saga compensates exactly the completed steps = %s (%d compensations for %d completed)" % (saga_compensates_all_completed, len(comps), len(completed)))

    reverse_order = comps == [s["compensate"] for s in reversed(completed)]
    print("  the compensations run in reverse order = %s (%s)" % (reverse_order, comps))

    failing_step_not_compensated = next(s["compensate"] for s in steps if s["name"] == fails) not in comps
    print("  the failing step is NOT compensated (it never completed) = %s" % failing_step_not_compensated)

    saga_no_orphans = set(naive_orphans(steps, fails)) == {s["name"] for s in completed} and len(comps) == len(naive_orphans(steps, fails))
    print("  the saga undoes every effect the naive pipeline would orphan = %s" % saga_no_orphans)

    ok = (fails_partway and naive_leaves_partial and saga_compensates_all_completed and reverse_order
          and failing_step_not_compensated and saga_no_orphans)
    print("-" * 124)
    print("SELF-TEST %s  fails_partway=%s  naive_leaves_partial=%s  saga_compensates_all_completed=%s  reverse_order=%s  failing_step_not_compensated=%s  saga_no_orphans=%s"
          % ("PASS" if ok else "FAIL", fails_partway, naive_leaves_partial, saga_compensates_all_completed, reverse_order, failing_step_not_compensated, saga_no_orphans))
    return ok


def main():
    p = argparse.ArgumentParser(description="Saga pattern: run a multi-step distributed transaction as a saga -- commit each step immediately and, on failure, undo the completed steps by running their compensating actions in reverse order -- rather than holding locks across all steps (2PC), because compensation restores consistency without blocking, at the cost of eventual (not immediate) consistency and a requirement that every step have a real compensating action.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--compensate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%d  fails_at=%s  file=%s  (the steps and failure point are a fixture)"
          % (len(data["steps"]), data["fails_at"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.compensate:
        compensate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
