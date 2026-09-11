"""Coalesce concurrent misses with single-flight, or a hot key's expiry stampedes the origin.

A cache serves a hot key thousands of times a second from memory, and the origin behind it (a database, an
API, an expensive computation) never notices. Then the key expires. In the window between the expiry and
the first refill, every arriving request finds the cache empty and does the obvious thing: fetch from the
origin and repopulate. If the refill takes any real time, dozens or hundreds of requests arrive during
that window and each launches its own origin fetch -- so a key that cost the origin one lookup per TTL
suddenly costs it one lookup per request, all at once. That synchronized pile-on is a cache stampede (a
thundering herd), and it routinely takes down the very origin the cache was protecting, right when traffic
is highest.

Single-flight fixes it by making the first miss the only miss. When a request finds the key empty, it
marks the key in-flight and starts one origin fetch; every other request that arrives while that fetch is
in flight does not start its own -- it attaches to the in-flight fetch and waits for the same result. One
origin call serves the whole herd, and every waiter still gets the value (it is not dropped, just made to
wait for the shared fetch). The origin sees one lookup per refill instead of one per request, no matter
how large the herd.

On this fixture eight requests hit an expired key while a refill takes 5 time units: six arrive together
at the instant of expiry and two more during the refill. Without single-flight, seven of the eight miss
and each hits the origin -- seven origin fetches for one value. With single-flight, the first request
fetches and the other seven attach to it -- one origin fetch, and all eight requests are served. This
computes both.

  --trace      each request: hit, miss-and-fetch, or coalesced-wait, under each policy
  --load       origin fetches and requests served, naive vs single-flight
  --check      naive stampedes the origin with one fetch per miss; single-flight collapses them to one

The arrivals and refill time are the fixture; every fetch is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "requests.json"


def simulate(arrivals, refill, single_flight):
    """Walk requests in arrival order over a cold key; return each request's outcome."""
    completed = []          # completion times of fetches that have finished populating the cache
    inflight = []           # (start, end) of a fetch currently running (single-flight only)
    outcomes = []
    for t in sorted(arrivals):
        if any(c <= t for c in completed):
            outcomes.append({"t": t, "outcome": "hit"})
        elif single_flight and any(s <= t < e for s, e in inflight):
            outcomes.append({"t": t, "outcome": "wait"})     # attached to the in-flight fetch
        else:
            end = t + refill
            completed.append(end)
            inflight.append((t, end))
            outcomes.append({"t": t, "outcome": "fetch"})
    return outcomes


def fetches(outcomes):
    return sum(1 for o in outcomes if o["outcome"] == "fetch")


def served(outcomes):
    return sum(1 for o in outcomes if o["outcome"] in ("hit", "wait", "fetch"))


# ----------------------------------------------------------------- printing

def trace_view(data):
    arr, refill = data["arrivals"], data["refill"]
    for name, sf in (("NAIVE (no coalescing)", False), ("SINGLE-FLIGHT", True)):
        outs = simulate(arr, refill, sf)
        print("%s   (refill %d)" % (name, refill))
        print("-" * 52)
        label = {"hit": "HIT (cached)", "fetch": "MISS -> origin fetch", "wait": "wait for in-flight fetch"}
        for o in outs:
            print("  t=%d   %s" % (o["t"], label[o["outcome"]]))
        print("  origin fetches: %d   requests served: %d" % (fetches(outs), served(outs)))
        print("")


def load_view(data):
    arr, refill = data["arrivals"], data["refill"]
    naive, sf = simulate(arr, refill, False), simulate(arr, refill, True)
    print("LOAD — origin fetches and requests served per policy (%d requests)" % len(arr))
    print("-" * 54)
    print("  policy          origin fetches   requests served")
    print("  naive           %14d   %15d" % (fetches(naive), served(naive)))
    print("  single-flight   %14d   %15d" % (fetches(sf), served(sf)))
    print("-" * 54)
    print("  single-flight collapses the herd's fetches to one, serving everyone.")


def check(data):
    print("SELF-TEST — naive stampedes the origin with one fetch per miss; single-flight collapses them to one")
    print("-" * 100)
    arr, refill = data["arrivals"], data["refill"]
    naive, sf = simulate(arr, refill, False), simulate(arr, refill, True)

    naive_stampedes = fetches(naive) > 1
    print("  naive fires more than one origin fetch for one value = %s (%d fetches)" % (naive_stampedes, fetches(naive)))

    singleflight_one = fetches(sf) == 1
    print("  single-flight fires exactly one origin fetch = %s (%d fetch)" % (singleflight_one, fetches(sf)))

    singleflight_reduces = fetches(sf) < fetches(naive)
    print("  single-flight cuts origin load below naive = %s (%d vs %d)" % (singleflight_reduces, fetches(sf), fetches(naive)))

    all_served = served(sf) == len(arr) and served(naive) == len(arr)
    print("  every request is served under both (waiters are not dropped) = %s (%d/%d)" % (all_served, served(sf), len(arr)))

    coalesced = sum(1 for o in sf if o["outcome"] == "wait")
    herd_coalesced = coalesced == fetches(naive) - 1
    print("  the requests naive would have stampeded are coalesced = %s (%d waited)" % (herd_coalesced, coalesced))

    ok = naive_stampedes and singleflight_one and singleflight_reduces and all_served and herd_coalesced
    print("-" * 100)
    print("SELF-TEST %s  naive_stampedes=%s  singleflight_one=%s  singleflight_reduces=%s  all_served=%s  herd_coalesced=%s"
          % ("PASS" if ok else "FAIL", naive_stampedes, singleflight_one, singleflight_reduces, all_served, herd_coalesced))
    return ok


def main():
    p = argparse.ArgumentParser(description="Coalesce concurrent cache misses with single-flight to prevent a stampede.")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--load", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    print("requests=%d  refill=%d  file=%s  (the arrivals and refill time are a fixture)"
          % (len(data["arrivals"]), data["refill"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trace:
        trace_view(data)
    elif args.load:
        load_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
