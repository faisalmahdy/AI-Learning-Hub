---
id: govern-inter-15
title: Write the event to an outbox in the same transaction — or a crash between the two writes loses it
topic: orchestration-and-governance
level: intermediate
status: ready
time: 21 min
summary: Saving state to a database and publishing an event are two independent writes with no transaction spanning them, so a crash in the gap desynchronizes them — commit then crash loses the event, publish then crash emits a phantom. The outbox pattern writes the event into an outbox table in the same DB transaction as the state change, so the two commit atomically and a relay publishes the row on recovery. On four orders with a crash during the third, db-first loses that event and publish-first phantoms it, while the outbox does neither.
eli5: Imagine you must both write a note in your diary and mail a letter. If you write the note then get interrupted before mailing, the letter never goes. If you mail first then get interrupted before writing, your diary is wrong. The trick: put the letter in your outbox as part of writing the diary entry — one action — and a mail carrier sends whatever's in the outbox later. Now they can never disagree.
---

## Why this module

Two writes to two different systems can never be made atomic by ordering them, so any code that saves state and then publishes an event has a crash window that silently corrupts one or the other.

A service does two things when an order is placed: it saves the order to its database, and it publishes an "order created" event so downstream services react — reserve inventory, send a confirmation, update analytics. The database and the message broker are two separate systems, and there is no transaction that spans both. You commit to one, then the other, and between those two commits there is a window in which the process can crash, the network can drop, the machine can be killed. Whatever you did first survives; whatever you were about to do does not.

Which failure you get depends only on the order you chose, and both are bad. Save the order first and crash before publishing: the order exists in the database but the event was never sent, so no downstream service ever learns of it — a lost event, and the order sits there un-processed forever. Publish first and crash before saving: the event went out for an order that does not exist, so downstream services react to nothing — a phantom event, reserving inventory for a phantom order. There is no third ordering that escapes this; as long as the state change and the event are two independent writes, the gap between them is a correctness hole.

The outbox pattern closes the gap by making the event part of the state change instead of a second, separate write. In the same database transaction that saves the order, you insert a row into an "outbox" table describing the event to be published. That transaction is atomic — the database guarantees the order row and the outbox row either both commit or both roll back. A separate relay process then reads unsent outbox rows and publishes them to the broker, marking each row sent once the broker acknowledges. The event is now recorded exactly when the state changed, because they were written together, and publishing is a durable, retriable step decoupled from the state change.

On the fixture, four orders are processed and a crash hits during the third. Naive db-first commits the third order but loses its event. Naive publish-first emits the third event but never commits the order — a phantom. The outbox commits the order and its event row together, and the relay publishes it on recovery: no lost event, no phantom.

**Saving state and publishing an event are two writes with no shared transaction, so a crash between them loses the event or emits a phantom depending on order; the outbox writes the event into the same DB transaction as the state change, making them atomic, and a relay publishes the durable row on recovery.**

## Concepts

The root problem is that atomicity does not compose across systems. A database transaction is atomic within the database; a broker publish is (at best) atomic within the broker; but there is no transaction that brackets one write to each. Sequencing them — do A, then B — gives you "A definitely happened, B maybe happened," which is exactly the inconsistency. This is the dual-write problem, and it is fundamental: you cannot make two independent writes to two systems atomic by any ordering or retry logic at the call site, because the failure can land in the gap no matter how you arrange the calls.

<svg role="img" aria-label="Naive path has two separate writes with a crash gap between them; outbox path has one atomic write to the database and a separate relay publish" viewBox="0 0 470 185" width="470" height="185">
  <rect x="0" y="0" width="470" height="185" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">two writes with a gap vs one atomic write plus a relay</text>
  <text x="20" y="46" font-family="var(--mono)" font-size="9" fill="var(--s2)">naive</text>
  <rect x="70" y="36" width="80" height="20" fill="var(--acc-line)"/>
  <text x="80" y="50" font-family="var(--mono)" font-size="7" fill="var(--panel)">write DB</text>
  <rect x="180" y="36" width="30" height="20" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/>
  <text x="176" y="70" font-family="var(--mono)" font-size="7" fill="var(--s2)">GAP (crash here desyncs)</text>
  <rect x="240" y="36" width="90" height="20" fill="var(--acc-line)"/>
  <text x="250" y="50" font-family="var(--mono)" font-size="7" fill="var(--panel)">publish broker</text>
  <text x="20" y="116" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">outbox</text>
  <rect x="70" y="106" width="150" height="20" fill="var(--acc-line)"/>
  <text x="76" y="120" font-family="var(--mono)" font-size="7" fill="var(--panel)">write DB + outbox row (atomic)</text>
  <text x="230" y="120" font-family="var(--mono)" font-size="10" fill="var(--muted)">→</text>
  <rect x="250" y="106" width="120" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="256" y="120" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">relay reads + publishes</text>
  <text x="70" y="150" font-family="var(--mono)" font-size="8" fill="var(--muted)">no gap between two writes — the event is durable the moment the state is</text>
</svg>
^ The naive path has a crash-exposed gap between two independent writes; the outbox makes the state change and the event one atomic write, then the relay publishes from the durable row as a separate, retriable step.

The outbox pattern works by reducing two writes to one. Instead of writing state to the database and the event to the broker, you write both state and event to the database — the event as a row in an outbox table — in a single transaction. Now there is exactly one atomic write, so there is no gap to crash in: either the order and its pending event both exist, or neither does. The broker publish still happens, but it is moved out of the critical path and turned into a separate step that reads the durable outbox and publishes from it. You have traded "two writes that can disagree" for "one write, then a retriable read-and-publish."

That relay step is what makes publishing reliable, and it works because the outbox row is durable and the publish is idempotent-friendly. The relay polls (or tails the transaction log for) unsent outbox rows and publishes each, marking it sent only after the broker acknowledges. If the relay crashes mid-publish, the row is still marked unsent, so on restart it publishes again — which means the event may be delivered more than once, so consumers must be idempotent (dedup on the event id). This is the deliberate trade the outbox makes: it guarantees at-least-once delivery (never lost) rather than exactly-once (which is impossible across systems), and pushes the deduplication to the consumer, where it can actually be done.

This is one of a small family of solutions to the same problem, and knowing the neighbors helps. The transactional outbox (what this module builds) is the most common. Change-data-capture (CDC) is a variant where the relay tails the database's write-ahead log instead of polling a table, so the outbox is implicit in the log. The listen-to-yourself pattern publishes first and treats the event as the source of truth. And full distributed transactions (two-phase commit across the DB and broker) are the heavyweight alternative, usually avoided for their cost and coupling. All of them share the outbox's core move: never rely on two independent writes staying consistent — anchor the event to the state change in one atomic step, and make delivery a separate, retriable concern.

**Atomicity does not compose across a database and a broker, so no ordering of two writes is safe; the outbox reduces them to one atomic write by storing the event in the DB transaction, then a retriable relay publishes it at-least-once — trading impossible exactly-once for lost-nothing plus idempotent consumers.**

## Worked example

The fixture is a list of orders and the point at which the process crashes.

```json filename=modules/orchestration-and-governance/code/govern-inter-15/orders.json:3-4 COMPLETE
  "crash_at": 2,
  "orders": ["order_0", "order_1", "order_2", "order_3"]
```

Four orders, each needing a database commit and an event publish; the crash lands during order index 2, in the gap between its two writes. The naive db-first strategy commits, then publishes — so the crash leaves order 2 committed but unpublished.

```python filename=modules/orchestration-and-governance/code/govern-inter-15/outbox.py:39-47 COMPLETE
def naive_db_first(orders, crash_at):
    """Commit the order, then publish -- a crash in between loses the event."""
    committed, published = [], []
    for i, o in enumerate(orders):
        committed.append(o)                 # write 1: database
        if i == crash_at:
            break                           # crash before the publish
        published.append(o)                 # write 2: broker
    return committed, published
```

The outbox strategy commits the order and its outbox row in one transaction, then a relay publishes every outbox row on recovery.

```python filename=modules/orchestration-and-governance/code/govern-inter-15/outbox.py:61-70 COMPLETE
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
```

Predict: db-first will have one more committed order than published event (order 2 lost); publish-first will have the reverse (order 2 phantom); the outbox will have committed and published equal, because the event row committed with the order and the relay published it. Run all three.

```text filename=modules/orchestration-and-governance/code/govern-inter-15/outbox.py --run
RUN — committed orders vs published events (crash during order index 2)
------------------------------------------------------------
  db-first       committed ['order_0', 'order_1', 'order_2']
                 published ['order_0', 'order_1']
  publish-first  committed ['order_0', 'order_1']
                 published ['order_0', 'order_1', 'order_2']
  outbox         committed ['order_0', 'order_1', 'order_2']
                 published ['order_0', 'order_1', 'order_2']
------------------------------------------------------------
  the two should always match; a crash tests whether they do.
```

Db-first committed order_2 but never published its event — the committed list is longer than the published list by exactly that order. Publish-first published order_2's event but never committed the order — the mismatch is reversed. The outbox committed order_2 and its event row in one transaction, so both are present, and the relay published it on recovery: committed and published match exactly. The crash landed in the same place all three times; only the outbox had no gap for it to land in. Now name the damage.

```text filename=modules/orchestration-and-governance/code/govern-inter-15/outbox.py --sync
SYNC — events lost or phantom after the crash
------------------------------------------------------------
  strategy         lost events        phantom events
  db-first         ['order_2']        none
  publish-first    none               ['order_2']
  outbox           none               none
------------------------------------------------------------
  only the outbox leaves neither lost nor phantom.
```

Db-first's failure is a lost event: order_2 exists but nothing downstream will ever hear of it, so it silently never gets processed — the worst kind of bug, because there is no error, just missing work. Publish-first's failure is a phantom event: downstream services act on order_2 (charge a card, reserve stock) for an order that does not exist in the database. The outbox has an empty column under both — the only strategy where the committed orders and published events are the same set.

<svg role="img" aria-label="Timeline of order 2's two writes: db-first commits then crashes losing the publish; publish-first publishes then crashes losing the commit; outbox does both in one atomic block then a relay publishes" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">order 2's writes and where the crash lands (✕)</text>
  <text x="20" y="46" font-family="var(--mono)" font-size="9" fill="var(--s2)">db-first</text>
  <rect x="100" y="36" width="80" height="16" fill="var(--acc-line)"/>
  <text x="108" y="48" font-family="var(--mono)" font-size="7" fill="var(--panel)">commit DB</text>
  <text x="188" y="48" font-family="var(--mono)" font-size="10" fill="var(--s2)">✕</text>
  <rect x="210" y="36" width="80" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="3 2"/>
  <text x="214" y="48" font-family="var(--mono)" font-size="7" fill="var(--s2)">publish (lost)</text>
  <text x="20" y="96" font-family="var(--mono)" font-size="9" fill="var(--s2)">publish-first</text>
  <rect x="100" y="86" width="80" height="16" fill="var(--s2)"/>
  <text x="108" y="98" font-family="var(--mono)" font-size="7" fill="var(--panel)">publish</text>
  <text x="188" y="98" font-family="var(--mono)" font-size="10" fill="var(--s2)">✕</text>
  <rect x="210" y="86" width="80" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="3 2"/>
  <text x="214" y="98" font-family="var(--mono)" font-size="7" fill="var(--s2)">commit (phantom)</text>
  <text x="20" y="146" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">outbox</text>
  <rect x="100" y="136" width="120" height="16" fill="var(--acc-line)"/>
  <text x="106" y="148" font-family="var(--mono)" font-size="7" fill="var(--panel)">commit DB + outbox row</text>
  <text x="228" y="148" font-family="var(--mono)" font-size="10" fill="var(--s2)">✕</text>
  <rect x="250" y="136" width="120" height="16" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="256" y="148" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">relay publishes on recovery</text>
  <text x="30" y="178" font-family="var(--mono)" font-size="8" fill="var(--muted)">the crash lands between the two writes for all three — only the outbox has no gap there</text>
</svg>
^ For db-first and publish-first the crash falls between two independent writes and one is lost; the outbox does both state and event in one atomic block, so the crash falls after it, where the durable outbox row lets the relay finish the publish.

## Build

Reproduce the desync. Pure standard library, deterministic, so the lost order_2, the phantom order_2, and the clean outbox come out exactly.

Run `--run` for the committed-versus-published lists, `--sync` for the lost and phantom events, `--check` for the gate. The lost and phantom sets are simple list differences.

```python filename=modules/orchestration-and-governance/code/govern-inter-15/outbox.py:76-83 COMPLETE
def lost(committed, published):
    """Orders committed but whose event was never published -- silently dropped work."""
    return [o for o in committed if o not in published]


def phantom(committed, published):
    """Events published for orders that were never committed -- reactions to nothing."""
    return [o for o in published if o not in committed]
```

<svg role="img" aria-label="Table of the three strategies showing db-first with a lost event, publish-first with a phantom event, and outbox with neither" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">order 2 after the crash, by strategy</text>
  <text x="150" y="42" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">lost?</text>
  <text x="300" y="42" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">phantom?</text>
  <text x="20" y="72" font-family="var(--mono)" font-size="9" fill="var(--ink)">db-first</text>
  <text x="150" y="72" font-family="var(--mono)" font-size="10" fill="var(--s2)">LOST</text>
  <text x="300" y="72" font-family="var(--mono)" font-size="10" fill="var(--acc-line)">ok</text>
  <text x="20" y="102" font-family="var(--mono)" font-size="9" fill="var(--ink)">publish-first</text>
  <text x="150" y="102" font-family="var(--mono)" font-size="10" fill="var(--acc-line)">ok</text>
  <text x="300" y="102" font-family="var(--mono)" font-size="10" fill="var(--s2)">PHANTOM</text>
  <text x="20" y="132" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">outbox</text>
  <text x="150" y="132" font-family="var(--mono)" font-size="10" fill="var(--acc-line)">ok</text>
  <text x="300" y="132" font-family="var(--mono)" font-size="10" fill="var(--acc-line)">ok</text>
  <line x1="130" y1="50" x2="130" y2="145" stroke="var(--line)"/>
  <line x1="15" y1="82" x2="440" y2="82" stroke="var(--line)" stroke-dasharray="2 2"/>
  <line x1="15" y1="112" x2="440" y2="112" stroke="var(--line)" stroke-dasharray="2 2"/>
</svg>
^ Each naive ordering fails on exactly one axis — db-first loses, publish-first phantoms — and only the outbox is clean on both, because it never has two independent writes to disagree.

The self-test pins each naive failure and the outbox's atomicity — that its committed orders and published events are exactly the same set.

```python filename=modules/orchestration-and-governance/code/govern-inter-15/outbox.py:132 COMPLETE
    outbox_atomic = cob == pob
```

```text filename=modules/orchestration-and-governance/code/govern-inter-15/outbox.py --check
SELF-TEST — naive db-first loses an event, publish-first phantoms one; the outbox does neither
------------------------------------------------------------------------------------------------
  db-first commits an order whose event is lost = True (lost ['order_2'])
  publish-first emits an event with no committed order = True (phantom ['order_2'])
  the outbox loses no event = True
  the outbox emits no phantom = True
  every committed order has exactly its event, and vice versa = True (3 = 3)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  db_first_loses=True  publish_first_phantoms=True  outbox_no_loss=True  outbox_no_phantom=True  outbox_atomic=True
```

Five True flags. Db_first_loses: committing before publishing drops order_2's event. Publish_first_phantoms: publishing before committing emits a phantom order_2 event. Outbox_no_loss and outbox_no_phantom: the outbox has neither. Outbox_atomic: its committed and published sets are identical (3 = 3), which is the whole guarantee — the event exists exactly when the state does. The atomicity flag is the one that explains the other four: because the order and its event row commit together, there is no state without an event or event without state.

**The atomicity flag is the mechanism — committed equals published because the order and its outbox row are one transaction, so the crash that loses an event under either naive ordering has no gap to exploit under the outbox.**

## Definition of done

You are done when you reproduce the lost and phantom events and can explain why the outbox has neither.

Concretely: `--run` shows db-first with one more committed than published and publish-first with the reverse, while the outbox matches; `--sync` shows lost order_2 for db-first, phantom order_2 for publish-first, and none for the outbox; `--check` prints PASS with five True flags. You can explain that atomicity does not compose across a database and a broker so no ordering of two writes is safe, that the outbox reduces them to one atomic write by storing the event in the DB transaction, and that the relay then publishes at-least-once — so consumers must be idempotent because exactly-once across systems is impossible. You can name the neighbors: CDC, listen-to-yourself, and two-phase commit.

The habit to carry: whenever code writes to a database and then publishes an event (or calls another service), recognize the dual-write and use an outbox — write the event to an outbox table in the same transaction and let a relay publish it — rather than trusting the two writes to stay consistent. When downstream services occasionally miss events, or react to state that does not exist, suspect a dual-write with a crash window, not a flaky broker. Anchor the event to the state change; deliver it separately.

## Boss fight

The instructive failure is an order service that occasionally ships nothing for a paid order.

Customers report being charged with no confirmation and no fulfillment for a small fraction of orders. The order service commits the order to its database and then publishes an "order placed" event to Kafka; once in a while the pod is killed in the millisecond between the commit and the publish, so the order is saved and paid but the event never fires, and no downstream service — fulfillment, email, analytics — ever sees it. It is rare, non-reproducible, and invisible in logs (no error occurred), which is why it survives to production. The fix is the transactional outbox: write the event to an outbox table in the same transaction as the order, and run a relay (or Debezium CDC on the outbox table) to publish reliably, so a kill anywhere either leaves the order un-committed or leaves a durable outbox row the relay will send.

Your turn, two moves. First, add the at-least-once wrinkle: make the relay crash after publishing order_2 but before marking its outbox row sent, then re-run the relay and confirm order_2 is published twice — showing the outbox guarantees at-least-once, not exactly-once, so consumers must dedup on the event id. Second, sweep the crash point across every order and across both phases (before and after the single outbox transaction) and confirm the outbox is consistent at every crash point while the two naive strategies each fail at the crash points in their gap — the outbox has no gap, the naive ones have a gap per order.

## External resources

Chris Richardson's microservices.io writeup of the Transactional Outbox pattern (and the companion Polling Publisher and Transaction Log Tailing patterns) is the canonical reference, with the dual-write motivation this module builds from.

The Debezium documentation on the outbox event router shows the change-data-capture variant in production — tailing the database log so the outbox table is published without a polling relay.

Any treatment of the dual-write problem and why distributed transactions (two-phase commit) are usually avoided (Kleppmann's "Designing Data-Intensive Applications" covers both) explains the trade the outbox makes: at-least-once delivery with idempotent consumers instead of impossible cross-system exactly-once.
