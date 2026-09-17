"""Break the symmetry of retries to escape livelock -- two workers that grab-fail-release in lockstep repeat forever and complete nothing, even though neither is blocked, so a deadlock detector finds nothing to fix.

Two transactions each need the same two resources in opposite order: transaction 0 takes A then B, transaction 1 takes B then A. Each round both succeed at their first resource (they want different ones), then each fails at its second because the other is holding it, so each politely releases what it holds and tries again. Everyone is busy, cooperative, and making no progress.

This is not deadlock, and the distinction is the whole point. In deadlock each transaction would hold its first resource and wait for the second forever -- a cycle in the wait-for graph that a detector can find and break by aborting a victim. Here nothing waits and nothing is held between rounds: the resources are released every single round, so there is no cycle, no blocked transaction, nothing for a deadlock detector to abort. The system passes every liveness check that looks for stuck processes while accomplishing zero work.

The cause is symmetry. If both transactions retry on the same schedule, each round is a bit-for-bit repeat of the last -- same grabs, same conflict, same release -- so the loop is a fixed point that never breaks. The cure is to make the retries asymmetric so the tie is broken exactly once: on a conflict, have the two back off by different amounts (here, by transaction id), so one comes back to retry while the other is still waiting, finds both resources free, completes, and clears the way. Randomized backoff does the same statistically -- it makes an exact repeat of the schedule vanishingly unlikely -- which is why real retry loops randomize.

On this fixture the lockstep policy runs the full round budget and completes zero transactions, with the resources free at every round boundary (livelock, not deadlock); the asymmetric policy completes both transactions in a few rounds. This computes both.

  --lockstep    both retry on the same schedule: the per-round state and the completion count
  --asymmetric  the two back off by different amounts: the per-round state and the completion count
  --check       lockstep makes no progress yet never deadlocks (resources always freed); asymmetry breaks the tie and both complete

resource_order, max_rounds, and the backoff flag are the fixture; the completions and per-round holdings under each policy are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "livelock.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def backoff(t, asymmetric):
    """The retry delay after a conflict. Lockstep: the same (0) for everyone -- the tie never breaks.
    Asymmetric: an id-dependent delay, so the two transactions retry on different rounds."""
    return t if asymmetric else 0


def simulate(order, max_rounds, asymmetric):
    """Run the two transactions. Each round: all active grab their first resource, then simultaneously
    try their second against a snapshot; a transaction that would get both commits and releases,
    one that conflicts releases its first and backs off. Resources are free between rounds."""
    txns = sorted(int(t) for t in order)
    completed = []
    next_round = {t: 0 for t in txns}
    log = []                                   # (round, holdings-at-round-end, completed-this-round)
    for r in range(max_rounds):
        if len(completed) == len(txns):
            break
        active = [t for t in txns if t not in completed and next_round[t] <= r]
        held = {}                              # resource -> transaction
        # phase 1: each active transaction grabs its first resource if free
        first = {}
        for t in active:
            res0 = order[str(t)][0]
            if res0 not in held:
                held[res0] = t
                first[t] = res0
        # phase 2: decide all outcomes against the post-phase-1 snapshot (simultaneous)
        snapshot = dict(held)                  # what each grabbed before anyone releases
        done_now = []
        for t in active:
            if t not in first:
                continue
            res1 = order[str(t)][1]
            if res1 not in snapshot:           # second resource was free -> commit, then release both
                completed.append(t)
                done_now.append(t)
                del held[first[t]]
            else:                              # conflict: release the first, retry after a backoff
                del held[first[t]]
                next_round[t] = r + 1 + backoff(t, asymmetric)
        log.append((r, list(active), snapshot, list(done_now), dict(held)))
    return {"completed": completed, "rounds_used": len(log), "log": log}


# ----------------------------------------------------------------- printing

def _run_view(title, res, txns, note):
    print(title)
    print("-" * 68)
    print("  round   grabbed (mid-round)     completed   held at round end")
    for r, active, snap, done, endheld in res["log"]:
        snap_s = ", ".join("%s->T%d" % (k, v) for k, v in sorted(snap.items())) or "(none)"
        end_s = ", ".join("%s->T%d" % (k, v) for k, v in sorted(endheld.items())) or "(all free)"
        print("  %-5d   %-22s  %-9s   %s" % (r, snap_s, [("T%d" % t) for t in done], end_s))
    print("-" * 68)
    print("  completed %d of %d transactions in %d rounds -- %s" % (len(res["completed"]), txns, res["rounds_used"], note))


def lockstep_view(data):
    res = simulate(data["resource_order"], data["max_rounds"], asymmetric=False)
    _run_view("LOCKSTEP — both retry on the same schedule", res, len(data["resource_order"]),
              "no progress; resources freed every round (livelock, not deadlock)")


def asymmetric_view(data):
    res = simulate(data["resource_order"], data["max_rounds"], asymmetric=True)
    _run_view("ASYMMETRIC — back off by different amounts (by id)", res, len(data["resource_order"]),
              "the tie is broken and both complete")


def check(data):
    print("SELF-TEST — lockstep makes no progress yet never deadlocks (resources always freed); asymmetry breaks the tie and both complete")
    print("-" * 112)
    order, mr = data["resource_order"], data["max_rounds"]
    n = len(order)

    lock = simulate(order, mr, asymmetric=False)
    asym = simulate(order, mr, asymmetric=True)

    lockstep_no_progress = len(lock["completed"]) == 0
    print("  lockstep completes zero transactions in %d rounds = %s" % (mr, lockstep_no_progress))

    lockstep_stays_active = all(len(active) == n for _, active, _, _, _ in lock["log"])
    print("  lockstep keeps both transactions active every round (not blocked) = %s" % lockstep_stays_active)

    lockstep_never_deadlocks = all(len(endheld) == 0 for _, _, _, _, endheld in lock["log"])
    print("  lockstep holds no resources between rounds (no cycle to detect) = %s" % lockstep_never_deadlocks)

    asymmetric_all_complete = len(asym["completed"]) == n
    print("  asymmetric completes all %d transactions = %s (%s)" % (n, asymmetric_all_complete, ["T%d" % t for t in asym["completed"]]))

    asymmetric_faster = asym["rounds_used"] < mr
    print("  asymmetric finishes within the budget = %s (%d rounds)" % (asymmetric_faster, asym["rounds_used"]))

    ok = (lockstep_no_progress and lockstep_stays_active and lockstep_never_deadlocks
          and asymmetric_all_complete and asymmetric_faster)
    print("-" * 112)
    print("SELF-TEST %s  lockstep_no_progress=%s  lockstep_stays_active=%s  lockstep_never_deadlocks=%s  asymmetric_all_complete=%s  asymmetric_faster=%s"
          % ("PASS" if ok else "FAIL", lockstep_no_progress, lockstep_stays_active, lockstep_never_deadlocks,
             asymmetric_all_complete, asymmetric_faster))
    return ok


def main():
    p = argparse.ArgumentParser(description="Livelock: break the symmetry of retries, because two workers that grab-fail-release in lockstep repeat forever and complete nothing though neither is blocked -- a deadlock detector finds nothing to fix because the resources are freed every round.")
    p.add_argument("--lockstep", action="store_true")
    p.add_argument("--asymmetric", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("resource_order=%s  max_rounds=%d  file=%s  (these are a fixture)"
          % (data["resource_order"], data["max_rounds"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.lockstep:
        lockstep_view(data)
    elif args.asymmetric:
        asymmetric_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
