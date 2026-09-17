"""Match each parallel tool result back to its call by the call's id, not by the order results arrive -- out-of-order completion pairs the wrong result with the wrong call, and the model reasons on scrambled data.

When a model emits several tool calls in one turn, a good harness runs them in parallel for speed. But parallel calls finish in an order set by how long each takes, which has nothing to do with the order they were issued: a fast lookup returns before a slow one that was requested earlier. The harness then has to give the results back to the model, and here is the fork. It can pair them by arrival -- take the results in completion order and drop them onto the calls in issue order, slot by slot -- or it can pair them by identity, matching each result to the specific call it answers.

Pairing by arrival is the bug, and it is a quiet one. Because completion order differs from issue order, the results land on the wrong calls: the weather call is told it returned a stock price, the stock call is told it returned the time. Nothing errors -- every call has a result, the shapes are fine -- but each result is attributed to the wrong question. The model reads its context, sees 'get_weather returned stock:150', and reasons from there, producing confidently wrong conclusions built on correctly-fetched data pinned to the wrong calls. The faster the fan-out and the more variable the latencies, the more often the orders differ and the scrambling bites.

The fix is identity, not order. Every tool call carries a unique id -- the tool_call_id in modern tool-calling APIs -- and every result carries the id of the call it answers. The harness matches result to call by that id, so it does not matter which result arrives first; each is placed on the call it belongs to. Completion order becomes irrelevant, which is exactly what you want, because completion order is noise.

The rule: pair each tool result with its call by the call's id, never by the order results complete, because parallel calls finish out of issue order -- so position-based pairing attributes results to the wrong calls and the model reasons on scrambled data, while id-based pairing is correct regardless of completion order.

On this fixture three calls are issued in order t0, t1, t2 but finish t1, t2, t0. Position pairing mismatches all three -- t0 is told it got the stock result, and so on; id pairing gives every call its own result. This computes both.

  --order    the issue order vs the completion order of the parallel calls
  --pair     the naive position-based pairing vs the correct id-based pairing, per call
  --check    position pairing attributes results to the wrong calls; id pairing is correct regardless of completion order

calls is the fixture; the completion order and both pairings are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "toolmatch.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def issue_order(calls):
    return [c["id"] for c in calls]


def completion_order(calls):
    """Results arrive in order of how long each call takes."""
    return sorted(calls, key=lambda c: c["dur"])


def naive_pairing(calls):
    """Pair arrival-order results to issue-order call slots by position."""
    arrived = completion_order(calls)
    slots = issue_order(calls)
    return {slots[i]: arrived[i]["result"] for i in range(len(calls))}


def id_pairing(calls):
    """Match each result to its call by id -- completion order is irrelevant."""
    return {c["id"]: c["result"] for c in calls}


# ----------------------------------------------------------------- printing

def order_view(data):
    calls = data["calls"]
    print("ORDER — the parallel calls finish in a different order than issued")
    print("-" * 56)
    print("  issued (in order)      : %s" % issue_order(calls))
    print("  completed (by duration): %s" % [c["id"] for c in completion_order(calls)])
    print("-" * 56)
    print("  a fast call (t1) returns before a slow one (t0) issued earlier")


def pair_view(data):
    calls = data["calls"]
    naive, correct = naive_pairing(calls), id_pairing(calls)
    print("PAIR — result assigned to each call, position-based vs id-based")
    print("-" * 66)
    print("  call   true result       position pairing    ok?")
    for c in calls:
        cid = c["id"]
        ok = "yes" if naive[cid] == correct[cid] else "NO  <- wrong result"
        print("  %-5s  %-16s  %-16s  %s" % (cid, correct[cid], naive[cid], ok))
    print("-" * 66)
    print("  position pairing lands each result on the wrong call; id pairing is correct")


def check(data):
    print("SELF-TEST — position pairing attributes results to the wrong calls; id pairing is correct regardless of completion order")
    print("-" * 124)
    calls = data["calls"]
    naive, correct = naive_pairing(calls), id_pairing(calls)

    completion_differs = [c["id"] for c in completion_order(calls)] != issue_order(calls)
    print("  the calls complete in a different order than issued = %s (%s vs %s)"
          % (completion_differs, [c["id"] for c in completion_order(calls)], issue_order(calls)))

    mismatches = [cid for cid in correct if naive[cid] != correct[cid]]
    position_mispairs = len(mismatches) > 0
    print("  position pairing assigns some result to the wrong call = %s (%s)" % (position_mispairs, mismatches))

    first_call = calls[0]["id"]
    first_call_wrong = naive[first_call] != correct[first_call]
    print("  the first-issued call %s gets the wrong result = %s (%r, should be %r)"
          % (first_call, first_call_wrong, naive[first_call], correct[first_call]))

    id_pairing_correct = all(id_pairing(calls)[c["id"]] == c["result"] for c in calls)
    print("  id pairing gives every call its own result = %s" % id_pairing_correct)

    id_pairing_order_independent = id_pairing(calls) == id_pairing(list(reversed(calls)))
    print("  id pairing is the same regardless of result order = %s" % id_pairing_order_independent)

    ok = (completion_differs and position_mispairs and first_call_wrong
          and id_pairing_correct and id_pairing_order_independent)
    print("-" * 124)
    print("SELF-TEST %s  completion_differs=%s  position_mispairs=%s  first_call_wrong=%s  id_pairing_correct=%s  id_pairing_order_independent=%s"
          % ("PASS" if ok else "FAIL", completion_differs, position_mispairs, first_call_wrong, id_pairing_correct, id_pairing_order_independent))
    return ok


def main():
    p = argparse.ArgumentParser(description="Tool-result matching: pair each tool result with its call by the call's id, never by the order results complete, because parallel calls finish out of issue order -- so position-based pairing attributes results to the wrong calls and the model reasons on scrambled data, while id-based pairing is correct regardless of completion order.")
    p.add_argument("--order", action="store_true")
    p.add_argument("--pair", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%s  file=%s  (the calls are a fixture)"
          % ([(c["id"], c["dur"]) for c in data["calls"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.order:
        order_view(data)
    elif args.pair:
        pair_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
