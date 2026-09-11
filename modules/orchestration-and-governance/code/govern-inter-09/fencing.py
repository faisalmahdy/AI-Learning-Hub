"""Fence writes with a monotonic epoch -- or a stale leader that lost its lease still corrupts state.

A cluster elects one leader to make changes. When the leader is partitioned away, its lease
expires and a new leader is elected -- but the old leader, cut off, does not know it has been
replaced, and it keeps issuing writes believing it is still in charge. Now two nodes think they
are the leader: split-brain. If the resource they write to accepts writes from anyone claiming
to be leader, the deposed leader's stale write lands after the new leader's, and it overwrites
correct state with the decisions of a leader that no longer exists.

A fencing token stops it. Each leadership term gets a monotonically increasing epoch, and every
write carries the epoch of the leader that issued it. The resource remembers the highest epoch
it has ever accepted and rejects any write with a lower one -- so once the new leader (epoch 2)
has written, the old leader's epoch-1 writes are refused, no matter that it still thinks it is
in charge. On this fixture the deposed leader A issues a late write after the new leader B has
committed; without fencing that stale write wins and the final state is A's, while with fencing
it is rejected and the state stays B's. This applies the same write sequence both ways and shows
the corruption prevented.

  --writes    the write sequence, each with its leader, epoch, and value
  --apply     the resulting state without fencing vs with fencing
  --check     without fencing the stale leader's write wins; fencing rejects it and keeps the true state

The write sequence and epochs are the fixture; every applied state is computed. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "writes.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- applying writes

def apply_without_fencing(writes):
    """Accept every write in arrival order -- a stale leader's write overwrites the current one's."""
    state, log = None, []
    for w in writes:
        state = w["value"]
        log.append((w["leader"], w["epoch"], "applied", state))
    return state, log


def apply_with_fencing(writes):
    """Reject any write whose epoch is below the highest epoch already accepted."""
    state, highest, log = None, 0, []
    for w in writes:
        if w["epoch"] < highest:
            log.append((w["leader"], w["epoch"], "REJECTED (stale)", state))
            continue
        highest = w["epoch"]
        state = w["value"]
        log.append((w["leader"], w["epoch"], "applied", state))
    return state, log


def current_leader(writes):
    """The leader of the highest epoch -- the one legitimately in charge."""
    return max(writes, key=lambda w: w["epoch"])["leader"]


# ----------------------------------------------------------------- printing

def writes_view(data):
    print("WRITES — the sequence, in arrival order (leader, epoch, value)")
    print("-" * 54)
    for w in data["writes"]:
        print("  %-8s epoch %d  value=%s" % (w["leader"], w["epoch"], w["value"]))
    print("-" * 54)
    print("  %s was deposed but keeps writing at its old epoch after %s took over."
          % (data["deposed"], current_leader(data["writes"])))


def apply_view(data):
    writes = data["writes"]
    s_no, log_no = apply_without_fencing(writes)
    s_fen, log_fen = apply_with_fencing(writes)
    print("APPLY — final state without fencing vs with fencing")
    print("-" * 60)
    print("  without fencing:")
    for leader, epoch, result, st in log_no:
        print("    %-8s e%d  %-18s -> %s" % (leader, epoch, result, st))
    print("    final state: %s" % s_no)
    print("  with fencing:")
    for leader, epoch, result, st in log_fen:
        print("    %-8s e%d  %-18s -> %s" % (leader, epoch, result, st))
    print("    final state: %s" % s_fen)
    print("-" * 60)
    print("  without fencing the deposed leader wins the last word; fencing refuses it.")


def check(data):
    print("SELF-TEST — without fencing the stale leader's write wins; fencing rejects it")
    print("-" * 66)
    writes = data["writes"]
    leader = current_leader(writes)
    max_epoch = max(w["epoch"] for w in writes)
    true_value = [w["value"] for w in writes if w["epoch"] == max_epoch][-1]  # last write of the current term

    s_no, _ = apply_without_fencing(writes)
    stale_wins = s_no != true_value
    print("  without fencing, the final state is NOT the current leader's = %s (state %s, should be %s)"
          % (stale_wins, s_no, true_value))

    s_fen, log_fen = apply_with_fencing(writes)
    fencing_correct = s_fen == true_value
    print("  with fencing, the final state IS the current leader's = %s (state %s)" % (fencing_correct, s_fen))

    rejected = [row for row in log_fen if "REJECTED" in row[2]]
    fencing_rejects_stale = len(rejected) > 0 and all(r[0] == data["deposed"] for r in rejected)
    print("  fencing rejects the deposed leader's stale writes = %s (%d rejected)"
          % (fencing_rejects_stale, len(rejected)))

    # epochs are monotonic across leadership changes: the new leader's epoch exceeds the old
    epochs_by_leader = {}
    for w in writes:
        epochs_by_leader.setdefault(w["leader"], set()).add(w["epoch"])
    monotonic = max(epochs_by_leader[leader]) > max(epochs_by_leader[data["deposed"]])
    print("  the current leader's epoch exceeds the deposed leader's = %s" % monotonic)

    ok = stale_wins and fencing_correct and fencing_rejects_stale and monotonic
    print("-" * 66)
    print("SELF-TEST %s  stale_wins=%s  fencing_correct=%s  fencing_rejects_stale=%s  monotonic=%s"
          % ("PASS" if ok else "FAIL", stale_wins, fencing_correct, fencing_rejects_stale, monotonic))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fence writes with a monotonic epoch to stop split-brain.")
    p.add_argument("--writes", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("writes=%d  deposed=%s  current=%s  file=%s  (the write sequence is a fixture)"
          % (len(data["writes"]), data["deposed"], current_leader(data["writes"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.writes:
        writes_view(data)
    elif args.apply:
        apply_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
