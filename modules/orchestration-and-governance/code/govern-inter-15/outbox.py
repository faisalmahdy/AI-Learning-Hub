"""Write the event to an outbox in the same transaction, or a crash between the two writes loses it.

A service does two things when an order is placed: it saves the order to its database and it publishes an
'order created' event so other services react. These are two separate systems -- a database and a message
broker -- and there is no transaction that spans both. So whichever you do first, a crash in the gap
between them leaves the two out of sync. Save the order, then crash before publishing: the order exists but
no one is ever told (a lost event). Publish first, then crash before saving: the event went out for an
order that does not exist (a phantom event). This is the dual-write problem, and it has no fix as long as
the state change and the event are two independent writes.

The outbox pattern removes the gap by making the event part of the state change. In the SAME database
transaction that saves the order, insert a row into an 'outbox' table describing the event. That
transaction is atomic: either both the order and its outbox row commit, or neither does. A separate relay
process then reads unsent outbox rows and publishes them, marking each sent once the broker acknowledges.
Now a crash anywhere is safe -- if it happens before the transaction commits, nothing happened; if after,
the outbox row is durably stored and the relay will publish it on recovery. The event is published exactly
when the state changed, because they were written together.

On this fixture four orders are processed and a crash hits during the third. Naive db-first commits the
third order but loses its event. Naive publish-first emits the third event but never commits the order --
a phantom. The outbox commits the order and its event row together and the relay publishes it on recovery:
no lost event, no phantom. This computes all three.

  --run        each strategy's committed orders vs published events after the crash
  --sync       the lost and phantom events each strategy leaves
  --check      naive db-first loses an event, publish-first phantoms one; the outbox does neither

The orders and crash point are the fixture; every outcome is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "orders.json"


def naive_db_first(orders, crash_at):
    """Commit the order, then publish -- a crash in between loses the event."""
    committed, published = [], []
    for i, o in enumerate(orders):
        committed.append(o)                 # write 1: database
        if i == crash_at:
            break                           # crash before the publish
        published.append(o)                 # write 2: broker
    return committed, published


def naive_publish_first(orders, crash_at):
    """Publish, then commit the order -- a crash in between emits a phantom event."""
    committed, published = [], []
    for i, o in enumerate(orders):
        published.append(o)                 # write 1: broker
        if i == crash_at:
            break                           # crash before the commit
        committed.append(o)                 # write 2: database
    return committed, published


def outbox(orders, crash_at):
    """Commit the order and an outbox row in one transaction; a relay publishes rows on recovery."""
    committed, outbox_rows = [], []
    for i, o in enumerate(orders):
        committed.append(o)                 # one atomic transaction:
        outbox_rows.append(o)               #   order + outbox row commit together
        if i == crash_at:
            break                           # crash after the commit, before the relay runs
    published = list(outbox_rows)           # recovery relay publishes every unsent outbox row
    return committed, published


STRATEGIES = {"db-first": naive_db_first, "publish-first": naive_publish_first, "outbox": outbox}


def lost(committed, published):
    """Orders committed but whose event was never published -- silently dropped work."""
    return [o for o in committed if o not in published]


def phantom(committed, published):
    """Events published for orders that were never committed -- reactions to nothing."""
    return [o for o in published if o not in committed]


# ----------------------------------------------------------------- printing

def run_view(data):
    orders, crash = data["orders"], data["crash_at"]
    print("RUN — committed orders vs published events (crash during order index %d)" % crash)
    print("-" * 60)
    for name, fn in STRATEGIES.items():
        c, p = fn(orders, crash)
        print("  %-14s committed %s" % (name, c))
        print("  %-14s published %s" % ("", p))
    print("-" * 60)
    print("  the two should always match; a crash tests whether they do.")


def sync_view(data):
    orders, crash = data["orders"], data["crash_at"]
    print("SYNC — events lost or phantom after the crash")
    print("-" * 60)
    print("  strategy         lost events        phantom events")
    for name, fn in STRATEGIES.items():
        c, p = fn(orders, crash)
        print("  %-14s   %-16s   %s" % (name, lost(c, p) or "none", phantom(c, p) or "none"))
    print("-" * 60)
    print("  only the outbox leaves neither lost nor phantom.")


def check(data):
    print("SELF-TEST — naive db-first loses an event, publish-first phantoms one; the outbox does neither")
    print("-" * 96)
    orders, crash = data["orders"], data["crash_at"]

    cdf, pdf = naive_db_first(orders, crash)
    db_first_loses = len(lost(cdf, pdf)) > 0
    print("  db-first commits an order whose event is lost = %s (lost %s)" % (db_first_loses, lost(cdf, pdf)))

    cpf, ppf = naive_publish_first(orders, crash)
    publish_first_phantoms = len(phantom(cpf, ppf)) > 0
    print("  publish-first emits an event with no committed order = %s (phantom %s)" % (publish_first_phantoms, phantom(cpf, ppf)))

    cob, pob = outbox(orders, crash)
    outbox_no_loss = len(lost(cob, pob)) == 0
    print("  the outbox loses no event = %s" % outbox_no_loss)

    outbox_no_phantom = len(phantom(cob, pob)) == 0
    print("  the outbox emits no phantom = %s" % outbox_no_phantom)

    outbox_atomic = cob == pob
    print("  every committed order has exactly its event, and vice versa = %s (%d = %d)" % (outbox_atomic, len(cob), len(pob)))

    ok = db_first_loses and publish_first_phantoms and outbox_no_loss and outbox_no_phantom and outbox_atomic
    print("-" * 96)
    print("SELF-TEST %s  db_first_loses=%s  publish_first_phantoms=%s  outbox_no_loss=%s  outbox_no_phantom=%s  outbox_atomic=%s"
          % ("PASS" if ok else "FAIL", db_first_loses, publish_first_phantoms, outbox_no_loss, outbox_no_phantom, outbox_atomic))
    return ok


def main():
    p = argparse.ArgumentParser(description="Write the event to an outbox in the same transaction as the state change.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--sync", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = json.loads((HERE / "orders.json").read_text(encoding="utf-8"))
    print("orders=%d  crash_at=%d  file=orders.json  (the orders and crash point are a fixture)"
          % (len(data["orders"]), data["crash_at"]))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.sync:
        sync_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
