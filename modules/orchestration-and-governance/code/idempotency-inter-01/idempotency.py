"""Dedup a retried request by its idempotency key -- or at-least-once delivery turns one charge into two.

A network between a client and a server cannot promise a message is delivered exactly once. It can promise at MOST
once (send, and if the response is lost, give up -- so some operations never happen) or at LEAST once (send, and if the
response is lost, retry -- so every operation happens, but some happen more than once). Real systems pick at-least-once,
because a lost charge that silently never happens is worse than a charge that might happen twice -- provided you can make
the twice-ness harmless. The danger is concrete: the client sends 'charge 30', the server charges 30 and replies, the
reply is lost to a timeout, and the client -- having no way to tell 'my request never arrived' from 'the reply never came
back' -- retries. A server that just applies every request it receives now charges 30 twice: the account is debited 60
for one intended payment.

The fix is an idempotency key: a client-generated id that names the OPERATION, not the network attempt. The client
stamps both the original and the retry with the same key, and the server keeps a dedup store mapping key -> the response
it already produced. On the first request for a key the server applies the effect and records the response; on any later
request with a key it has seen, it does NOT re-apply -- it returns the stored response, so the retry is a safe no-op that
still gives the client the answer it missed. That makes an at-least-once transport deliver an exactly-once EFFECT. The
key discipline: dedup must suppress retries (same key) without suppressing genuinely distinct operations (different
keys), so the key must name the operation the client intends, and two real payments must carry two different keys.

On this fixture the account starts at 100 and one charge of 30 is sent, then retried after a lost response (same key
req-abc). The naive server applies both and leaves the balance at 40 -- charged twice. The idempotent server applies the
first, stores the response, and on the retry returns that stored response without re-charging, leaving the balance at 70
-- charged once. Two DIFFERENT operations (keys req-abc and req-xyz) both apply, so dedup does not over-suppress. This
computes all three.

  --naive       process the charge and its retry with a server that applies every request -- the account is charged twice
  --idempotent  process the same two messages with a dedup store keyed by idempotency key -- charged once, retry cached
  --check       at-least-once retries double-charge naively but apply once under the key; distinct keys both still apply

The balances, keys, and amounts are the fixture; every resulting balance is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "idempotency.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def apply_charge(balance, amount):
    """Debit the account: the effect a charge request performs."""
    return round(balance - amount, 2)


def run_naive(start, requests):
    """A server that applies every request it receives -- no dedup, so a retry is a second charge."""
    balance = start
    log = []
    for r in requests:
        balance = apply_charge(balance, r["amount"])
        log.append({"key": r["key"], "amount": r["amount"], "applied": True, "balance": balance})
    return balance, log


def run_idempotent(start, requests):
    """A server that dedups by idempotency key: apply and store on first sight of a key, replay the stored response after."""
    balance = start
    store = {}
    log = []
    for r in requests:
        key = r["key"]
        if key in store:
            # a retry of an operation already performed: do NOT re-apply, return the stored response
            log.append({"key": key, "amount": r["amount"], "applied": False, "balance": balance, "returned": store[key]["balance_after"]})
        else:
            balance = apply_charge(balance, r["amount"])
            store[key] = {"balance_after": balance, "charged": r["amount"]}
            log.append({"key": key, "amount": r["amount"], "applied": True, "balance": balance, "returned": balance})
    return balance, store, log


# ----------------------------------------------------------------- printing

def naive_view(data):
    start = data["start_balance"]
    final, log = run_naive(start, data["requests"])
    print("NAIVE — a server that applies every request (no dedup)")
    print("-" * 62)
    print("  start balance = %.2f" % start)
    for e in log:
        print("  recv %-8s amount %-5.1f -> APPLIED, balance %.2f" % (e["key"], e["amount"], e["balance"]))
    print("-" * 62)
    print("  final balance = %.2f  (one intended charge of 30, applied twice = 60 debited)" % final)


def idempotent_view(data):
    start = data["start_balance"]
    final, store, log = run_idempotent(start, data["requests"])
    print("IDEMPOTENT — a server that dedups by idempotency key")
    print("-" * 66)
    print("  start balance = %.2f" % start)
    for e in log:
        if e["applied"]:
            print("  recv %-8s amount %-5.1f -> APPLIED, balance %.2f (response stored)" % (e["key"], e["amount"], e["balance"]))
        else:
            print("  recv %-8s amount %-5.1f -> DUPLICATE, no re-charge, returned stored %.2f" % (e["key"], e["amount"], e["returned"]))
    print("-" * 66)
    print("  final balance = %.2f  (one intended charge, applied once = 30 debited)" % final)
    print("  dedup store: %s" % {k: v["balance_after"] for k, v in store.items()})


def check(data):
    print("SELF-TEST — at-least-once retries double-charge naively but apply once under the key; distinct keys both still apply")
    print("-" * 114)
    start = data["start_balance"]
    amt = data["requests"][0]["amount"]

    naive_final, _ = run_naive(start, data["requests"])
    naive_double_charges = abs(naive_final - (start - 2 * amt)) < 1e-9
    print("  the naive server applies the retry too, charging twice = %s (%.2f, debited %.2f)"
          % (naive_double_charges, naive_final, start - naive_final))

    idem_final, store, log = run_idempotent(start, data["requests"])
    idempotent_charges_once = abs(idem_final - (start - amt)) < 1e-9
    print("  the idempotent server charges the operation exactly once = %s (%.2f, debited %.2f)"
          % (idempotent_charges_once, idem_final, start - idem_final))

    retry = log[1]
    retry_returns_cached = (not retry["applied"]) and abs(retry["returned"] - idem_final) < 1e-9
    print("  the retry is not re-applied and returns the stored response = %s (returned %.2f)"
          % (retry_returns_cached, retry["returned"]))

    store_has_one_entry = len(store) == 1
    print("  the two same-key messages produced one stored operation = %s (%d entr%s)"
          % (store_has_one_entry, len(store), "y" if len(store) == 1 else "ies"))

    d_final, d_store, _ = run_idempotent(start, data["distinct"])
    distinct_keys_both_apply = len(d_store) == 2 and abs(d_final - (start - sum(r["amount"] for r in data["distinct"]))) < 1e-9
    print("  two DIFFERENT keys are both applied (dedup does not over-suppress) = %s (%.2f, %d entries)"
          % (distinct_keys_both_apply, d_final, len(d_store)))

    ok = naive_double_charges and idempotent_charges_once and retry_returns_cached and store_has_one_entry and distinct_keys_both_apply
    print("-" * 114)
    print("SELF-TEST %s  naive_double_charges=%s  idempotent_charges_once=%s  retry_returns_cached=%s  store_has_one_entry=%s  distinct_keys_both_apply=%s"
          % ("PASS" if ok else "FAIL", naive_double_charges, idempotent_charges_once, retry_returns_cached, store_has_one_entry, distinct_keys_both_apply))
    return ok


def main():
    p = argparse.ArgumentParser(description="Idempotency-key deduplication: at-least-once delivery retries a request whose response was lost, so a non-idempotent server double-applies the effect; a dedup store keyed by a client-generated idempotency key makes the retry a no-op that replays the stored response, turning an at-least-once transport into an exactly-once effect.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--idempotent", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("start_balance=%.2f  requests=%s  distinct_keys=%s  file=%s  (the amounts and keys are a fixture)"
          % (data["start_balance"], [(r["key"], r["amount"]) for r in data["requests"]],
             [r["key"] for r in data["distinct"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.idempotent:
        idempotent_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
