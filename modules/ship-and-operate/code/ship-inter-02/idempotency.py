#!/usr/bin/env python3
"""Retries need idempotency, or you pay twice -- the lost-ack double-charge.

A client calls a server over a channel that can fail. The benign failure is the
request never arriving: the client retries, nothing was committed, no harm. The
vicious failure is the ack getting lost AFTER the server already committed the
effect. The client sees no ack, cannot tell "never happened" from "happened, reply
lost", and does the only safe-looking thing: retry. A naive server treats the retry
as a new request and commits the effect again. Now the customer is charged twice.

The fix is an idempotency key: a stable identifier the client attaches to the
logical operation and REUSES on every retry. The server remembers keys it has
already applied and, on a repeat, returns the stored result instead of committing
again -- exactly-once effect over an at-least-once channel. The catch is "stable":
if the key changes between retries (a timestamp, an attempt counter), the server
sees a new key each time and the dedup does nothing. This measures both.

  --naive       retry without idempotency keys; count the duplicate charges
  --keyed       retry with a stable idempotency key; exactly-once effect
  --check       naive overcharges; a stable key fixes it; an unstable key does not

Deterministic: the fixture says how many attempts committed-then-lost-their-ack per
operation. Stdlib only. No network, no clock.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "idempotency.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))["ops"]


# ------------------------------------------------------------- the server

class Server:
    """Commits charges. With idempotency, it remembers keys already applied."""

    def __init__(self):
        self.total = 0.0
        self.commits = 0
        self.seen = {}  # idempotency key -> stored result

    def apply(self, amount, key=None):
        """Commit the charge. If a key is given and already seen, return the stored result."""
        if key is not None and key in self.seen:
            return self.seen[key]  # dedup: no second commit
        self.total += amount
        self.commits += 1
        result = {"committed": amount}
        if key is not None:
            self.seen[key] = result
        return result


# ---------------------------------------------------- the client's retry loop

def send_with_retries(server, op, key_fn=None):
    """Retry until the ack lands. key_fn(op, attempt) builds the key sent on each attempt.

    The fixture's commits_before_ack says how many attempts commit but lose the ack;
    those attempts still call server.apply (the effect happened), then the client
    retries. key_fn=None models a server with no idempotency at all.
    """
    lost = op["commits_before_ack"]
    for attempt in range(lost + 1):  # attempts 0..lost; the last one's ack survives
        key = key_fn(op, attempt) if key_fn else None
        server.apply(op["amount"], key)
        # attempts < lost committed but the ack was lost -> client loops again
    # attempt == lost acked successfully; client stops


STABLE_KEY = lambda op, attempt: op["id"]            # correct: same key every retry
UNSTABLE_KEY = lambda op, attempt: "%s#%d" % (op["id"], attempt)  # bug: key changes per attempt


# ----------------------------------------------------------------- runs

def run(ops, key_fn):
    server = Server()
    for op in ops:
        send_with_retries(server, op, key_fn)
    return server


def intended(ops):
    return sum(op["amount"] for op in ops), len(ops)


def naive_view(ops):
    want_total, want_n = intended(ops)
    s = run(ops, None)
    print("NAIVE — retry with no idempotency key; every retry commits again")
    print("-" * 66)
    for op in ops:
        dup = op["commits_before_ack"]
        note = "charged %dx" % (dup + 1) if dup else "charged once"
        print("  %-12s amount=%5.1f  lost-acks=%d  -> %s" % (op["id"], op["amount"], dup, note))
    print("-" * 66)
    print("  intended: %d charges totalling %.1f" % (want_n, want_total))
    print("  committed: %d charges totalling %.1f  (overcharge %.1f)"
          % (s.commits, s.total, s.total - want_total))


def keyed_view(ops):
    want_total, want_n = intended(ops)
    s = run(ops, STABLE_KEY)
    print("KEYED — retry with a STABLE idempotency key; server dedups repeats")
    print("-" * 66)
    for op in ops:
        print("  %-12s amount=%5.1f  key=%s  -> committed once" % (op["id"], op["amount"], op["id"]))
    print("-" * 66)
    print("  intended: %d charges totalling %.1f" % (want_n, want_total))
    print("  committed: %d charges totalling %.1f  (overcharge %.1f)"
          % (s.commits, s.total, s.total - want_total))


def check(ops):
    print("SELF-TEST — naive overcharges; a stable key is exactly-once; an unstable key is not")
    print("-" * 66)
    want_total, want_n = intended(ops)

    naive = run(ops, None)
    naive_overcharges = naive.total > want_total and naive.commits > want_n
    print("  naive retry overcharges = %s (committed %.1f vs intended %.1f)"
          % (naive_overcharges, naive.total, want_total))

    keyed = run(ops, STABLE_KEY)
    keyed_exact = keyed.total == want_total and keyed.commits == want_n
    print("  stable key -> exactly once = %s (committed %.1f, %d charges)"
          % (keyed_exact, keyed.total, keyed.commits))

    unstable = run(ops, UNSTABLE_KEY)
    unstable_fails = unstable.total == naive.total
    print("  UNSTABLE key dedups nothing = %s (committed %.1f, same as naive)"
          % (unstable_fails, unstable.total))

    det = run(ops, STABLE_KEY).total == run(ops, STABLE_KEY).total
    ok = naive_overcharges and keyed_exact and unstable_fails and det
    print("-" * 66)
    print("SELF-TEST %s  naive_overcharges=%s  keyed_exact=%s  unstable_fails=%s"
          % ("PASS" if ok else "FAIL", naive_overcharges, keyed_exact, unstable_fails))
    return ok


def main():
    p = argparse.ArgumentParser(description="Lost-ack double-charge and the idempotency-key fix.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--keyed", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    ops = load()
    print("ops=%d  file=%s  (delivery outcomes are a fixture)" % (len(ops), DATA.name))
    print("")

    if args.check:
        return 0 if check(ops) else 1
    if args.naive:
        naive_view(ops)
    elif args.keyed:
        keyed_view(ops)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
