"""Dedup retried tool calls by the idempotency KEY -- not by their content, or a real charge vanishes.

A harness that calls an external tool has to survive a lost acknowledgement. The call reaches the
service, the side effect happens, and then the response is dropped on the way back. The harness sees
a timeout, cannot tell "never arrived" from "arrived, ack lost", and retries. So the same logical
operation shows up twice in the stream, and if the service applies both attempts the customer is
charged twice.

The fix is an idempotency key: the client stamps every operation with a key that is stable across
its own retries and distinct across different operations. The service remembers the keys it has
already applied and, on a repeat, returns the first result instead of applying the effect again --
so a retry is a no-op. The tempting shortcut is to dedup on the content of the call instead (same op,
same amount), but that is wrong: two genuinely separate charges of the same amount share content
and different keys, and content-dedup collapses them into one, silently dropping a real charge.

On this fixture five attempts arrive: k1 twice (a retry), k2 once (a separate $10 charge), k3 twice
(a retry). Applying every attempt overcharges to 40; deduping on content undercharges to 15 because
it eats k2; deduping on the key applies each distinct operation exactly once for the true total 25.
This runs all three and shows only the key gets it right.

  --attempts   the attempt stream, with the retries marked
  --apply      the total under apply-all vs dedup-on-content vs dedup-on-key
  --check      apply-all overcharges, content-dedup drops a real charge, key-dedup is exact

The attempt stream and keys are the fixture; every total is computed. Deterministic, stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "attempts.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- three apply strategies

def apply_all(attempts):
    """Apply every attempt -- a retry is charged again, so a lost ack costs the customer twice."""
    total, log = 0, []
    for a in attempts:
        total += a["amount"]
        log.append((a["key"], a["amount"], "applied", total))
    return total, log


def apply_dedup_content(attempts):
    """Dedup on (op, amount) -- wrong: two separate charges of the same amount collapse into one."""
    total, seen, log = 0, set(), []
    for a in attempts:
        sig = (a["op"], a["amount"])
        if sig in seen:
            log.append((a["key"], a["amount"], "skipped (same content)", total))
            continue
        seen.add(sig)
        total += a["amount"]
        log.append((a["key"], a["amount"], "applied", total))
    return total, log


def apply_dedup_key(attempts):
    """Dedup on the idempotency key -- a retry is a no-op; distinct operations always apply."""
    total, seen, log = 0, set(), []
    for a in attempts:
        if a["key"] in seen:
            log.append((a["key"], a["amount"], "no-op (key seen)", total))
            continue
        seen.add(a["key"])
        total += a["amount"]
        log.append((a["key"], a["amount"], "applied", total))
    return total, log


def true_total(attempts):
    """The correct total: each distinct key's amount, counted once."""
    by_key = {a["key"]: a["amount"] for a in attempts}
    return sum(by_key.values())


# ----------------------------------------------------------------- printing

def attempts_view(data):
    attempts = data["attempts"]
    print("ATTEMPTS — the stream, in arrival order (key, amount, note)")
    print("-" * 62)
    for a in attempts:
        print("  %-4s %3d  %s" % (a["key"], a["amount"], a["note"]))
    print("-" * 62)
    keys = {a["key"] for a in attempts}
    print("  %d attempts, %d distinct keys — the extra %d are retries after a lost ack."
          % (len(attempts), len(keys), len(attempts) - len(keys)))


def apply_view(data):
    attempts = data["attempts"]
    strategies = [
        ("apply every attempt", apply_all),
        ("dedup on content", apply_dedup_content),
        ("dedup on the key", apply_dedup_key),
    ]
    print("APPLY — final total under each strategy (true total = %d)" % true_total(attempts))
    print("-" * 62)
    for name, fn in strategies:
        total, log = fn(attempts)
        print("  %s:" % name)
        for key, amt, result, running in log:
            print("    %-4s %3d  %-22s -> total %d" % (key, amt, result, running))
        print("    final total: %d" % total)
    print("-" * 62)
    print("  apply-all overcharges, content-dedup drops k2, key-dedup lands on the true total.")


def check(data):
    print("SELF-TEST — apply-all overcharges, content-dedup drops a real charge, key-dedup is exact")
    print("-" * 74)
    attempts = data["attempts"]
    true = true_total(attempts)

    t_all, _ = apply_all(attempts)
    overcharges = t_all > true
    print("  applying every attempt overcharges = %s (total %d, should be %d)" % (overcharges, t_all, true))

    t_content, _ = apply_dedup_content(attempts)
    content_drops = t_content < true
    print("  deduping on content undercharges (drops a real charge) = %s (total %d, should be %d)"
          % (content_drops, t_content, true))

    t_key, log_key = apply_dedup_key(attempts)
    key_exact = t_key == true
    print("  deduping on the key hits the true total exactly = %s (total %d)" % (key_exact, t_key))

    noops = [row for row in log_key if "no-op" in row[2]]
    retries_are_noops = len(noops) == len(attempts) - len({a["key"] for a in attempts})
    print("  every retry became a no-op under key-dedup = %s (%d no-ops)" % (retries_are_noops, len(noops)))

    ok = overcharges and content_drops and key_exact and retries_are_noops
    print("-" * 74)
    print("SELF-TEST %s  overcharges=%s  content_drops=%s  key_exact=%s  retries_are_noops=%s"
          % ("PASS" if ok else "FAIL", overcharges, content_drops, key_exact, retries_are_noops))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dedup retried tool calls by the idempotency key, not their content.")
    p.add_argument("--attempts", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    attempts = data["attempts"]
    print("attempts=%d  distinct_keys=%d  true_total=%d  file=%s  (the attempt stream is a fixture)"
          % (len(attempts), len({a["key"] for a in attempts}), true_total(attempts), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.attempts:
        attempts_view(data)
    elif args.apply:
        apply_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
