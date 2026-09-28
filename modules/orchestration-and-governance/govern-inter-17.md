---
id: govern-inter-17
title: Dedup retries by an idempotency key — or a lost ack makes the effect apply twice
topic: orchestration-and-governance
level: intermediate
status: ready
time: 19 min
summary: A side-effecting request travels over an unreliable link. The service does the work and sends an ack; the ack is lost. The client, seeing no reply, retries — and the same logical request arrives again. A plain handler does the work a second time: a double charge, a duplicate email, a counter off by one. Each application is correct in isolation; the failure is that "do the work" and "at most once" are different requirements. An idempotency key fixes it — the client stamps each logical request with a stable key and reuses it on every retry, and the service applies a key's effect only the first time it sees it. On a six-request stream with three distinct keys, a naive handler totals 48; the keyed handler totals 23, the correct sum of the three logical requests.
eli5: Imagine mailing a check and never getting a receipt, so you mail another — now the store might cash both. If every check has the same serial number, the store can say "already cashed this one" and ignore the copy. An idempotency key is that serial number: it lets a service tell a real new request from a nervous repeat, so your action counts exactly once no matter how many times it is sent.
---

## Why this module

Retries are not optional — a client that never got an ack cannot know whether the work happened, so it must resend — and that is exactly what makes side effects dangerous.

The link between client and service is unreliable in both directions. The request can be lost, but so can the ack. When the ack is lost, the service already did the work; the client, seeing silence, retries. A plain handler treats the retry as a fresh request and does the work again. Now the effect has happened twice: two charges, two emails, a counter that is wrong. Nothing in the handler is buggy — each application is individually correct. The gap is that the handler was built to satisfy "do the work" when the real requirement is "apply the effect at most once per logical request."

**A retry is indistinguishable from a new request unless the request carries something that says which logical operation it is.**

That something is an idempotency key. The client stamps each logical request with a stable key and reuses it on every retry; the service remembers which keys it has applied and turns repeats into no-ops. This module builds a naive handler and a keyed handler on one retry-laden stream and measures the double-apply.

## Concepts

An **idempotency key** is a client-generated identifier for one logical request — a UUID minted once, before the first send, and reused byte-for-byte on every retry of that same request. Two different logical requests get two different keys; a request and its retries share one.

The service keeps a **seen set** (in production, a durable table with the key as primary key). On each arrival it checks the key. First time: do the work, record the key, return the result. Seen before: skip the work, return the stored result. The effect is applied exactly once per key, regardless of arrival count.

The **naive handler** has no such memory. It applies every arrival, so N retries of one request apply the effect N times.

The distinction being tested is not "did the total come out round." It is structural: the gap between the naive total and the keyed total must equal exactly the amount contributed by duplicate arrivals — nothing from the first arrival of any key, everything from the repeats.

**An idempotency key moves the dedup responsibility to a stable identifier the client controls, so the service can be safe to retry without guessing.**

The whole hazard is one lost message: the work succeeded, but the ack never made it back, so the client resends the same key.

<svg role="img" aria-label="Client sends request, service does work, ack is lost, client retries same key, service returns stored result without redoing work" viewBox="0 0 300 140" width="300" height="140">
  <text x="20" y="20" fill="var(--muted)" font-size="9">client</text>
  <text x="230" y="20" fill="var(--muted)" font-size="9">service</text>
  <line x1="45" y1="25" x2="45" y2="130" stroke="var(--grid)" stroke-width="1"/>
  <line x1="255" y1="25" x2="255" y2="130" stroke="var(--grid)" stroke-width="1"/>
  <line x1="45" y1="40" x2="253" y2="48" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="70" y="40" fill="var(--muted)" font-size="8">key r1 → work done</text>
  <line x1="253" y1="58" x2="150" y2="70" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="3 2"/>
  <text x="150" y="80" fill="var(--s2)" font-size="8">ack ✗ lost</text>
  <line x1="45" y1="92" x2="253" y2="100" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="60" y="92" fill="var(--muted)" font-size="8">retry key r1 → no-op</text>
  <line x1="253" y1="110" x2="47" y2="122" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="80" y="120" fill="var(--muted)" font-size="8">stored result re-acked</text>
</svg>
^ The work happened once; the lost ack triggers a retry with the same key, and the service replays the stored result instead of doing the work again.

Idempotency is a property of the effect, not just the handler. A key makes a non-idempotent effect (charge, append) safe by gating it. Some effects are naturally idempotent — "set balance to 50" is safe to repeat — and need no key; the key is for the ones that are not.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-17/idempotent.py

The fixture is a stream of requests. Three logical requests, but r1 was retried twice and r2 once, so six arrive.

```json filename=modules/orchestration-and-governance/code/govern-inter-17/ledger.json:1-11 COMPLETE
{
  "_meta": "A stream of side-effecting requests arriving at a service. Each has a key (the idempotency key identifying one logical request) and an amount (the effect, e.g. a charge). A retry re-sends the SAME key because the client never saw the ack -- so several entries share a key. The service must apply each logical request's effect exactly once.",
  "requests": [
    {"key": "r1", "amount": 10},
    {"key": "r1", "amount": 10},
    {"key": "r2", "amount": 5},
    {"key": "r3", "amount": 8},
    {"key": "r2", "amount": 5},
    {"key": "r1", "amount": 10}
  ]
}
```

The two handlers are five lines apart. The naive one sums every arrival; the keyed one applies a key's amount only the first time it is seen.

```python filename=modules/orchestration-and-governance/code/govern-inter-17/idempotent.py:40-52 COMPLETE
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
```

Run `--apply` and watch the two running totals diverge exactly at each retry.

```text filename=--apply
APPLY — running total after each request (naive applies all, keyed dedups)
----------------------------------------------------------------
  #  key   amount   naive   keyed   note
  1  r1       10      10      10   
  2  r1       10      20      10   retry -> no-op
  3  r2        5      25      15   
  4  r3        8      33      23   
  5  r2        5      38      23   retry -> no-op
  6  r1       10      48      23   retry -> no-op
----------------------------------------------------------------
  naive total 48 overshoots; keyed total 23 matches the 3 logical requests.
```

Every row marked "retry" is where the naive column jumps and the keyed column holds flat. The keyed handler recognizes r1 at rows 2 and 6, and r2 at row 5, and does nothing. Naive ends at 48; keyed ends at 23 — one amount per logical request.

<svg role="img" aria-label="Two running totals over six requests: naive climbs to 48, keyed steps to 23 and holds flat on retries" viewBox="0 0 300 150" width="300" height="150">
  <line x1="35" y1="15" x2="35" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <line x1="35" y1="120" x2="285" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <text x="10" y="25" fill="var(--muted)" font-size="8">48</text>
  <text x="10" y="70" fill="var(--muted)" font-size="8">23</text>
  <polyline points="45,110 85,110 125,100 165,84 205,74 245,64 245,64" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="250" y="60" fill="var(--s1)" font-size="8">naive 48</text>
  <polyline points="45,110 85,110 125,100 165,84 205,84 245,84" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="250" y="90" fill="var(--s2)" font-size="8">keyed 23</text>
  <text x="60" y="135" fill="var(--muted)" font-size="8">1    2    3    4    5    6   (request #)</text>
</svg>
^ The naive total climbs on every arrival; the keyed total steps up on a new key and stays flat on a retry — the flats are requests 2, 5, and 6.

## Build

The `--keys` view collapses the stream to its distinct keys and the once-only amount each applies.

```python filename=modules/orchestration-and-governance/code/govern-inter-17/idempotent.py:55-66 COMPLETE
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
```

```text filename=--keys
KEYS — distinct keys, arrivals, and the once-only applied amount
----------------------------------------------------------------
  r1    arrived 3 time(s)   applies 10 once
  r2    arrived 2 time(s)   applies 5 once
  r3    arrived 1 time(s)   applies 8 once
----------------------------------------------------------------
  6 requests arrived, 3 distinct keys, 3 duplicate arrivals.
```

Six arrivals, three distinct keys, three duplicate arrivals. Each key applies its amount once: 10 + 5 + 8 = 23. The three duplicates account for exactly the 25 the naive handler over-applied (two extra r1 at 10, one extra r2 at 5).

<svg role="img" aria-label="Key r1 arrived 3 times, r2 twice, r3 once; each applies once under the keyed handler" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="25" fill="var(--muted)" font-size="9">r1</text>
  <rect x="40" y="15" width="18" height="14" fill="var(--s2)"/>
  <rect x="60" y="15" width="18" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/>
  <rect x="80" y="15" width="18" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/>
  <text x="110" y="25" fill="var(--muted)" font-size="8">applies 10 (2 retries dropped)</text>
  <text x="10" y="55" fill="var(--muted)" font-size="9">r2</text>
  <rect x="40" y="45" width="18" height="14" fill="var(--s2)"/>
  <rect x="60" y="45" width="18" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/>
  <text x="110" y="55" fill="var(--muted)" font-size="8">applies 5 (1 retry dropped)</text>
  <text x="10" y="85" fill="var(--muted)" font-size="9">r3</text>
  <rect x="40" y="75" width="18" height="14" fill="var(--s2)"/>
  <text x="110" y="85" fill="var(--muted)" font-size="8">applies 8 (no retry)</text>
  <text x="40" y="108" fill="var(--muted)" font-size="8">filled = applied · dashed = no-op retry</text>
</svg>
^ Each key applies its effect on the first (filled) arrival; every later (dashed) arrival is a no-op — the dashed boxes are the 25 the naive handler wrongly counted.

## Definition of done

The self-test pins the structural claims: duplicates exist, naive over-applies, keyed matches the correct total, the keyed total is one-amount-per-key, and the naive/keyed gap equals exactly the retried amounts.

```python filename=modules/orchestration-and-governance/code/govern-inter-17/idempotent.py:114-132 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive handler double-applies retried keys; the keyed handler applies each exactly once
--------------------------------------------------------------------------------------------------------
  the stream contains retried (duplicate) keys = True ({'r1': 3, 'r2': 2})
  the naive handler applies too much = True (naive 48 vs correct 23)
  the keyed handler matches the correct total = True (keyed 23 vs correct 23)
  the keyed total equals one amount per distinct key = True
  the gap naive-keyed equals exactly the retried amounts = True (25)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  duplicates_present=True  naive_overshoots=True  keyed_correct=True  keyed_applies_each_once=True  retries_are_noops=True
```

**Done means the over-apply is accounted for, not just avoided: the naive/keyed gap of 25 equals exactly the retried amounts, proving the key dropped repeats and nothing else.**

## Boss fight

The keyed handler stores a key the first time it applies it. Predict what happens if the service crashes after doing the work but before recording the key. It is tempting to say the key protects you — that is the whole point.

It does not, and this is the subtle failure that separates a real idempotency implementation from a toy. If "do the work" and "record the key" are two separate steps, a crash between them loses the record, so the retry finds no key and applies the effect again — the double charge is back. The fix is to make recording the key part of the same atomic commit as the effect (one transaction, the key as a unique constraint), so either both happen or neither. This is the same dual-write hazard the transactional outbox pattern addresses, seen from the dedup side.

The mirror-image mistake is a key that is not stable. If the client mints a fresh key on each retry — say, keyed by a timestamp — then every retry looks like a new logical request and the dedup never fires. The key must be generated once, before the first attempt, and pinned to the logical request, not to the attempt.

```python filename=modules/orchestration-and-governance/code/govern-inter-17/idempotent.py:45-52 COMPLETE
def idempotent_total(requests):
    """Apply a key's effect only the first time it is seen; later arrivals are no-ops."""
    seen, total = set(), 0
    for r in requests:
        if r["key"] not in seen:
            seen.add(r["key"])
            total += r["amount"]
    return total
```

**An idempotency key is only as good as its atomicity and its stability: record it in the same commit as the effect, and mint it once per logical request, or the guarantee silently evaporates.**

## External resources

Stripe's API documentation on idempotent requests — the canonical production design: a client-supplied `Idempotency-Key` header, a stored result, and a defined window, on exactly the double-charge scenario here.

Brandon Byars, "Enterprise Integration Using Idempotent Receiver" (and the Hohpe/Woolf "Enterprise Integration Patterns" Idempotent Receiver entry) — the messaging framing of dedup on redelivery.

The AWS "Making retries safe with idempotent APIs" builder's-library article — atomicity of the effect-plus-key write, key stability, and expiry, the exact pitfalls in the boss fight.
