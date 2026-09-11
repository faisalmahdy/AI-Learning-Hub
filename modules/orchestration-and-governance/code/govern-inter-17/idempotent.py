"""Dedup retries by an idempotency key, or a lost ack makes the effect apply twice.

A request with a side effect -- charge a card, send an email, increment a counter -- travels over an
unreliable link. The service does the work and sends an ack; the ack is lost. The client, seeing no
reply, does the only safe thing it knows: it retries. Now the same logical request arrives again. If the
service just does the work again, the effect happens twice: a double charge, a duplicate email, a counter
off by one. The failure is not a bug in the work -- each application is correct in isolation -- it is that
"do the work" and "at most once" are different requirements, and a plain handler only satisfies the first.

An idempotency key fixes it. The client stamps each LOGICAL request with a stable key and reuses that key
on every retry. The service keeps a record of keys it has already applied; on a repeat key it returns the
stored result WITHOUT redoing the effect. The first arrival of a key does the work; every later arrival of
the same key is a no-op that just re-acks. The effect now happens exactly once per logical request no matter
how many times the network makes the client retry.

On this fixture six requests arrive, but only three keys are distinct -- r1 was retried twice and r2 once.
A naive handler applies all six and totals 48. A keyed handler applies each key's amount once and totals 23,
the correct sum of the three logical requests. Same stream; the key turns the duplicates into no-ops. This
computes both.

  --apply      the running effect of the naive handler vs the idempotent handler, request by request
  --keys       the distinct keys, how many times each arrived, and the once-only applied amount
  --check      the naive handler double-applies retried keys; the keyed handler applies each exactly once

The request stream is the fixture; every application is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ledger.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_total(requests):
    """Apply every request's effect -- no memory of what was already done."""
    return sum(r["amount"] for r in requests)


def idempotent_total(requests):
    """Apply a key's effect only the first time it is seen; later arrivals are no-ops."""
    seen, total = set(), 0
    for r in requests:
        if r["key"] not in seen:
            seen.add(r["key"])
            total += r["amount"]
    return total


def key_counts(requests):
    counts = {}
    for r in requests:
        counts[r["key"]] = counts.get(r["key"], 0) + 1
    return counts


def correct_total(requests):
    """One amount per distinct logical request -- the intended sum."""
    first = {}
    for r in requests:
        first.setdefault(r["key"], r["amount"])
    return sum(first.values())


# ----------------------------------------------------------------- printing

def apply_view(data):
    requests = data["requests"]
    print("APPLY — running total after each request (naive applies all, keyed dedups)")
    print("-" * 64)
    seen, naive, keyed = set(), 0, 0
    print("  #  key   amount   naive   keyed   note")
    for i, r in enumerate(requests, 1):
        naive += r["amount"]
        note = ""
        if r["key"] in seen:
            note = "retry -> no-op"
        else:
            seen.add(r["key"])
            keyed += r["amount"]
        print("  %d  %-4s  %5d   %5d   %5d   %s" % (i, r["key"], r["amount"], naive, keyed, note))
    print("-" * 64)
    print("  naive total %d overshoots; keyed total %d matches the %d logical requests."
          % (naive, keyed, len(set(r["key"] for r in requests))))


def keys_view(data):
    requests = data["requests"]
    counts = key_counts(requests)
    first = {}
    for r in requests:
        first.setdefault(r["key"], r["amount"])
    print("KEYS — distinct keys, arrivals, and the once-only applied amount")
    print("-" * 64)
    for k in sorted(counts):
        print("  %-4s  arrived %d time(s)   applies %d once" % (k, counts[k], first[k]))
    print("-" * 64)
    print("  %d requests arrived, %d distinct keys, %d duplicate arrivals."
          % (len(requests), len(counts), len(requests) - len(counts)))


def check(data):
    print("SELF-TEST — the naive handler double-applies retried keys; the keyed handler applies each exactly once")
    print("-" * 104)
    requests = data["requests"]
    counts = key_counts(requests)
    naive, keyed, correct = naive_total(requests), idempotent_total(requests), correct_total(requests)

    duplicates_present = any(c > 1 for c in counts.values())
    print("  the stream contains retried (duplicate) keys = %s (%s)"
          % (duplicates_present, {k: c for k, c in counts.items() if c > 1}))

    naive_overshoots = naive > correct
    print("  the naive handler applies too much = %s (naive %d vs correct %d)" % (naive_overshoots, naive, correct))

    keyed_correct = keyed == correct
    print("  the keyed handler matches the correct total = %s (keyed %d vs correct %d)" % (keyed_correct, keyed, correct))

    first = {}
    for r in requests:
        first.setdefault(r["key"], r["amount"])
    keyed_applies_each_once = keyed == sum(first.values())
    print("  the keyed total equals one amount per distinct key = %s" % keyed_applies_each_once)

    retried_amount = sum((counts[k] - 1) * first[k] for k in counts)
    retries_are_noops = naive - keyed == retried_amount
    print("  the gap naive-keyed equals exactly the retried amounts = %s (%d)" % (retries_are_noops, retried_amount))

    ok = duplicates_present and naive_overshoots and keyed_correct and keyed_applies_each_once and retries_are_noops
    print("-" * 104)
    print("SELF-TEST %s  duplicates_present=%s  naive_overshoots=%s  keyed_correct=%s  keyed_applies_each_once=%s  retries_are_noops=%s"
          % ("PASS" if ok else "FAIL", duplicates_present, naive_overshoots, keyed_correct, keyed_applies_each_once, retries_are_noops))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dedup retried requests by an idempotency key so a side effect applies exactly once.")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--keys", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  distinct_keys=%d  file=%s  (the request stream is a fixture)"
          % (len(data["requests"]), len(key_counts(data["requests"])), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.apply:
        apply_view(data)
    elif args.keys:
        keys_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
