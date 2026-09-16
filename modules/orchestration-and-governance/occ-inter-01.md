---
id: occ-inter-01
title: Guard a read-modify-write with a version check — two clients that both read then write blindly lose one update, and a compare-and-swap prevents it
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: Updating a shared record usually means read-modify-write: read the current value, compute a new one from it, write it back. That is three steps, and between the read and the write someone else can write. If your write is blind — it just stores your value — you overwrite whatever landed in between as if it were never there. So two clients that both read the same starting value and both write back produce a lost update: each computed from the same old value, unaware of the other, and the one that writes second overwrites the first, whose change simply vanishes with nothing errored. On the fixture the record starts at 100, client A subtracts 10 and client B subtracts 5 (applied A then B), so the correct result is 85 — but a blind write leaves 95, A's subtraction lost. Optimistic concurrency control fixes it without a lock: the client remembers the version it read and sends it with the write as an expected version, and the store performs a compare-and-swap — it applies the write only if the record is still at that version, and rejects it otherwise. A rejection is information: it means someone wrote since you read, so your value is stale. The rejected client re-reads the now-current value, re-applies its change to that, and writes again against the fresh version, which succeeds. On the fixture A's compare-and-swap at version 1 is accepted (90, version 2), B's compare-and-swap at version 1 is rejected because the store moved to version 2, and B re-reads 90 and retries to reach the correct 85 — both changes land, in a serialized order, with no lock held. The rule: never write back a value you read without checking the record is still at the version you read, or a concurrent update is silently lost.
eli5: Imagine two people editing the same shared shopping list on paper by copying it, crossing off one item each, and handing back their copy. The first hands back a list with milk crossed off; the second, who copied the original before that, hands back a list with eggs crossed off — and since the second copy replaces the first, milk is uncrossed again, as if nobody ever removed it. One person's change is lost, and no one notices. The fix is to number the list: each person notes "I copied version 3," and when they hand it back the keeper only accepts it if the list is still version 3. The second person's "version 3" is rejected because the list is now version 4, so they grab the current version and redo their change on it — and now both items stay crossed off.
---

## Why this module

A shared counter, an inventory total, a document, a user's balance — anything updated by reading it and writing back a new value has a race hiding in plain sight. The read and the write are two separate operations, and correctness silently assumes nothing changed the record in between. Under concurrency, something does.

When it does, a blind write does not fail — it succeeds at doing the wrong thing. It stores a value computed from data that is now stale, overwriting a change it never saw. The record ends up internally consistent and externally wrong: a count that should be 85 reads 95, and there is no error, no exception, no log line, because every individual operation did exactly what it was told.

This module runs two clients that both decrement the same record and shows the blind version losing an update — the final value is 95 when it should be 85. Then it adds a version to the record and a compare-and-swap to the write, so the second writer's stale write is rejected, it retries against the fresh value, and both decrements land at the correct 85. The whole fix is checking, at write time, that the record is still what you read.

**A blind read-modify-write assumes the world held still between the read and the write, and under concurrency that assumption fails silently — losing an update with no error, because each step individually succeeded.**

## Concepts

The lost update is a specific interleaving. Client A reads the value; client B reads the same value before A writes; A writes its result; B writes its result over A's. Because B computed from the pre-A value and B wrote last, B's write erases A's change. Both reads saw the same number, both writes succeeded, and exactly one update survives. Nothing about either client's actions was wrong in isolation; the defect is that a read and its dependent write were not atomic.

Locking is one fix — hold a lock across the read and the write so no one interleaves — but it serializes access and blocks other clients even when they would not have conflicted, and under low contention that is mostly wasted waiting. Optimistic concurrency control takes the opposite bet: assume conflicts are rare, do not lock, and detect a conflict at write time instead of preventing it up front.

Detection needs a version. The record carries a version number that increments on every accepted write, and a client that reads the record reads its version too. When the client writes, it sends that version back as the version it expects the record to still be at. The store does a compare-and-swap: if the record's current version equals the expected version, no one has written since the read, so the write is applied and the version bumped; if the versions differ, someone has written, the client's value is based on stale data, and the write is rejected.

A rejection is not a failure to handle and move on from — it is the signal that the optimistic bet lost this round. The correct response is to re-read the record (getting the current value and version), re-apply the change to that fresh value, and write again against the new version. This retry loop is what makes the two changes serialize: the second writer, forced to recompute from the first writer's result, adds its change on top instead of erasing it.

<svg role="img" aria-label="A timeline of two clients updating a record that starts at 100. Client A reads 100 and writes 90. Client B reads 100 (before A's write) and writes 95, which overwrites A's 90. The final value is 95, and A's subtraction of 10 is marked lost" viewBox="0 0 640 220">
<line x1="60" y1="60" x2="600" y2="60" stroke="var(--line)" stroke-width="1"/>
<text x="40" y="64" fill="var(--muted)" font-size="10" text-anchor="end">A</text>
<line x1="60" y1="150" x2="600" y2="150" stroke="var(--line)" stroke-width="1"/>
<text x="40" y="154" fill="var(--muted)" font-size="10" text-anchor="end">B</text>
<circle cx="140" cy="60" r="5" fill="var(--ink)"/>
<text x="140" y="46" fill="var(--muted)" font-size="10" text-anchor="middle">read 100</text>
<circle cx="180" cy="150" r="5" fill="var(--ink)"/>
<text x="180" y="172" fill="var(--muted)" font-size="10" text-anchor="middle">read 100</text>
<circle cx="360" cy="60" r="5" fill="var(--s1)"/>
<text x="360" y="46" fill="var(--muted)" font-size="10" text-anchor="middle">write 90</text>
<circle cx="480" cy="150" r="5" fill="var(--s2)"/>
<text x="480" y="172" fill="var(--muted)" font-size="10" text-anchor="middle">write 95</text>
<line x1="360" y1="66" x2="475" y2="144" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="3 2"/>
<text x="450" y="105" fill="var(--s2)" font-size="10">overwrites A</text>
<text x="330" y="205" fill="var(--ink)" font-size="11" text-anchor="middle">final = 95, not 85 — A's −10 is lost</text>
</svg>
^ B read before A wrote, so B's write is computed from the pre-A value and, landing last, overwrites A's change — one of the two updates vanishes.

**The lost update is not caused by a slow or buggy client but by a read and a write that are not atomic, so the fix is to make the write conditional on the record still being what the read saw.**

## Worked example

The fixture is a record at value 100, version 1, and two concurrent deltas applied A then B.

```json filename=modules/orchestration-and-governance/code/occ-inter-01/occ.json:3-6 COMPLETE
  "initial_value": 100,
  "initial_version": 1,
  "client_a_delta": -10,
  "client_b_delta": -5
```

A compare-and-swap applies the write only when the record is still at the expected version.

```python filename=modules/orchestration-and-governance/code/occ-inter-01/occ.py:42-48 COMPLETE
def cas_write(store, value, expected_version):
    """Compare-and-swap: apply the write only if the record is still at the version the client read."""
    if store["version"] != expected_version:
        return {"accepted": False, "current_version": store["version"], "current_value": store["value"]}
    store["value"] = value
    store["version"] += 1
    return {"accepted": True}
```

The blind path has both clients read the start value and write back, with no version check.

```python filename=modules/orchestration-and-governance/code/occ-inter-01/occ.py:51-58 COMPLETE
def run_blind(data):
    """Both clients read the start value, then write their result back blindly, A then B."""
    store = new_store(data)
    a_read = store["value"]                          # A reads 100
    b_read = store["value"]                          # B reads 100 (before A's write lands)
    blind_write(store, a_read + data["client_a_delta"])   # A writes 90
    blind_write(store, b_read + data["client_b_delta"])   # B writes 95, overwriting A
    return store["value"]
```

Running it loses A's update.

```text filename=occ.py --blind
BLIND — both read then overwrite, A then B
------------------------------------------------------------
  start 100; A reads 100, B reads 100 (both before any write lands)
  A writes 90, then B writes 95 (overwriting A)
  final = 95   correct = 85   lost update? True
------------------------------------------------------------
  B never saw A's change, so writing over it dropped A's update
```

The OCC path carries the version each client read and retries the loser.

```python filename=modules/orchestration-and-governance/code/occ-inter-01/occ.py:61-73 COMPLETE
def run_occ(data):
    """Both read the start version; A's CAS succeeds, B's is rejected, B re-reads and retries."""
    store = new_store(data)
    a_val, a_ver = store["value"], store["version"]       # A reads (100, v1)
    b_val, b_ver = store["value"], store["version"]       # B reads (100, v1)
    cas_write(store, a_val + data["client_a_delta"], a_ver)          # A: CAS at v1 -> accepted, 90 v2
    first = cas_write(store, b_val + data["client_b_delta"], b_ver)  # B: CAS at v1, store is v2 -> rejected
    retried = False
    if not first["accepted"]:
        b_val, b_ver = first["current_value"], first["current_version"]   # B re-reads (90, v2)
        cas_write(store, b_val + data["client_b_delta"], b_ver)           # B: CAS at v2 -> accepted, 85 v3
        retried = True
    return store["value"], retried, first["accepted"]
```

Running it rejects B's stale write, retries, and reaches the correct total.

```text filename=occ.py --occ
OCC — compare-and-swap on the version read
------------------------------------------------------------
  A CAS at v1 -> accepted (90)
  B CAS at v1 -> REJECTED (store moved to v2)
  B re-reads the fresh value and retries: True
  final = 85   correct = 85   lost update? False
------------------------------------------------------------
  the rejection told B its read was stale, so it recomputed against the fresh value
```

A's compare-and-swap at version 1 succeeds and moves the record to version 2. B's compare-and-swap, also at version 1, is rejected because the record is now at version 2 — the version mismatch is exactly the detection of A's intervening write. B re-reads the fresh 90 at version 2, subtracts its 5, writes against version 2, and lands 85. The figure traces the version chain.

<svg role="img" aria-label="A version chain. The record at value 100 version 1 receives A's compare-and-swap at expected version 1, accepted, becoming 90 version 2. B's compare-and-swap at expected version 1 is rejected because the record is at version 2. B re-reads 90 version 2 and its compare-and-swap at version 2 is accepted, becoming 85 version 3" viewBox="0 0 640 210">
<rect x="30" y="80" width="90" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="75" y="98" fill="var(--ink)" font-size="11" text-anchor="middle">100</text>
<text x="75" y="112" fill="var(--muted)" font-size="9" text-anchor="middle">version 1</text>
<line x1="120" y1="100" x2="165" y2="100" stroke="var(--s1)" stroke-width="1.5"/>
<polygon points="165,100 157,95 157,105" fill="var(--s1)"/>
<text x="142" y="90" fill="var(--s1)" font-size="9" text-anchor="middle">A@v1 ok</text>
<rect x="165" y="80" width="90" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="210" y="98" fill="var(--ink)" font-size="11" text-anchor="middle">90</text>
<text x="210" y="112" fill="var(--muted)" font-size="9" text-anchor="middle">version 2</text>
<line x1="210" y1="120" x2="210" y2="160" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="3 2"/>
<text x="210" y="178" fill="var(--s2)" font-size="9" text-anchor="middle">B@v1 REJECTED</text>
<line x1="255" y1="100" x2="300" y2="100" stroke="var(--s1)" stroke-width="1.5"/>
<polygon points="300,100 292,95 292,105" fill="var(--s1)"/>
<text x="277" y="90" fill="var(--s1)" font-size="9" text-anchor="middle">B@v2 ok</text>
<rect x="300" y="80" width="90" height="40" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="345" y="98" fill="var(--ink)" font-size="11" text-anchor="middle">85</text>
<text x="345" y="112" fill="var(--muted)" font-size="9" text-anchor="middle">version 3</text>
<text x="500" y="96" fill="var(--muted)" font-size="10" text-anchor="middle">B retried against</text>
<text x="500" y="110" fill="var(--muted)" font-size="10" text-anchor="middle">the fresh value</text>
</svg>
^ Each accepted write bumps the version, so B's version-1 write is rejected the moment A's landed — and B's retry against version 2 serializes its change on top of A's.

**The version mismatch is the whole mechanism: it turns "someone wrote since I read" from an invisible race into an explicit rejection the loser can recover from.**

## Build

The self-test pins both paths: the blind write loses an update, and the compare-and-swap rejects the stale write, retries, and reaches the correct total.

```python filename=modules/orchestration-and-governance/code/occ-inter-01/occ.py:112-119 COMPLETE
    blind_loses_update = blind_final != correct
    print("  the blind read-modify-write loses an update = %s (final %d, correct %d)" % (blind_loses_update, blind_final, correct))

    occ_rejects_stale_write = b_first_ok is False
    print("  compare-and-swap rejects B's stale write = %s" % occ_rejects_stale_write)

    occ_retries = retried is True
    print("  B re-reads and retries against the fresh version = %s" % occ_retries)
```

The remaining flags confirm the compare-and-swap total is correct and both updates were applied. All five pass.

```text filename=occ.py --check
SELF-TEST — the blind path loses an update while the compare-and-swap path rejects the stale write, retries, and gets the correct total
----------------------------------------------------------------------------------------------------------------
  the blind read-modify-write loses an update = True (final 95, correct 85)
  compare-and-swap rejects B's stale write = True
  B re-reads and retries against the fresh version = True
  compare-and-swap reaches the correct total = True (final 85)
  both updates were applied under CAS = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  blind_loses_update=True  occ_rejects_stale_write=True  occ_retries=True  occ_final_correct=True  occ_applied_both=True
```

**The blind final of 95 and the compare-and-swap final of 85 differ by exactly A's lost 10 — the version check did not compute a better answer, it stopped a correct answer from being erased.**

## Definition of done

You are done when every read-modify-write on a shared record is conditioned on the version (or an equivalent token) the read observed, so a concurrent write is detected at commit time and retried rather than silently overwritten.

The building blocks are small and widely available. Give the record a version, revision, or ETag that changes on every write; carry it from the read to the write; and make the write a compare-and-swap — a conditional update that commits only if the stored version still matches (SQL `UPDATE ... WHERE version = ?` returning zero rows on mismatch, an HTTP `If-Match` on the ETag, a database with a `@Version` column, or a compare-and-set on an atomic register). On a rejection, re-read and re-apply, and bound the retries with backoff so a hot record does not spin forever. Two cautions: this is optimistic, so it is the right default only when conflicts are rare — under heavy contention on one key, the constant rejections and retries can cost more than a lock would, and pessimistic locking or a serialized single-writer becomes the better choice. And the retry must recompute from the fresh value, not resubmit the stale one, or it just loses the race again.

<svg role="img" aria-label="A loop: read value and version, compute the new value, write with compare-and-swap on the version. If accepted, done. If rejected, loop back to re-read and recompute." viewBox="0 0 640 190">
<rect x="30" y="76" width="110" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="85" y="94" fill="var(--ink)" font-size="10" text-anchor="middle">read value +</text>
<text x="85" y="108" fill="var(--muted)" font-size="10" text-anchor="middle">version</text>
<line x1="140" y1="96" x2="180" y2="96" stroke="var(--line)" stroke-width="1"/>
<polygon points="180,96 172,91 172,101" fill="var(--line)"/>
<rect x="180" y="76" width="110" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="235" y="100" fill="var(--ink)" font-size="10" text-anchor="middle">compute new</text>
<line x1="290" y1="96" x2="330" y2="96" stroke="var(--line)" stroke-width="1"/>
<polygon points="330,96 322,91 322,101" fill="var(--line)"/>
<rect x="330" y="72" width="130" height="48" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="395" y="92" fill="var(--ink)" font-size="10" text-anchor="middle">write if version</text>
<text x="395" y="106" fill="var(--ink)" font-size="10" text-anchor="middle">still matches</text>
<line x1="460" y1="88" x2="520" y2="88" stroke="var(--s1)" stroke-width="1"/>
<text x="540" y="91" fill="var(--s1)" font-size="10" text-anchor="middle">accept → done</text>
<path d="M 395 120 L 395 155 L 85 155 L 85 116" fill="none" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="4 3"/>
<polygon points="85,116 80,124 90,124" fill="var(--s2)"/>
<text x="235" y="150" fill="var(--s2)" font-size="10" text-anchor="middle">reject → re-read and recompute</text>
</svg>
^ Read the version, compute, and commit only if the version still matches; a rejection sends you back to re-read and recompute against the fresh value.

**Optimistic concurrency does not prevent the conflict, it detects it at the last possible moment and makes the loser redo its work — which is cheaper than a lock exactly when conflicts are rare, and worse than one when they are not.**

## Boss fight

Your turn: make the conflict a three-way pile-up and watch the retries chain. Add a client C that also reads at version 1 and subtracts 20. Now A commits at version 1, B is rejected and retries at version 2, and C — which also read version 1 — is rejected, and after its retry may be rejected again if B committed in between, so it retries once more. Each writer eventually commits against a fresh version, and the final value is the correct 100 − 10 − 5 − 20 = 65, but the number of retries grows with the number of concurrent writers on the same key. This is the honest cost of optimism: under contention the work is redone, not waited on, and a very hot key can spend more effort retrying than it would have spent holding a lock.

Then break the retry to see the subtle wrong fix. Suppose B, on rejection, resubmits its original value (95) instead of recomputing from the fresh value — a compare-and-swap that retries with the stale result. If the store checks the version, the resubmission is rejected again (still stale), so B spins; but if a tired engineer "fixes" the spinning by dropping the version check on the retry, B writes 95 over A's 90 and the update is lost after all, defeating the whole mechanism. The compare-and-swap only works if the retry both recomputes from the fresh value and keeps checking the version — a retry that does either half-way reintroduces the lost update it was meant to stop. The discipline is that the version travels with the value through every attempt, and each attempt derives its value from the version it is about to check.

**Optimistic concurrency's correctness lives entirely in the retry: recompute from the fresh value and re-check the version every time, because a retry that resubmits stale data or skips the check is a lost update wearing a compare-and-swap's clothes.**

## External resources

Most databases and ORMs implement this as "optimistic locking" with a version column — Hibernate's `@Version`, Django's and Rails' patterns, and the SQL `UPDATE ... WHERE version = ?` idiom — and their documentation is the practical guide to wiring it into an application.

HTTP's conditional requests (`ETag` with `If-Match`, returning `412 Precondition Failed` on a mismatch) are optimistic concurrency for web resources, and the MDN and RFC 7232 write-ups explain the same read-version-then-conditional-write flow over the network.

Herlihy and Shavit's "The Art of Multiprocessor Programming" covers compare-and-swap as the primitive underneath lock-free algorithms, connecting this record-level pattern to the hardware CAS instruction it is named after.
