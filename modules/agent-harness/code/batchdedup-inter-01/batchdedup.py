"""Collapse the model's duplicate parallel tool calls in one turn -- executing each twice wastes budget and doubles effects.

A tool-calling model can emit several tool calls at once, to be run in parallel, and it is not always tidy about it: in a
single batch it sometimes asks for the SAME call more than once -- the identical tool with identical arguments -- because it
listed the call under two lines of reasoning, or repeated itself, or genuinely lost track. A naive harness dispatches every
call in the batch as written, so those duplicate calls each execute. For a read-only tool that is merely wasteful: you pay
twice the latency and twice the token/compute budget to fetch the same answer, and on a batch with several duplicates the
waste adds up. For a tool with SIDE EFFECTS it is worse than wasteful -- running 'send_email' or 'create_ticket' twice
because the model listed it twice sends two emails, files two tickets. Either way, executing a call the batch already
contains is work the harness should not do.

Deduplication fixes this within the batch. Compute a SIGNATURE for each call -- the tool name plus its arguments,
canonicalized so that argument order does not matter -- and group the calls by signature. Execute each UNIQUE signature
exactly once, and then FAN the single result back out to every call position that shares that signature, so the model still
receives one result per call it emitted (the shapes line up, nothing downstream notices) while the number of actual
executions drops to the number of distinct calls. Five emitted calls with two duplicates become three executions and five
results. This is distinct from caching across turns (memoization) and from retry deduplication: it is collapsing the
redundancy WITHIN one parallel batch, before anything runs, so no duplicate call is ever dispatched in the first place.

The canonicalization matters: two calls are the same only if they are truly identical, so the signature must normalize
argument order (a dict serialized with sorted keys) but must NOT treat different arguments as the same. And the fan-out
must preserve positions, because the model emitted N calls and expects N results in the right slots. Done correctly, dedup
is invisible to the model and free of downside for pure tools, and it is the ONLY safe default for effectful tools in a
batch, where a duplicate is a bug waiting to double an action.

The rule: within a single turn's batch of parallel tool calls, deduplicate by signature (tool + canonicalized arguments) --
execute each unique call once and fan its result back to every slot that shares the signature -- because dispatching a
duplicate call the batch already contains wastes latency and budget and, for a tool with side effects, performs the action
twice.

On this fixture the model emitted 5 calls, of which 2 are duplicates (a repeated search and a repeated get-time). A naive
harness runs all 5; dedup runs the 3 unique calls once each and fans the results back to all 5 slots. This computes both.

  --calls     the 5 emitted calls, each call's signature, and which are duplicates of an earlier call
  --execute   naive (5 executions) vs dedup (3 executions, results fanned to all 5 slots)
  --check     the naive harness executes every call including duplicates; dedup executes each unique call once for all slots

calls is the fixture; every signature, execution count, and fan-out is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "batchdedup.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def signature(call):
    """A canonical signature: tool name plus arguments serialized with sorted keys (order-independent)."""
    return call["tool"] + "(" + json.dumps(call["args"], sort_keys=True) + ")"


def run_naive(calls):
    """Execute every call in the batch as written -- duplicates included."""
    executed = [signature(c) for c in calls]
    return executed


def run_dedup(calls):
    """Execute each unique signature once; fan the result back to every slot that shares it."""
    first_seen = {}
    executed = []
    results = [None] * len(calls)
    for i, c in enumerate(calls):
        sig = signature(c)
        if sig not in first_seen:
            first_seen[sig] = "result_of(%s)" % sig
            executed.append(sig)          # actually dispatched
        results[i] = first_seen[sig]      # fan the (possibly reused) result into this slot
    return executed, results


# ----------------------------------------------------------------- printing

def calls_view(data):
    calls = data["calls"]
    print("CALLS — the batch the model emitted, with each call's signature")
    print("-" * 74)
    seen = set()
    for i, c in enumerate(calls):
        sig = signature(c)
        dup = "  <- duplicate of an earlier call" if sig in seen else ""
        seen.add(sig)
        print("  call %d: %s%s" % (i, sig, dup))
    print("-" * 74)
    print("  %d calls emitted; %d distinct signatures." % (len(calls), len(seen)))


def execute_view(data):
    calls = data["calls"]
    naive = run_naive(calls)
    executed, results = run_dedup(calls)
    print("EXECUTE — naive dispatch vs dedup")
    print("-" * 70)
    print("  NAIVE:  executes %d calls: %s" % (len(naive), naive))
    print("  DEDUP:  executes %d calls: %s" % (len(executed), executed))
    print("          results fanned to all %d slots:" % len(results))
    for i, r in enumerate(results):
        print("            slot %d <- %s" % (i, r))
    print("-" * 70)
    print("  dedup saved %d executions and still answered all %d slots." % (len(naive) - len(executed), len(results)))


def check(data):
    print("SELF-TEST — the naive harness executes every call including duplicates; dedup executes each unique call once for all slots")
    print("-" * 124)
    calls = data["calls"]
    naive = run_naive(calls)
    executed, results = run_dedup(calls)
    unique = len(set(signature(c) for c in calls))

    naive_executes_all = len(naive) == len(calls)
    print("  naive executes every call in the batch = %s (%d executions for %d calls)" % (naive_executes_all, len(naive), len(calls)))

    dedup_executes_unique = len(executed) == unique
    print("  dedup executes exactly the unique calls = %s (%d executions for %d distinct)" % (dedup_executes_unique, len(executed), unique))

    dedup_saves = len(executed) < len(naive)
    print("  dedup runs fewer executions than naive = %s (%d < %d)" % (dedup_saves, len(executed), len(naive)))

    all_slots_answered = all(r is not None for r in results) and len(results) == len(calls)
    print("  every emitted call slot still gets a result = %s (%d of %d)" % (all_slots_answered, sum(1 for r in results if r is not None), len(calls)))

    dups_share_result = results[0] == results[2] and results[1] == results[4]
    print("  duplicate slots share the single result = %s (slot0==slot2, slot1==slot4)" % dups_share_result)

    ok = naive_executes_all and dedup_executes_unique and dedup_saves and all_slots_answered and dups_share_result
    print("-" * 124)
    print("SELF-TEST %s  naive_executes_all=%s  dedup_executes_unique=%s  dedup_saves=%s  all_slots_answered=%s  dups_share_result=%s"
          % ("PASS" if ok else "FAIL", naive_executes_all, dedup_executes_unique, dedup_saves, all_slots_answered, dups_share_result))
    return ok


def main():
    p = argparse.ArgumentParser(description="Batch tool-call dedup: within a single turn's batch of parallel tool calls, deduplicate by signature (tool + canonicalized arguments) -- execute each unique call once and fan its result back to every slot that shares the signature -- because dispatching a duplicate call the batch already contains wastes latency and budget and, for a tool with side effects, performs the action twice.")
    p.add_argument("--calls", action="store_true")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  file=%s  (the emitted batch of tool calls is a fixture)" % (len(data["calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.calls:
        calls_view(data)
    elif args.execute:
        execute_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
