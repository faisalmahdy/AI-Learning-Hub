"""Shed low-priority requests first under overload -- admitting in arrival order spends scarce capacity on best-effort traffic and drops the requests that matter.

When demand exceeds what a server can handle, some requests will not be served -- that is arithmetic, not a bug. The question a server actually gets to decide is not whether to drop requests but WHICH ones. The default answer, made by doing nothing special, is to admit requests in the order they arrive until capacity is full and turn away the rest. That is first-come-first-served, and under overload it is indiscriminate: it fills the last scarce slots with whatever happened to arrive early, which includes best-effort traffic -- a prefetch, an analytics beacon, a retry of something already abandoned -- while a high-value request that arrived a moment later gets turned away. The server stayed busy; it just spent its scarcest resource on the wrong work.

LOAD SHEDDING makes the choice deliberately: when the server is over capacity, it drops LOW-priority requests first, reserving the limited slots for high-priority ones. A checkout, a payment, a health probe that keeps the instance in the load balancer -- these are served; a prefetch or a background sync is shed with a fast rejection so it does not consume a slot. Shedding does not create capacity and it does not serve more requests than first-come-first-served -- both serve exactly the capacity. It spends that same capacity on the requests that matter, so the requests you cannot afford to lose survive the overload and the ones you can afford to lose are the ones dropped.

The rejection has to be CHEAP to be worth it -- a shed request should be turned away with a quick 'try later' (an HTTP 503 with a Retry-After, say) before it does expensive work, so shedding actually frees capacity rather than just relabeling a slow failure. And priority has to reflect real value, not a guess, or you shed the wrong thing. But the core move is simple and it is the difference between an overload that degrades gracefully -- best-effort traffic thins out, critical paths keep working -- and one where the important requests are dropped alongside the unimportant ones purely by arrival timing.

The rule: under overload, shed low-priority requests first with a cheap rejection, reserving scarce capacity for high-priority requests, rather than admitting requests in arrival order until full, because first-come-first-served spends the last slots on whatever arrived early -- including best-effort traffic -- and drops high-value requests that happened to arrive later.

On this burst of 7 requests for 4 slots, arrival-order admission serves 2 of the 3 high-priority requests and drops one high-priority request while serving a low-priority one. Shedding serves all 3 high-priority requests plus the earliest low-priority one, dropping only low-priority requests. Both serve exactly 4. This computes both.

  --burst     the incoming requests in arrival order with their priorities, and the capacity
  --admit     arrival-order admission vs load shedding: which requests each serves and drops
  --check     demand exceeds capacity; arrival order drops a high-priority request while shedding preserves all of them

capacity and requests are the fixture; every admission decision, served set, and dropped set is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "loadshed.json"

PRIORITY_RANK = {"high": 0, "low": 1}


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def admit_fifo(requests, capacity):
    """Arrival-order admission: fill the slots with the first `capacity` requests, drop the rest."""
    served = requests[:capacity]
    dropped = requests[capacity:]
    return served, dropped


def admit_shed(requests, capacity):
    """Load shedding: order by priority (high first), then arrival; serve the top `capacity`, shed the rest."""
    ordered = sorted(enumerate(requests), key=lambda p: (PRIORITY_RANK[p[1]["priority"]], p[0]))
    served_ids = {requests[i]["id"] for i, _ in ordered[:capacity]}
    served = [r for r in requests if r["id"] in served_ids]
    dropped = [r for r in requests if r["id"] not in served_ids]
    return served, dropped


def high_count(reqs):
    return sum(1 for r in reqs if r["priority"] == "high")


def ids(reqs):
    return [r["id"] for r in reqs]


# ----------------------------------------------------------------- printing

def burst_view(data):
    reqs, cap = data["requests"], data["capacity"]
    print("BURST — the incoming requests in arrival order (capacity %d)" % cap)
    print("-" * 52)
    print("  arrival: %s" % " ".join("%s(%s)" % (r["id"], r["priority"][0]) for r in reqs))
    print("-" * 52)
    print("  demand = %d requests ; capacity = %d ; must drop %d" % (len(reqs), cap, len(reqs) - cap))
    print("  high-priority in burst = %d ; low-priority = %d" % (high_count(reqs), len(reqs) - high_count(reqs)))


def admit_view(data):
    reqs, cap = data["requests"], data["capacity"]
    fs, fd = admit_fifo(reqs, cap)
    ss, sd = admit_shed(reqs, cap)
    print("ADMIT — arrival-order admission vs load shedding")
    print("-" * 60)
    print("  arrival order:  serves %s (high %d/%d)" % (ids(fs), high_count(fs), high_count(reqs)))
    print("                  drops  %s%s" % (ids(fd), "  <- dropped a HIGH-priority request!" if high_count(fd) else ""))
    print("  load shedding:  serves %s (high %d/%d)" % (ids(ss), high_count(ss), high_count(reqs)))
    print("                  drops  %s (all low-priority)" % ids(sd))
    print("-" * 60)
    print("  both serve exactly %d; shedding spends the same capacity on all %d high-priority requests" % (cap, high_count(reqs)))


def check(data):
    print("SELF-TEST — demand exceeds capacity; arrival order drops a high-priority request while shedding preserves all of them")
    print("-" * 124)
    reqs, cap = data["requests"], data["capacity"]
    fs, fd = admit_fifo(reqs, cap)
    ss, sd = admit_shed(reqs, cap)
    total_high = high_count(reqs)

    demand_exceeds_capacity = len(reqs) > cap
    print("  demand exceeds capacity (some requests must be dropped) = %s (%d > %d)" % (demand_exceeds_capacity, len(reqs), cap))

    naive_drops_high = high_count(fd) > 0
    print("  arrival-order admission drops a high-priority request = %s (dropped high: %s)" % (naive_drops_high, [r["id"] for r in fd if r["priority"] == "high"]))

    shedding_serves_all_high = high_count(ss) == total_high
    print("  load shedding serves ALL high-priority requests = %s (%d/%d)" % (shedding_serves_all_high, high_count(ss), total_high))

    shedding_drops_only_low = high_count(sd) == 0
    print("  load shedding drops only low-priority requests = %s" % shedding_drops_only_low)

    same_total_served = len(fs) == len(ss) == cap
    print("  both admission policies serve exactly the capacity = %s (%d == %d == %d)" % (same_total_served, len(fs), len(ss), cap))

    shedding_preserves_more_high = high_count(ss) > high_count(fs)
    print("  shedding preserves more high-priority than arrival order = %s (%d > %d)" % (shedding_preserves_more_high, high_count(ss), high_count(fs)))

    ok = demand_exceeds_capacity and naive_drops_high and shedding_serves_all_high and shedding_drops_only_low and same_total_served and shedding_preserves_more_high
    print("-" * 124)
    print("SELF-TEST %s  demand_exceeds_capacity=%s  naive_drops_high=%s  shedding_serves_all_high=%s  shedding_drops_only_low=%s  same_total_served=%s  shedding_preserves_more_high=%s"
          % ("PASS" if ok else "FAIL", demand_exceeds_capacity, naive_drops_high, shedding_serves_all_high, shedding_drops_only_low, same_total_served, shedding_preserves_more_high))
    return ok


def main():
    p = argparse.ArgumentParser(description="Load shedding: under overload, shed low-priority requests first with a cheap rejection, reserving scarce capacity for high-priority requests, rather than admitting requests in arrival order until full, because first-come-first-served spends the last slots on whatever arrived early -- including best-effort traffic -- and drops high-value requests that happened to arrive later.")
    p.add_argument("--burst", action="store_true")
    p.add_argument("--admit", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("capacity=%d  requests=%d  file=%s  (the capacity and request burst are a fixture)"
          % (data["capacity"], len(data["requests"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.burst:
        burst_view(data)
    elif args.admit:
        admit_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
