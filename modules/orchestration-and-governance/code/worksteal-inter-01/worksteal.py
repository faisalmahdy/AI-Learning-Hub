"""Balance uneven work by letting idle workers steal queued tasks, not by partitioning tasks across workers up front by count -- a static round-robin split ignores how long each task takes, so the worker that draws the heavy tasks runs long while the others finish early and sit idle.

The obvious way to hand N tasks to K workers is to deal them out like cards: task 0 to worker 0, task 1 to worker 1, and so on, round-robin. Each worker gets the same *number* of tasks, which feels fair. It is fair only if every task takes the same time. When task durations vary -- and they almost always do -- equal counts do not mean equal work: the worker that happens to draw the long tasks has a large total, and the makespan (the time until the last worker finishes) is set by that one unlucky worker while the others have long since gone idle.

Idle workers next to a backlog is pure waste. The fix is to stop deciding the whole assignment in advance. Give each worker a local queue, but when a worker empties its own queue it steals a task from the back of the most-loaded worker's queue instead of stopping. Work flows from busy workers to idle ones on demand, so no worker sits idle while another still has queued work, and the makespan drops toward the ideal -- the total work divided by the number of workers.

This is work stealing, the scheduling discipline behind Cilk, the Java fork/join pool, Go's goroutine scheduler, and Rust's Rayon. It is decentralized -- each worker makes its own steal decision when it runs dry, with no central dispatcher -- and it is self-balancing: the more skewed the task sizes, the more the stealing helps, because that is exactly when a static split strands the most work behind one worker.

On this fixture eight tasks whose durations are mostly small but with two large ones are given to two workers. Round-robin by count hands both large tasks to the same worker, so its total is 22 while the other's is 4 and the makespan is 22; work stealing rebalances to a makespan of 15 (loads 11 and 15) and cuts the idle time from 18 to 4 -- a large improvement toward the ideal of 13, though a coarse steal that grabs a big task late does not reach it exactly. This computes both.

  --schedule  each worker's total busy time and the makespan, static round-robin vs work stealing
  --idle      the idle time each schedule wastes -- workers finished while work remained elsewhere
  --check     static round-robin overloads one worker and leaves others idle; work stealing cuts the makespan and the idle time toward the ideal

durations, workers is the fixture; the assignments, per-worker loads, makespans, and idle times are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "worksteal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def static_loads(durations, workers):
    """Round-robin by count: task i goes to worker i % workers, decided up front."""
    loads = [0.0] * workers
    for i, d in enumerate(durations):
        loads[i % workers] += d
    return loads


def steal_finish(durations, workers):
    """Work stealing: each worker drains its own round-robin queue, then steals from the back of the most-loaded queue when it runs dry."""
    queues = [[durations[i] for i in range(len(durations)) if i % workers == w] for w in range(workers)]
    free = [0.0] * workers
    while any(queues):
        # the earliest-free worker takes the next task (its own, or a stolen one)
        w = min(range(workers), key=lambda j: free[j])
        if queues[w]:
            task = queues[w].pop(0)
        else:
            victim = max(range(workers), key=lambda j: len(queues[j]))
            task = queues[victim].pop()  # steal from the back
        free[w] += task
    return free


def makespan(loads):
    """The time the last worker finishes -- the schedule's real duration."""
    return max(loads)


def idle_time(loads):
    """Total worker-time wasted: every worker waits until the makespan, minus the work it did."""
    return makespan(loads) * len(loads) - sum(loads)


# ----------------------------------------------------------------- printing

def schedule_view(data):
    durations, workers = data["durations"], data["workers"]
    s = static_loads(durations, workers)
    w = steal_finish(durations, workers)
    ideal = sum(durations) / workers
    print("SCHEDULE — %d tasks across %d workers (total work %g, ideal makespan %g)"
          % (len(durations), workers, sum(durations), ideal))
    print("-" * 56)
    print("  static round-robin loads : %s   makespan %g" % (["%g" % x for x in s], makespan(s)))
    print("  work-stealing loads      : %s   makespan %g" % (["%g" % x for x in w], makespan(w)))
    print("-" * 56)
    print("  same tasks, same total work; stealing moves work off the overloaded worker")


def idle_view(data):
    durations, workers = data["durations"], data["workers"]
    s = static_loads(durations, workers)
    w = steal_finish(durations, workers)
    print("IDLE — worker-time wasted while work remained elsewhere")
    print("-" * 56)
    print("  static round-robin idle : %g" % idle_time(s))
    print("  work-stealing idle      : %g" % idle_time(w))
    print("-" * 56)
    print("  static strands work behind one worker; stealing moves it to the idle ones")


def check(data):
    print("SELF-TEST — static round-robin overloads one worker and leaves others idle; work stealing cuts the makespan and the idle time toward the ideal")
    print("-" * 112)
    durations, workers = data["durations"], data["workers"]
    ideal = sum(durations) / workers
    # list-scheduling upper bound: a greedy/stealing schedule finishes within max_task*(1-1/K) of the ideal
    bound = ideal + max(durations) * (1 - 1.0 / workers)

    s = static_loads(durations, workers)
    w = steal_finish(durations, workers)

    same_total_work = abs(sum(s) - sum(durations)) < 1e-9 and abs(sum(w) - sum(durations)) < 1e-9
    print("  both schedules do the same total work = %s (%g)" % (same_total_work, sum(durations)))

    static_exceeds_ideal = makespan(s) > ideal
    print("  static makespan far exceeds the ideal = %s (%g > %g)" % (static_exceeds_ideal, makespan(s), ideal))

    steal_beats_static = makespan(w) < makespan(s)
    print("  work-stealing finishes sooner than static = %s (%g < %g)" % (steal_beats_static, makespan(w), makespan(s)))

    steal_within_bound = makespan(w) <= bound + 1e-9
    print("  work-stealing stays within the list-scheduling bound = %s (%g <= %g)" % (steal_within_bound, makespan(w), bound))

    static_wastes_idle = idle_time(s) > idle_time(w)
    print("  static wastes more idle worker-time = %s (%g > %g)" % (static_wastes_idle, idle_time(s), idle_time(w)))

    ok = (same_total_work and static_exceeds_ideal and steal_beats_static
          and steal_within_bound and static_wastes_idle)
    print("-" * 112)
    print("SELF-TEST %s  same_total_work=%s  static_exceeds_ideal=%s  steal_beats_static=%s  steal_within_bound=%s  static_wastes_idle=%s"
          % ("PASS" if ok else "FAIL", same_total_work, static_exceeds_ideal, steal_beats_static,
             steal_within_bound, static_wastes_idle))
    return ok


def main():
    p = argparse.ArgumentParser(description="Work stealing: balance uneven work by letting idle workers steal queued tasks, not by partitioning tasks across workers up front by count, because a static round-robin split ignores how long each task takes, so the worker that draws the heavy tasks runs long while the others finish early and sit idle.")
    p.add_argument("--schedule", action="store_true")
    p.add_argument("--idle", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("durations=%s  workers=%d  file=%s  (these are a fixture)"
          % (data["durations"], data["workers"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.schedule:
        schedule_view(data)
    elif args.idle:
        idle_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
