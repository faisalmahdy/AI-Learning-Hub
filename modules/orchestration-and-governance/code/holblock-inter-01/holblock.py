"""Head-of-line blocking: a single strict FIFO lane lets one slow task at the head delay every unrelated task behind it -- reordering the same tasks on the same server leaves total work identical but collapses the mean completion time.

Put every task through one first-in-first-out queue served by one worker, and each task's fate is chained to whatever sits ahead of it. If a long task is at the head, the short tasks behind it cannot start until it finishes -- their completion times are dominated by a task they have nothing to do with. The item at the head of the line holds up the whole line, so a single slow request inflates the latency of every request queued behind it. This is head-of-line blocking, and it is why one big upload, one slow query, or one stuck message can wreck the latency of a stream of small fast ones sharing the lane.

The crucial thing to see is that this is not a capacity problem. The server is busy the entire time in either ordering; the total work and the throughput are exactly the same. What changes is who waits. Under FIFO, the many short tasks each pay the long task's duration as pure waiting. Serve the same tasks on the same single server in a different order -- shortest first, say -- and the short tasks finish immediately while only the one long task waits, and the mean completion time drops sharply. No extra worker, no less work: just a different order.

So HOL blocking is an ordering effect. A strict single FIFO lane couples the latency of unrelated tasks, and the cure is to stop forcing them through one head-blocked lane -- serve by size or class, give small tasks their own lane, or allow out-of-order service -- so that a quick task is never held hostage by a slow one ahead of it. (The classic examples are network switches, HTTP/1.1 pipelining, and TCP's in-order delivery, all of which suffer HOL blocking that later designs specifically remove.)

The rule: don't force unrelated tasks through one strict FIFO lane, because the task at the head blocks everything behind it -- head-of-line blocking -- inflating the latency of quick tasks stuck behind a slow one; reordering or separating lanes lowers the mean latency at no cost in total work or throughput.

On this fixture four tasks are queued with a slow one at the head. FIFO makes the three quick tasks each wait behind it; serving shortest-first frees them, cutting the mean completion time by more than half while the total work stays the same. This computes both.

  --complete   each task's completion time under FIFO order vs shortest-first, and the mean of each
  --waste      how much of each quick task's completion is pure waiting behind the head task
  --check      FIFO's head task blocks the queue and inflates mean completion; reordering lowers it at equal total work

service_times is the fixture; the completion times, means, and total work are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "holblock.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def completions(order):
    """Completion time of each task when served one at a time in the given order (all present at t=0)."""
    t = 0
    out = []
    for s in order:
        t += s
        out.append(t)
    return out


def mean(xs):
    return sum(xs) / len(xs)


# ----------------------------------------------------------------- printing

def complete_view(data):
    st = data["service_times"]
    fifo = st
    sjf = sorted(st)
    print("COMPLETE — completion time per task (one server, all queued at t=0)")
    print("-" * 60)
    print("  order          service times      completions          mean")
    print("  FIFO           %-18s %-20s %.2f" % (fifo, completions(fifo), mean(completions(fifo))))
    print("  shortest-first %-18s %-20s %.2f" % (sjf, completions(sjf), mean(completions(sjf))))
    print("-" * 60)
    print("  same server, same work -- only the order changed, and the mean latency with it")


def waste_view(data):
    st = data["service_times"]
    head = st[0]
    print("WASTE — for FIFO, how much of each task's completion is waiting behind the head (%d)" % head)
    print("-" * 58)
    comps = completions(st)
    print("  task   service   completion   own service   waited")
    for s, c in zip(st, comps):
        print("  %-5s  %-7d   %-10d   %-11d   %d" % ("t", s, c, s, c - s))
    print("-" * 58)
    print("  every task after the head inherits the head's duration as pure waiting")


def check(data):
    print("SELF-TEST — FIFO's head task blocks the queue and inflates mean completion; reordering lowers it at equal total work")
    print("-" * 120)
    st = data["service_times"]
    fifo = st
    sjf = sorted(st)

    cf, cs = completions(fifo), completions(sjf)
    mf, ms = mean(cf), mean(cs)

    head_is_slowest = st[0] == max(st)
    print("  the head task is the slowest in the queue = %s (%d)" % (head_is_slowest, st[0]))

    quick_tasks_blocked = all(c >= st[0] for c in cf[1:])
    print("  under FIFO every task after the head finishes no sooner than the head = %s" % quick_tasks_blocked)

    reorder_lowers_mean = ms < mf
    print("  shortest-first has a lower mean completion than FIFO = %s (%.2f < %.2f)" % (reorder_lowers_mean, ms, mf))

    same_total_work = sum(fifo) == sum(sjf) and max(cf) == max(cs)
    print("  total work and makespan are identical either way = %s (%d)" % (same_total_work, sum(fifo)))

    ordering_effect = reorder_lowers_mean and same_total_work
    print("  so the latency change is pure ordering, not capacity = %s" % ordering_effect)

    ok = (head_is_slowest and quick_tasks_blocked and reorder_lowers_mean
          and same_total_work and ordering_effect)
    print("-" * 120)
    print("SELF-TEST %s  head_is_slowest=%s  quick_tasks_blocked=%s  reorder_lowers_mean=%s  same_total_work=%s  ordering_effect=%s"
          % ("PASS" if ok else "FAIL", head_is_slowest, quick_tasks_blocked,
             reorder_lowers_mean, same_total_work, ordering_effect))
    return ok


def main():
    p = argparse.ArgumentParser(description="Head-of-line blocking: don't force unrelated tasks through one strict FIFO lane, because the task at the head blocks everything behind it, inflating the latency of quick tasks stuck behind a slow one; reordering or separating lanes lowers the mean latency at no cost in total work or throughput.")
    p.add_argument("--complete", action="store_true")
    p.add_argument("--waste", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("service_times=%s  file=%s  (the queued tasks are a fixture)"
          % (data["service_times"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.complete:
        complete_view(data)
    elif args.waste:
        waste_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
