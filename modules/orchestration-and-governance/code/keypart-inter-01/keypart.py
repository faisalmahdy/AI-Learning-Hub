"""Partition a work stream by a hash of the key, not round-robin, when events for the same key must be processed in order -- round-robin scatters one key's ordered events across parallel workers that finish at different times, so a later event can be applied before an earlier one and the final state is wrong, while nothing errors because every event ran exactly once.

The obvious way to spread a stream of work across a pool of workers is round-robin: send event 0 to worker 0, event 1 to worker 1, and so on. It balances load perfectly and it is right whenever the events are independent. It is wrong the moment two events for the same entity must be applied in order.

Consider an account balance and two operations that do not commute: a bonus that adds 100 and a promo that doubles. Bonus-then-double and double-then-bonus give different balances. The correct answer needs the account's operations applied in sequence order. Round-robin puts the account's first operation on one worker and its second on another; the two workers run concurrently with different backlogs, so the second operation can complete before the first, and the balance is computed in the wrong order. No error is raised -- both events were processed, once each -- the number is just wrong.

The fix is to make the assignment a function of the key: worker = hash(key) mod num_workers. Now every event for one account lands on the same worker, which processes its queue sequentially, so the account's operations stay in order. Different accounts hash to different workers, so the pool still runs in parallel across accounts -- ordering is preserved per key without giving up throughput across keys.

On this fixture two accounts each get a bonus (sequence 1) then a double (sequence 2), on a base of 50, so each correct balance is (50 + 100) * 2 = 300. Round-robin scatters each account's two operations across the two workers; the double, on the lighter worker, finishes first, so each account is computed double-then-bonus = (50 * 2) + 100 = 200 -- an undercount, in order-broken. Partitioning sends each account to one worker and both come out 300. This computes both.

  --roundrobin  balance load by event index: each account's operations split across workers and applied out of order, wrong balances
  --partition   assign by hash(key): each account's operations on one worker in sequence order, correct balances
  --check       round-robin reorders at least one key and gets the balance wrong, while partitioning preserves every key's order, gets every balance right, and still spreads keys across workers

base, num_workers, and the event stream are the fixture; every worker assignment, completion order, apply order, and final balance is computed. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "keypart.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def round_robin(events, n):
    """Balance by event index: event i goes to worker i mod n, regardless of its key."""
    queues = {w: [] for w in range(n)}
    for i, e in enumerate(events):
        queues[i % n].append(e)
    return queues


def partitioned(events, n):
    """Assign by key: every event for a key goes to worker hash(key) mod n, so one key stays on one worker."""
    queues = {w: [] for w in range(n)}
    for e in events:
        w = int(hashlib.sha256(e["key"].encode()).hexdigest(), 16) % n
        queues[w].append(e)
    return queues


def completion_order(queues):
    """Each event completes at its worker's cumulative cost; the global apply order is the order events complete."""
    timed = []
    for w, q in queues.items():
        t = 0
        for pos, e in enumerate(q):
            t += e["cost"]
            timed.append((t, w, pos, e))
    timed.sort(key=lambda x: (x[0], x[1], x[2]))
    return [e for (_t, _w, _pos, e) in timed]


def apply_op(val, e):
    """Apply one operation -- add a fixed amount, or double -- which do not commute."""
    if e["kind"] == "add":
        return val + e["by"]
    if e["kind"] == "double":
        return val * 2
    raise ValueError(e["kind"])


def final_states(apply_order, keys, base):
    """Fold the operations onto each key's balance in the given global apply order."""
    state = {k: base for k in keys}
    for e in apply_order:
        state[e["key"]] = apply_op(state[e["key"]], e)
    return state


def correct_states(events, keys, base):
    """The truth: apply each key's operations strictly in sequence order."""
    state = {k: base for k in keys}
    for k in keys:
        for e in sorted((e for e in events if e["key"] == k), key=lambda e: e["seq"]):
            state[k] = apply_op(state[k], e)
    return state


def applied_seqs(apply_order, key):
    """The sequence numbers of one key's events, in the order they were actually applied."""
    return [e["seq"] for e in apply_order if e["key"] == key]


# ----------------------------------------------------------------- printing

def _op(e):
    return "add %d" % e["by"] if e["kind"] == "add" else "double"


def roundrobin_view(data):
    events, n, keys, base = data["events"], data["num_workers"], data["keys"], data["base"]
    q = round_robin(events, n)
    order = completion_order(q)
    final = final_states(order, keys, base)
    correct = correct_states(events, keys, base)
    print("ROUND-ROBIN — balance by event index (i mod %d), ignoring the key" % n)
    print("-" * 64)
    for w in range(n):
        print("  worker %d queue: %s" % (w, ["%s#%d %s c%d" % (e["key"], e["seq"], _op(e), e["cost"]) for e in q[w]]))
    print("  global apply order: %s" % ["%s#%d" % (e["key"], e["seq"]) for e in order])
    for k in keys:
        print("  %s applied in seq order %s  ->  balance %d   (correct %d)" % (k, applied_seqs(order, k), final[k], correct[k]))
    print("-" * 64)
    print("  a key's ops split across workers; the double finishes first, so the balance is wrong")


def partition_view(data):
    events, n, keys, base = data["events"], data["num_workers"], data["keys"], data["base"]
    q = partitioned(events, n)
    order = completion_order(q)
    final = final_states(order, keys, base)
    correct = correct_states(events, keys, base)
    print("PARTITION — assign by hash(key) mod %d, so a key stays on one worker" % n)
    print("-" * 64)
    for w in range(n):
        print("  worker %d queue: %s" % (w, ["%s#%d %s c%d" % (e["key"], e["seq"], _op(e), e["cost"]) for e in q[w]]))
    print("  global apply order: %s" % ["%s#%d" % (e["key"], e["seq"]) for e in order])
    for k in keys:
        print("  %s applied in seq order %s  ->  balance %d   (correct %d)" % (k, applied_seqs(order, k), final[k], correct[k]))
    print("-" * 64)
    print("  each key's ops stay on one worker in sequence order, so every balance is correct")


def check(data):
    print("SELF-TEST — round-robin reorders at least one key and gets the balance wrong, while partitioning preserves every key's order, gets every balance right, and still spreads keys across workers")
    print("-" * 112)
    events, n, keys, base = data["events"], data["num_workers"], data["keys"], data["base"]
    correct = correct_states(events, keys, base)

    rr = round_robin(events, n)
    rr_order = completion_order(rr)
    rr_final = final_states(rr_order, keys, base)
    rr_reorders = any(applied_seqs(rr_order, k) != sorted(applied_seqs(rr_order, k)) for k in keys)
    print("  round-robin applies some key's ops out of sequence order = %s" % rr_reorders)
    rr_wrong = any(rr_final[k] != correct[k] for k in keys)
    print("  round-robin gets some balance wrong = %s (got %s, correct %s)" % (rr_wrong, {k: rr_final[k] for k in keys}, correct))

    pt = partitioned(events, n)
    pt_order = completion_order(pt)
    pt_final = final_states(pt_order, keys, base)
    pt_in_order = all(applied_seqs(pt_order, k) == sorted(applied_seqs(pt_order, k)) for k in keys)
    print("  partition applies every key's ops in sequence order = %s" % pt_in_order)
    pt_correct = all(pt_final[k] == correct[k] for k in keys)
    print("  partition gets every balance right = %s (got %s)" % (pt_correct, {k: pt_final[k] for k in keys}))
    pt_parallel = sum(1 for w in pt if pt[w]) > 1
    print("  partition still spreads keys across more than one worker = %s (%d workers busy)" % (pt_parallel, sum(1 for w in pt if pt[w])))

    ok = rr_reorders and rr_wrong and pt_in_order and pt_correct and pt_parallel
    print("-" * 112)
    print("SELF-TEST %s  rr_reorders=%s  rr_wrong=%s  pt_in_order=%s  pt_correct=%s  pt_parallel=%s"
          % ("PASS" if ok else "FAIL", rr_reorders, rr_wrong, pt_in_order, pt_correct, pt_parallel))
    return ok


def main():
    p = argparse.ArgumentParser(description="Key-based partitioning: when events for the same key must be applied in order, assign each event to a worker by hash(key) mod num_workers rather than round-robin by event index, because round-robin scatters one key's ordered events across concurrent workers that finish at different times, applying a later event before an earlier one and computing the wrong final state, while partitioning keeps each key on one worker in sequence order and still runs keys in parallel.")
    p.add_argument("--roundrobin", action="store_true")
    p.add_argument("--partition", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("base=%d  num_workers=%d  keys=%s  events=%d  file=%s"
          % (data["base"], data["num_workers"], data["keys"], len(data["events"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.roundrobin:
        roundrobin_view(data)
    elif args.partition:
        partition_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
