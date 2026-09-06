"""A participant that voted yes but hasn't heard the decision cannot resolve alone -- two-phase commit blocks.

Two-phase commit makes a set of participants agree to commit-or-abort atomically. Phase one: the coordinator asks
everyone to PREPARE, and each participant that can commit votes YES and enters the prepared state -- it has
promised it will commit if asked, and to keep that promise it holds its locks and may NOT unilaterally abort.
Phase two: once all votes are in, the coordinator logs the decision and tells everyone, and they commit. The
protocol is correct: it never commits on one node and aborts on another. But it has a fatal operational property.

Between voting YES and hearing the decision, a participant is in a WINDOW OF UNCERTAINTY. It cannot abort -- it
promised it could commit, and the coordinator may have already told the others to commit. It cannot commit -- it
does not know whether every other participant also voted yes. Its only legal move is to wait for the coordinator.
So if the coordinator crashes while any participant is in that window, that participant BLOCKS: it sits holding
its locks, unable to move, until the coordinator comes back. The decision is not lost -- a recovered coordinator
resolves it -- but until recovery the participant is frozen, and so is everything waiting on its locks. This is
why two-phase commit is called a BLOCKING protocol, and why sagas and consensus-based commit exist.

On this fixture two participants vote yes at ticks 1 and 2; the coordinator logs COMMIT at tick 3 and delivers it
at ticks 4 and 5. A coordinator crash at tick 0 blocks nobody (safe abort). A crash at tick 2 blocks both -- both
are prepared and undecided. A crash at tick 4 still blocks p2, which has not yet heard. Only after tick 5 is a
crash harmless. This computes the blocked set at each crash time.

  --timeline   each participant's window of uncertainty (vote-yes tick to decision-delivered tick)
  --crash      for each candidate crash time, which participants block holding their locks
  --check      a crash before any vote is safe; a crash inside the window blocks; after all deliveries it is safe

The timeline is the fixture; every blocked set is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "twopc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def window(data, p):
    """A participant's uncertainty window [voted YES, decision delivered): prepared, holding locks, undecided."""
    return data["votes_yes"][p], data["decision_delivered"][p]


def blocked_at(data, t):
    """Participants that block if the coordinator crashes at time t: those inside their uncertainty window."""
    out = []
    for p in data["participants"]:
        lo, hi = window(data, p)
        if lo <= t < hi:
            out.append(p)
    return out


# ----------------------------------------------------------------- printing

def timeline_view(data):
    print("TIMELINE — each participant's window of uncertainty (prepared, holding locks, undecided)")
    print("-" * 66)
    print("  prepare sent at tick %d; coordinator logs COMMIT at tick %d" % (data["prepare_sent"], data["decision_logged"]))
    for p in data["participants"]:
        lo, hi = window(data, p)
        print("  %-4s votes YES at %d, learns decision at %d  ->  uncertain during [%d, %d)" % (p, lo, hi, lo, hi))
    print("-" * 66)
    print("  inside its window a participant can neither abort (it promised) nor commit (it doesn't know).")


def crash_view(data):
    print("CRASH — coordinator crashes at each time; who blocks holding locks")
    print("-" * 66)
    for t in data["crash_times"]:
        b = blocked_at(data, t)
        verdict = "SAFE (no one prepared-and-undecided)" if not b else "BLOCKS %s" % b
        print("  crash at tick %d  ->  %s" % (t, verdict))
    print("-" * 66)
    print("  a crash while any participant is mid-window freezes it until the coordinator recovers.")


def check(data):
    print("SELF-TEST — a crash before any vote is safe; a crash inside the window blocks; after all deliveries it is safe")
    print("-" * 112)
    parts = data["participants"]

    crash_before_prepare_safe = blocked_at(data, data["prepare_sent"]) == []
    print("  a crash at prepare-time (no yes votes yet) blocks no one = %s" % crash_before_prepare_safe)

    peak = max(data["votes_yes"].values())
    all_prepared_block = set(blocked_at(data, peak)) == set(parts)
    print("  a crash once all have voted yes blocks every participant = %s (%s)" % (all_prepared_block, blocked_at(data, peak)))

    last_delivery = max(data["decision_delivered"].values())
    crash_after_delivery_safe = blocked_at(data, last_delivery) == []
    print("  a crash after every participant has the decision blocks no one = %s" % crash_after_delivery_safe)

    p_last = max(parts, key=lambda p: window(data, p)[1])
    lo, hi = window(data, p_last)
    still_blocks_after_decision_logged = data["decision_logged"] < hi and p_last in blocked_at(data, data["decision_logged"])
    print("  a crash even AFTER the decision is logged still blocks a participant that hasn't heard = %s (%s uncertain until %d)" % (still_blocks_after_decision_logged, p_last, hi))

    window_is_vote_to_delivery = window(data, p_last) == (data["votes_yes"][p_last], data["decision_delivered"][p_last])
    print("  the window runs exactly from voting yes to learning the decision = %s %s" % (window_is_vote_to_delivery, window(data, p_last)))

    ok = crash_before_prepare_safe and all_prepared_block and crash_after_delivery_safe and still_blocks_after_decision_logged and window_is_vote_to_delivery
    print("-" * 112)
    print("SELF-TEST %s  crash_before_prepare_safe=%s  all_prepared_block=%s  crash_after_delivery_safe=%s  still_blocks_after_decision_logged=%s  window_is_vote_to_delivery=%s"
          % ("PASS" if ok else "FAIL", crash_before_prepare_safe, all_prepared_block, crash_after_delivery_safe, still_blocks_after_decision_logged, window_is_vote_to_delivery))
    return ok


def main():
    p = argparse.ArgumentParser(description="Two-phase commit blocks: a participant in its window of uncertainty cannot resolve alone if the coordinator crashes.")
    p.add_argument("--timeline", action="store_true")
    p.add_argument("--crash", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("participants=%s  votes_yes=%s  decision_logged=%d  delivered=%s  file=%s  (the timeline is a fixture)"
          % (data["participants"], data["votes_yes"], data["decision_logged"], data["decision_delivered"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.timeline:
        timeline_view(data)
    elif args.crash:
        crash_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
