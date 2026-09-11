---
id: harness-inter-08
title: A retried tool call must be idempotent — dedup on the key, not the content
topic: agent-harness
level: intermediate
status: ready
time: 24 min
summary: A tool call whose acknowledgement is lost gets retried, so the same operation arrives twice. Applying both double-charges the customer; deduping on the call's content drops a genuinely separate charge. Only a client-supplied idempotency key applies each operation exactly once.
eli5: If you tell someone "pay the shop $10" and don't hear back, you might say it again — and they might pay twice. So you write a ticket number on the request. The shop keeps a list of numbers it has already done, and if your number is on the list it just says "already done" instead of paying again.
---

## Why this module

An agent that calls the outside world will, sooner or later, not hear back.

The call left the harness, reached the service, and the side effect happened — a row was written, a card was charged, a message was sent. Then the response was dropped on the way home: a dropped packet, a load balancer that recycled the connection, a lambda that timed out one millisecond after committing. The harness sees a timeout. And here is the cruel part: a timeout tells you nothing. "Never arrived" and "arrived, but the ack was lost" produce the exact same silence. The harness cannot tell them apart, so it does the only safe-looking thing and retries.

Now the same logical operation is in the stream twice. If the service on the other end applies whatever it receives, the customer is charged twice, the email goes out twice, the ticket is filed twice. This is not a rare corner; it is the default outcome of a network that is allowed to drop a message, which every network is. Retries are not the bug — retries are correct, and you want them. The bug is a service that treats a retry as a new request.

<svg role="img" aria-label="A timeline: client sends a call, the service applies the effect, the acknowledgement is dropped, the client times out and retries the identical call" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="40" y="24" font-family="var(--mono)" font-size="12" fill="var(--muted)">client</text>
  <text x="380" y="24" font-family="var(--mono)" font-size="12" fill="var(--muted)">service</text>
  <line x1="70" y1="32" x2="70" y2="185" stroke="var(--grid)"/>
  <line x1="400" y1="32" x2="400" y2="185" stroke="var(--grid)"/>
  <line x1="70" y1="52" x2="400" y2="66" stroke="var(--ink)"/>
  <text x="120" y="50" font-family="var(--mono)" font-size="11" fill="var(--ink)">charge 10 (key k1)</text>
  <text x="300" y="86" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">effect applied ✓</text>
  <line x1="400" y1="92" x2="230" y2="104" stroke="var(--s2)" stroke-dasharray="5 4"/>
  <text x="240" y="118" font-family="var(--mono)" font-size="11" fill="var(--s2)">ack dropped ✕</text>
  <text x="16" y="140" font-family="var(--mono)" font-size="11" fill="var(--muted)">timeout — no ack</text>
  <line x1="70" y1="150" x2="400" y2="164" stroke="var(--ink)"/>
  <text x="110" y="148" font-family="var(--mono)" font-size="11" fill="var(--ink)">RETRY: charge 10 (key k1)</text>
  <text x="270" y="182" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">same key → no-op</text>
</svg>
^ The effect happens once; the ack is lost, so the client times out and retries the identical call. The retry carries the same key, so a fenced service applies nothing the second time.

This module builds the smallest thing that gets it right and, just as important, the plausible fix that gets it wrong. The wrong fix — dedup on what the call looks like — is the one people reach for first, and it fails silently in the one case that matters. We will charge a customer 40, then 15, then finally the correct 25, and read off exactly why.

**A retry is not a new request; a service that cannot tell the difference will either double-apply it or, trying not to, drop something real.**

## Concepts

Start with the one word that makes this tractable: idempotent. An operation is idempotent if applying it twice lands in the same state as applying it once. Setting a flag to `true` is idempotent — set it again, nothing moves. Adding 10 to a balance is not — do it twice and you are 10 too high. Most useful side effects are the second kind, so we cannot rely on the operation being naturally safe to repeat. We have to make repetition safe from the outside.

The tool for that is an idempotency key. The client — here, the harness — stamps every operation with a key at the moment it first decides to do it. The key has two properties and they are the whole game. It is stable across that operation's own retries: the first attempt and every retry of the same intent carry the same key. And it is distinct across different operations: two things the harness genuinely means to do separately get two different keys, even if they look identical.

The service keeps a record of keys it has already applied. When a call arrives, it checks the key. New key: apply the effect, remember the key, return the result. Seen key: do not apply anything, return the result it already produced. A retry becomes a no-op that still answers. That is idempotency bolted on from the client side, and it works for any operation, idempotent by nature or not.

The trap is to skip the key and dedup on the content of the call instead — same operation, same amount, must be a duplicate. It reads as equivalent and it is not. Two customers, or one customer twice on purpose, can each be charged the same amount for different reasons. Those calls have identical content and are emphatically not duplicates. Content-dedup collapses them into one and eats a real charge — and it does so quietly, because from the inside it looks exactly like the deduplication working.

**The key encodes the client's intent to do this once; the content only encodes what the operation looks like, and two different intents can look the same.**

## Worked example

The fixture is a stream of attempts a harness sent to a charging service. It is hand-authored so the two failure modes are exact and the honest answer is checkable.

```json filename=modules/agent-harness/code/harness-inter-08/attempts.json:8-12 COMPLETE
    {"key": "k1", "op": "charge", "amount": 10, "note": "first attempt"},
    {"key": "k1", "op": "charge", "amount": 10, "note": "retry -- the ack for k1 was lost"},
    {"key": "k2", "op": "charge", "amount": 10, "note": "a genuinely separate charge, same amount, different key"},
    {"key": "k3", "op": "charge", "amount": 5,  "note": "first attempt"},
    {"key": "k3", "op": "charge", "amount": 5,  "note": "retry -- the ack for k3 was lost"}
```

Read it slowly, because the whole lesson is in the shape. Five attempts, three distinct keys. `k1` appears twice — a retry after its ack was lost. `k3` appears twice — same story. `k2` appears once, and it charges 10, the same amount as `k1`. That is the load-bearing detail: `k2` is a real, separate charge that happens to cost what `k1` costs. The true total is the sum over distinct keys: 10 + 10 + 5 = 25.

Before running anything, predict. The naive service applies every attempt. What does it charge?

<svg role="img" aria-label="The attempt stream, five rows, with k1 and k3 marked as retries and k2 marked as a separate charge" viewBox="0 0 460 210" width="460" height="210">
  <rect x="0" y="0" width="460" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="26" font-family="var(--mono)" font-size="12" fill="var(--muted)">arrival order →</text>
  <rect x="16" y="40" width="120" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="24" y="59" font-family="var(--mono)" font-size="12" fill="var(--acc-ink)">k1  charge 10</text>
  <rect x="16" y="72" width="120" height="30" fill="var(--panel)" stroke="var(--line)"/>
  <text x="24" y="91" font-family="var(--mono)" font-size="12" fill="var(--ink)">k1  charge 10</text>
  <text x="150" y="91" font-family="var(--mono)" font-size="11" fill="var(--muted)">retry of k1 — same key</text>
  <rect x="16" y="104" width="120" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="24" y="123" font-family="var(--mono)" font-size="12" fill="var(--acc-ink)">k2  charge 10</text>
  <text x="150" y="123" font-family="var(--mono)" font-size="11" fill="var(--muted)">separate charge — same amount, new key</text>
  <rect x="16" y="136" width="120" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="24" y="155" font-family="var(--mono)" font-size="12" fill="var(--acc-ink)">k3  charge 5</text>
  <rect x="16" y="168" width="120" height="30" fill="var(--panel)" stroke="var(--line)"/>
  <text x="24" y="187" font-family="var(--mono)" font-size="12" fill="var(--ink)">k3  charge 5</text>
  <text x="150" y="187" font-family="var(--mono)" font-size="11" fill="var(--muted)">retry of k3 — same key</text>
</svg>
^ Five attempts arrive; the shaded rows are the three distinct operations, the plain rows are retries. The honest total counts one shaded row per key: 10 + 10 + 5 = 25.

Here is the naive service. It applies whatever it is handed.

```python filename=modules/agent-harness/code/harness-inter-08/idempotency.py:42-48 COMPLETE
def apply_all(attempts):
    """Apply every attempt -- a retry is charged again, so a lost ack costs the customer twice."""
    total, log = 0, []
    for a in attempts:
        total += a["amount"]
        log.append((a["key"], a["amount"], "applied", total))
    return total, log
```

Now the plausible fix — dedup on the content, `(op, amount)`. If we have already seen a charge of 10, skip the next charge of 10.

```python filename=modules/agent-harness/code/harness-inter-08/idempotency.py:51-62 COMPLETE
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
```

And the correct one — dedup on the key. If the key has been applied, it is a no-op; otherwise apply and remember the key.

```python filename=modules/agent-harness/code/harness-inter-08/idempotency.py:65-76 COMPLETE
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
```

The difference between the two dedup functions is one line: `sig = (a["op"], a["amount"])` versus `a["key"]`. That one line is the entire module. Run all three side by side.

```text filename=modules/agent-harness/code/harness-inter-08/idempotency.py --apply
  apply every attempt:
    k1    10  applied                -> total 10
    k1    10  applied                -> total 20
    k2    10  applied                -> total 30
    k3     5  applied                -> total 35
    k3     5  applied                -> total 40
    final total: 40
  dedup on content:
    k1    10  applied                -> total 10
    k1    10  skipped (same content) -> total 10
    k2    10  skipped (same content) -> total 10
    k3     5  applied                -> total 15
    k3     5  skipped (same content) -> total 15
    final total: 15
  dedup on the key:
    k1    10  applied                -> total 10
    k1    10  no-op (key seen)       -> total 10
    k2    10  applied                -> total 20
    k3     5  applied                -> total 25
    k3     5  no-op (key seen)       -> total 25
    final total: 25
```

Apply-all charges 40 — the two retries cost an extra 15, exactly what a double-apply predicts. Content-dedup charges 15, and this is the one to sit with. It caught both retries correctly, and then it also skipped `k2`, because `k2`'s content `(charge, 10)` had already been seen on `k1`. It refused a real charge. The customer who owed 25 was billed 15, and every log line says "skipped (same content)" as if that were the right thing. Key-dedup charges 25: `k1` applies, its retry is a no-op, `k2` applies because its key is new, `k3` applies, its retry is a no-op. The line that reads `k2 applied -> total 20` is the whole difference between the two dedup strategies.

<svg role="img" aria-label="Three final totals: apply-all 40 overcharges, content-dedup 15 undercharges, key-dedup 25 correct" viewBox="0 0 460 200" width="460" height="200">
  <rect x="0" y="0" width="460" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <line x1="150" y1="20" x2="150" y2="150" stroke="var(--grid)"/>
  <text x="16" y="45" font-family="var(--mono)" font-size="12" fill="var(--ink)">apply-all</text>
  <rect x="150" y="32" width="240" height="24" fill="var(--s1)" stroke="var(--line)"/>
  <text x="398" y="49" font-family="var(--mono)" font-size="12" fill="var(--ink)">40</text>
  <text x="16" y="93" font-family="var(--mono)" font-size="12" fill="var(--ink)">content</text>
  <rect x="150" y="80" width="90" height="24" fill="var(--s2)" stroke="var(--line)"/>
  <text x="248" y="97" font-family="var(--mono)" font-size="12" fill="var(--ink)">15</text>
  <text x="16" y="141" font-family="var(--mono)" font-size="12" fill="var(--ink)">key</text>
  <rect x="150" y="128" width="150" height="24" fill="var(--acc-line)" stroke="var(--line)"/>
  <text x="308" y="145" font-family="var(--mono)" font-size="12" fill="var(--acc-ink)">25</text>
  <line x1="300" y1="20" x2="300" y2="165" stroke="var(--acc-ink)" stroke-dasharray="4 3"/>
  <text x="306" y="180" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">true total = 25</text>
</svg>
^ Apply-all overshoots the true total by the cost of the retries; content-dedup undershoots by eating k2; only key-dedup lands on the dashed line.

The correct total comes from one honest definition — each distinct key, counted once — and nothing else in the file computes it, so the self-test has an independent yardstick to check against.

```python filename=modules/agent-harness/code/harness-inter-08/idempotency.py:78-81 COMPLETE
def true_total(attempts):
    """The correct total: each distinct key's amount, counted once."""
    by_key = {a["key"]: a["amount"] for a in attempts}
    return sum(by_key.values())
```

## Build

Wire the artifact yourself and reproduce the three totals. The whole thing is standard library — no keys, no spend, no network.

Run `python3 idempotency.py --attempts` first to see the stream and confirm five attempts, three distinct keys. Then `--apply` for the table above, then `--check` for the self-test. The numbers you get must match this module character for character; if they do not, the fixture was edited and the prose is now lying.

The self-test is where the planted failure earns its place. It does not just assert that key-dedup is right — it asserts that the plausible-but-wrong strategy is wrong, and wrong in the specific direction that hurts.

```python filename=modules/agent-harness/code/harness-inter-08/idempotency.py:127-130 COMPLETE
    t_content, _ = apply_dedup_content(attempts)
    content_drops = t_content < true
    print("  deduping on content undercharges (drops a real charge) = %s (total %d, should be %d)"
          % (content_drops, t_content, true))
```

The predicate is `t_content < true`, not `t_content != true`. That is deliberate. A strict-less-than pins down the direction: content-dedup does not merely disagree with the truth, it undershoots, because its only failure mode is dropping a charge it mistook for a duplicate. If someone "fixes" the fixture so that content-dedup happens to land on 25 by luck, this line goes False and the self-test fails loudly. Here is the full gate.

```text filename=modules/agent-harness/code/harness-inter-08/idempotency.py --check
SELF-TEST — apply-all overcharges, content-dedup drops a real charge, key-dedup is exact
--------------------------------------------------------------------------
  applying every attempt overcharges = True (total 40, should be 25)
  deduping on content undercharges (drops a real charge) = True (total 15, should be 25)
  deduping on the key hits the true total exactly = True (total 25)
  every retry became a no-op under key-dedup = True (2 no-ops)
--------------------------------------------------------------------------
SELF-TEST PASS  overcharges=True  content_drops=True  key_exact=True  retries_are_noops=True
```

Four independent claims, all True. Overcharges checks the naive service is unsafe. Content_drops checks the tempting fix loses money. Key_exact checks the real fix is exact. Retries_are_noops checks that the two extra attempts — and only those two — became no-ops, so key-dedup did not accidentally get the total right by skipping the wrong rows.

**The self-test does not just bless the right answer; it convicts the wrong one in the exact direction it fails.**

## Definition of done

You are done when the artifact reproduces every number here and you can say, without looking, why each one comes out the way it does.

Concretely: `--apply` prints 40, 15, and 25 in that order. `--check` prints SELF-TEST PASS with all four flags True. You can point at the single line — `k2 applied -> total 20` in the key-dedup log — that content-dedup gets wrong, and explain that it is wrong because `k2` shares content with `k1` but not intent. You can state the two properties of an idempotency key (stable across retries, distinct across operations) and say which property content-dedup violates: the second one, distinctness, by treating same-content calls as the same operation.

If you can do that, you have the mental model that scales past this toy: the key belongs to the client, it is minted once per intended operation, and the server's whole job is to remember keys and refuse to apply one twice.

## Boss fight

Here is where the plausible engineer gets it wrong, and it is worth walking into the trap deliberately.

They ship content-dedup. It passes their tests, because their tests never include two legitimately-identical operations — every test charge is a different amount. It runs in production for a month and looks perfect: retries are absorbed, no double-charges, the on-call is quiet. Then a customer buys two identical $10 items in the same minute, or two different customers are each charged the same subscription fee, and one of those charges silently vanishes. Revenue is short and nothing errored. The logs proudly say "skipped (same content)". This is the worst kind of bug — the kind that looks like the feature working.

Your turn: extend the fixture with a fourth key `k4` that charges 5 — the same amount as `k3` — as a genuinely separate operation, appearing once. Predict all three totals before you run. Apply-all should climb by 5 to 45. Key-dedup should climb by 5 to 30, because `k4` is a new key. Content-dedup should not move from 15, because `(charge, 5)` was already seen on `k3` — so it now drops two real charges, `k2` and `k4`, and the gap between it and the truth widens to 15. If your prediction and the run disagree, the model in your head is wrong, not the code; find the row you mispredicted and reconcile it.

Then the deeper question: what does the server's key store cost? It has to remember every key it has ever applied, or a retry that arrives late — after the entry expired — will be treated as new and applied again. Real systems bound this with a retention window (keys live for, say, 24 hours, longer than any client will retry) and require the client to stop retrying before the window closes. There is no free lunch; there is a window you size against your retry policy.

## External resources

Stripe's API reference on idempotent requests is the canonical practitioner's treatment: keys in a header, a 24-hour retention window, and the explicit rule that the key must be generated by the client per logical operation.

The AWS Builders' Library article "Making retries safe with idempotent APIs" walks through the lost-ack problem and the token store from the server's side, including the retention-window tradeoff.

For the theory underneath, Pat Helland's "Idempotence Is Not a Medical Condition" is the short, readable classic on why exactly-once delivery is a fiction and at-least-once plus idempotency is the real target.
