"""Partition the worker pool into bulkheads, or one hung dependency holds every worker and starves the rest.

Share a single pool of workers across every downstream dependency and you have coupled their fates. When
one dependency hangs -- stops responding, so its requests hold their worker and never release it -- those
stuck requests accumulate until they hold every worker in the pool. Now a request for a completely
healthy, unrelated dependency arrives and finds no free worker, and it is starved by a failure that had
nothing to do with it. One slow dependency has taken down the whole service. This is the same coupling a
ship avoids with bulkheads: a breach in one compartment floods only that compartment, not the hull.

The fix borrows the name. Partition the pool so each dependency gets a bounded share of workers, and a
request can only use workers from its own partition. When X hangs, it can hold at most its share; the rest
of the pool is untouched, and requests for healthy dependency Y draw from Y's own workers and keep being
served. You trade some peak throughput -- no single dependency can burst across the whole pool -- for
isolation: one dependency's failure is capped at its partition instead of consuming everything.

On this fixture a 6-worker pool serves a stream where X (hung) and Y (healthy) requests interleave. Shared,
the seven X requests hold all six workers and every one of the five Y requests is starved: 0 of 5 served.
Split into two bulkheads of 3, X saturates only its 3 workers and all 5 Y requests are served. This
computes the admissions both ways.

  --stream     the arrival stream and which dependency each request targets
  --serve      how many Y (healthy) requests get a worker, shared pool vs bulkheads
  --check      the shared pool starves the healthy dependency; bulkheads keep it served

The arrivals, pool size, and caps are the fixture; every admission is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "requests.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- admission, two pool designs

def serve_shared(arrivals, workers):
    """One shared pool. X requests hold a worker forever; Y releases at once. Returns per-request served flags."""
    held = 0  # workers held by hung X requests (never released within the run)
    log = []
    for dep in arrivals:
        free = workers - held
        if dep == "X":
            if free > 0:
                held += 1            # X grabs a worker and hangs onto it
                log.append((dep, True))
            else:
                log.append((dep, False))
        else:  # Y needs a momentarily-free worker, then releases it immediately
            log.append((dep, free > 0))
    return log


def serve_bulkhead(arrivals, caps):
    """Partitioned pool: each dependency draws only from its own share. X can't touch Y's workers."""
    held = {dep: 0 for dep in caps}
    log = []
    for dep in arrivals:
        free = caps[dep] - held[dep]
        if dep == "X":
            if free > 0:
                held[dep] += 1
                log.append((dep, True))
            else:
                log.append((dep, False))
        else:
            log.append((dep, free > 0))
    return log


def y_served(log):
    return sum(1 for dep, ok in log if dep == "Y" and ok)


def y_total(arrivals):
    return sum(1 for dep in arrivals if dep == "Y")


# ----------------------------------------------------------------- printing

def stream_view(data):
    arr = data["arrivals"]
    print("STREAM — %d requests; X is hung (holds its worker), Y is healthy (releases at once)" % len(arr))
    print("-" * 58)
    print("  arrivals: %s" % " ".join(arr))
    print("  %d X (hung) and %d Y (healthy); pool = %d workers." % (arr.count("X"), arr.count("Y"), data["workers"]))
    print("-" * 58)
    print("  the X requests never free their worker; the question is whether Y can still get one.")


def serve_view(data):
    arr, w, caps = data["arrivals"], data["workers"], data["bulkhead"]
    sh = serve_shared(arr, w)
    bh = serve_bulkhead(arr, caps)
    yt = y_total(arr)
    print("SERVE — healthy (Y) requests served, shared pool vs bulkheads")
    print("-" * 56)
    print("  shared pool (%d workers):        Y served %d of %d" % (w, y_served(sh), yt))
    print("  bulkheads (X:%d, Y:%d):           Y served %d of %d" % (caps["X"], caps["Y"], y_served(bh), yt))
    print("-" * 56)
    print("  shared: the hung X requests hold every worker; bulkheads: Y keeps its own.")


def check(data):
    print("SELF-TEST — the shared pool starves the healthy dependency; bulkheads keep it served")
    print("-" * 84)
    arr, w, caps = data["arrivals"], data["workers"], data["bulkhead"]
    yt = y_total(arr)

    sh = serve_shared(arr, w)
    bh = serve_bulkhead(arr, caps)

    shared_starves = y_served(sh) == 0
    print("  the shared pool starves every healthy Y request = %s (%d of %d served)" % (shared_starves, y_served(sh), yt))

    bulkhead_serves_all = y_served(bh) == yt
    print("  bulkheads serve every healthy Y request = %s (%d of %d served)" % (bulkhead_serves_all, y_served(bh), yt))

    caps_sum_to_pool = sum(caps.values()) == w
    print("  the bulkhead caps sum to the whole pool (no workers lost) = %s (%d = %d)"
          % (caps_sum_to_pool, sum(caps.values()), w))

    isolation = y_served(bh) > y_served(sh)
    print("  partitioning isolates X's failure from Y = %s (%d vs %d Y served)" % (isolation, y_served(bh), y_served(sh)))

    ok = shared_starves and bulkhead_serves_all and caps_sum_to_pool and isolation
    print("-" * 84)
    print("SELF-TEST %s  shared_starves=%s  bulkhead_serves_all=%s  caps_sum_to_pool=%s  isolation=%s"
          % ("PASS" if ok else "FAIL", shared_starves, bulkhead_serves_all, caps_sum_to_pool, isolation))
    return ok


def main():
    p = argparse.ArgumentParser(description="Partition the worker pool into bulkheads to isolate a hung dependency.")
    p.add_argument("--stream", action="store_true")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("arrivals=%d  workers=%d  bulkhead=%s  file=%s  (the arrivals and caps are a fixture)"
          % (len(data["arrivals"]), data["workers"], data["bulkhead"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stream:
        stream_view(data)
    elif args.serve:
        serve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
