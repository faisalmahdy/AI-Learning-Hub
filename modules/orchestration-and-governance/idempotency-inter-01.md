---
id: idempotency-inter-01
title: Dedup a retried request by its idempotency key — or at-least-once delivery turns one charge into two
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A network cannot deliver a message exactly once. It can deliver at most once (retry never, so some operations are lost) or at least once (retry on timeout, so some operations happen twice); real systems choose at-least-once because a silently-lost charge is worse than a repeatable one. The hazard is concrete: the client sends "charge 30", the server charges and replies, the reply is lost, and the client — unable to tell "my request never arrived" from "the reply never came back" — retries. A server that applies every request it receives charges 30 twice, debiting 60 for one payment. The fix is an idempotency key: a client-generated id naming the operation, not the attempt. The server keeps a dedup store mapping key to the response it already produced; the first request for a key applies the effect and records the response, and any later request with that key returns the stored response without re-applying. On a fixture starting at balance 100, the naive server leaves 40 (charged twice) while the idempotent server leaves 70 (charged once, retry replays the cached 70), and two genuinely different keys both still apply — turning an at-least-once transport into an exactly-once effect.
eli5: Imagine mailing a check, then not hearing back, so you mail another copy just in case. If the bank cashes both, you paid twice for one bill. The fix is to write a unique number on the check that means "this specific payment." When the bank sees a check number it has already cashed, it doesn't cash it again — it just tells you "already handled, here's your receipt." Now it's safe to keep re-sending until you get an answer: the payment happens exactly once no matter how many copies arrive, as long as they all carry the same number and two real payments carry two different numbers.
---

## Why this module

Networks retry, and retries repeat effects. The moment your system talks to another over an unreliable link, "the request was sent" and "the request happened once" stop being the same statement — and the gap between them is where one payment becomes two.

A network between a client and a server cannot promise exactly-once delivery. It can promise at-most-once — send, and if no acknowledgement comes back, give up — so some operations silently never happen. Or it can promise at-least-once — send, and if no acknowledgement comes back, retry — so every operation happens, but some happen more than once. There is no third option over an unreliable link, and real systems choose at-least-once, because a charge that silently vanishes is worse than a charge that might repeat, *provided you can make the repeat harmless*. The danger is exact: the client sends "charge 30", the server charges 30 and replies, the reply is lost to a timeout, and the client — which cannot distinguish "my request never arrived" from "the reply never came back" — retries. A server that applies every request it receives now charges 30 twice, debiting 60 for one intended payment.

The fix is an idempotency key: a client-generated id that names the *operation*, not the network attempt. The client stamps the original and every retry with the same key; the server keeps a dedup store mapping each key to the response it already produced. On the first request for a key the server applies the effect and records the response; on any later request with a key it has seen, it does not re-apply — it returns the stored response, so the retry is a safe no-op that still hands the client the answer it missed. That converts an at-least-once transport into an exactly-once *effect*. This module runs a charge and its retry through a naive server and an idempotent one, and pins the difference.

**At-least-once delivery guarantees every operation happens and permits some to happen twice, so correctness comes not from the transport but from the server making a repeated request idempotent — deduplicating on a client-supplied key so the effect applies exactly once no matter how many times the message arrives.**

## Concepts

**The effect** is the thing a request does that must not be doubled — here, debiting the account. Idempotency is a property of applying this effect: applying it once and applying it "again with the same key" leave the same state.

```python filename=modules/orchestration-and-governance/code/idempotency-inter-01/idempotency.py:45-47 COMPLETE
def apply_charge(balance, amount):
    """Debit the account: the effect a charge request performs."""
    return round(balance - amount, 2)
```

**The dedup store** is the whole mechanism: a map from idempotency key to the response already produced for it. First sight of a key applies the effect and records the response; any later sight replays the stored response without touching state. The retry still gets an answer — it just does not get a second charge.

```python filename=modules/orchestration-and-governance/code/idempotency-inter-01/idempotency.py:60-74 COMPLETE
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
```

<svg role="img" aria-label="A client sends a charge, the server applies it and replies, the reply is lost, and the client retries the same request carrying the same idempotency key" viewBox="0 0 300 132" width="300" height="132">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a lost reply forces a retry — the same key rides both</text>
  <text x="30" y="28" fill="var(--muted)" font-size="8">client</text>
  <text x="230" y="28" fill="var(--muted)" font-size="8">server</text>
  <line x1="44" y1="32" x2="44" y2="124" stroke="var(--line)"/>
  <line x1="244" y1="32" x2="244" y2="124" stroke="var(--line)"/>
  <line x1="46" y1="46" x2="242" y2="46" stroke="var(--s1)"/><text x="66" y="43" fill="var(--muted)" font-size="7">charge 30, key req-abc</text>
  <text x="250" y="49" fill="var(--muted)" font-size="7">apply</text>
  <line x1="242" y1="64" x2="120" y2="64" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="120" y="61" fill="var(--muted)" font-size="7">reply ✗ lost</text>
  <text x="150" y="80" fill="var(--muted)" font-size="7">(timeout)</text>
  <line x1="46" y1="98" x2="242" y2="98" stroke="var(--s1)"/><text x="60" y="95" fill="var(--muted)" font-size="7">RETRY charge 30, key req-abc</text>
  <text x="250" y="101" fill="var(--muted)" font-size="7">?</text>
  <text x="46" y="120" fill="var(--muted)" font-size="7">same key names one operation, not the attempt</text>
</svg>
^ The client cannot tell a lost request from a lost reply, so on timeout it retries — carrying the same idempotency key, which names the one operation both messages intend, so the server can recognize the second as a duplicate.

**The key names the operation, not the transport, so the dedup store can turn every retry after the first into a replay of the stored response — the effect applies once and the client still gets its answer.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/idempotency-inter-01/idempotency.py

The fixture is one charge and its retry, both carrying key `req-abc` — one logical operation, sent twice because the first reply was lost.

```json filename=modules/orchestration-and-governance/code/idempotency-inter-01/idempotency.json:4-7 COMPLETE
  "requests": [
    {"key": "req-abc", "amount": 30.0, "note": "original charge"},
    {"key": "req-abc", "amount": 30.0, "note": "client retry after a lost response (SAME key)"}
  ],
```

Run `--naive`, a server that applies every request it receives.

```text filename=--naive
NAIVE — a server that applies every request (no dedup)
--------------------------------------------------------------
  start balance = 100.00
  recv req-abc  amount 30.0  -> APPLIED, balance 70.00
  recv req-abc  amount 30.0  -> APPLIED, balance 40.00
--------------------------------------------------------------
  final balance = 40.00  (one intended charge of 30, applied twice = 60 debited)
```

The account started at 100 and ends at 40. The customer authorized one charge of 30, but because the retry looked to the server exactly like a fresh request — same amount, same everything — it applied a second 30, debiting 60 for a single payment. Nothing here is a bug in the charge logic; `apply_charge` did precisely what it was told, twice. The defect is that the server treated a message as an operation, when a message is only an attempt to deliver an operation, and at-least-once delivery makes multiple attempts routine. The two lines above are indistinguishable to a server that keeps no memory of what it has already done — and that missing memory is the entire failure.

## Build

Now run `--idempotent`, the same two messages through the dedup store.

```text filename=--idempotent
IDEMPOTENT — a server that dedups by idempotency key
------------------------------------------------------------------
  start balance = 100.00
  recv req-abc  amount 30.0  -> APPLIED, balance 70.00 (response stored)
  recv req-abc  amount 30.0  -> DUPLICATE, no re-charge, returned stored 70.00
------------------------------------------------------------------
  final balance = 70.00  (one intended charge, applied once = 30 debited)
  dedup store: {'req-abc': 70.0}
```

The first message for `req-abc` is applied — balance 100 → 70 — and its response (70) is recorded under the key. The second message carries the same key, so the server recognizes it as a duplicate: it does not re-charge, and it returns the stored 70. Final balance 70, debited exactly 30, and the client still receives a valid response for its retry — it never learns, or needs to learn, that the operation had already happened. The naive server, by contrast, is just the same loop with the memory removed: it applies every request unconditionally, which is exactly why the retry becomes a second charge.

```python filename=modules/orchestration-and-governance/code/idempotency-inter-01/idempotency.py:50-57 COMPLETE
def run_naive(start, requests):
    """A server that applies every request it receives -- no dedup, so a retry is a second charge."""
    balance = start
    log = []
    for r in requests:
        balance = apply_charge(balance, r["amount"])
        log.append({"key": r["key"], "amount": r["amount"], "applied": True, "balance": balance})
    return balance, log
```

<svg role="img" aria-label="Two balance timelines from 100: the naive server drops to 70 then 40 on the retry, the idempotent server drops to 70 then stays 70 by replaying the cached response" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the retry doubles the charge naively; the key holds it at one</text>
  <line x1="30" y1="24" x2="30" y2="100" stroke="var(--line)"/>
  <line x1="30" y1="100" x2="290" y2="100" stroke="var(--line)"/>
  <text x="24" y="30" fill="var(--muted)" font-size="7" text-anchor="end">100</text>
  <text x="24" y="58" fill="var(--muted)" font-size="7" text-anchor="end">70</text>
  <text x="24" y="86" fill="var(--muted)" font-size="7" text-anchor="end">40</text>
  <text x="60" y="112" fill="var(--muted)" font-size="7">start</text>
  <text x="150" y="112" fill="var(--muted)" font-size="7">after charge</text>
  <text x="250" y="112" fill="var(--muted)" font-size="7">after retry</text>
  <polyline points="65,24 160,58 255,86" fill="none" stroke="var(--s2)"/>
  <circle cx="255" cy="86" r="3" fill="var(--s2)"/><text x="230" y="82" fill="var(--muted)" font-size="7">naive → 40</text>
  <polyline points="65,24 160,58 255,58" fill="none" stroke="var(--s1)"/>
  <circle cx="255" cy="58" r="3" fill="var(--s1)"/><text x="228" y="52" fill="var(--muted)" font-size="7">idempotent → 70</text>
</svg>
^ Both start at 100 and drop to 70 on the first charge; on the retry the naive server charges again to 40, while the idempotent server recognizes the key and replays the stored 70, so one payment debits exactly 30.

## Definition of done

The self-test pins the double-charge, the single-charge, the cached retry, and — critically — that dedup does not over-suppress two genuinely different operations.

```python filename=modules/orchestration-and-governance/code/idempotency-inter-01/idempotency.py:118-130 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — at-least-once retries double-charge naively but apply once under the key; distinct keys both still apply
------------------------------------------------------------------------------------------------------------------
  the naive server applies the retry too, charging twice = True (40.00, debited 60.00)
  the idempotent server charges the operation exactly once = True (70.00, debited 30.00)
  the retry is not re-applied and returns the stored response = True (returned 70.00)
  the two same-key messages produced one stored operation = True (1 entry)
  two DIFFERENT keys are both applied (dedup does not over-suppress) = True (45.00, 2 entries)
```

The last flag is the one that keeps the fix honest. Deduplication that suppressed every repeated amount would "fix" the double charge by breaking every legitimate second payment of the same size. The test feeds two operations with *different* keys (`req-abc` and `req-xyz`) and confirms both apply — balance 100 → 45, two store entries — so the dedup keys on the operation's identity, not on the request's shape. Suppress by key, never by content.

<svg role="img" aria-label="The dedup store as a table from key to stored response: a retry with an existing key hits the cache and is suppressed, while a request with a new key misses and applies" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the store keys on the operation's identity, not its amount</text>
  <rect x="20" y="24" width="150" height="64" fill="none" stroke="var(--line)"/>
  <line x1="95" y1="24" x2="95" y2="88" stroke="var(--line)"/>
  <line x1="20" y1="44" x2="170" y2="44" stroke="var(--line)"/>
  <text x="30" y="38" fill="var(--muted)" font-size="7">key</text>
  <text x="105" y="38" fill="var(--muted)" font-size="7">stored response</text>
  <text x="30" y="60" fill="var(--ink)" font-size="7">req-abc</text><text x="105" y="60" fill="var(--ink)" font-size="7">balance 70</text>
  <text x="30" y="80" fill="var(--ink)" font-size="7">req-xyz</text><text x="105" y="80" fill="var(--ink)" font-size="7">balance 45</text>
  <line x1="172" y1="52" x2="205" y2="52" stroke="var(--s1)"/><text x="185" y="49" fill="var(--muted)" font-size="7">req-abc</text>
  <text x="210" y="55" fill="var(--muted)" font-size="7">HIT → replay 70,</text>
  <text x="210" y="65" fill="var(--muted)" font-size="7">no re-charge</text>
  <line x1="172" y1="80" x2="205" y2="80" stroke="var(--s2)"/><text x="185" y="77" fill="var(--muted)" font-size="7">req-new</text>
  <text x="210" y="83" fill="var(--muted)" font-size="7">MISS → apply,</text>
  <text x="210" y="93" fill="var(--muted)" font-size="7">then store</text>
</svg>
^ A retry whose key is already in the store is replayed without re-applying; a request whose key is new misses, applies its effect, and records its response — so two same-key messages collapse to one operation while two different keys stay two.

**Done means the naive server double-charges (100 → 40), the idempotent server charges once and replays the stored response on the retry (100 → 70, one store entry), and two distinct keys both still apply (100 → 45, two entries) — proving the dedup suppresses retries by key without suppressing genuinely different operations.**

## Boss fight

Predict where an idempotency key that looks correct still fails, because the store is a real system with scope, lifetime, and atomicity of its own.

The first trap is key scope and generation. The key must name the operation the *client intends*, and it must be generated once per intent and reused across retries — if the client mints a fresh key on each retry, every attempt is a new operation and the dedup never fires. Equally, the key must be scoped so two unrelated operations cannot collide: a bare "userid+amount" is not a key, because a customer legitimately buying two identical coffees an hour apart would have the second silently swallowed as a duplicate of the first. The key belongs to the request the client is making, generated at the moment of intent (a UUID per checkout, per submit), not derived from the payload — which is exactly what the self-test's distinct-keys flag guards.

The second trap is that the store's write and the effect's write must be atomic, or the dedup has its own race. If the server applies the charge and then, in a separate step, records the key, a crash or a concurrent duplicate landing in that gap re-applies the effect — two requests both find the key absent, both charge, and only then does one record it. The dedup store therefore has to be part of the same transaction as the effect (same database commit, or a conditional insert of the key that fails the second writer), and a concurrent duplicate must block on the first, not race it. And the store is not free forever: keys need a retention window long enough to outlast any retry the transport can produce, after which they expire — so "exactly once" is really "exactly once within the retry horizon," and an operation retried after its key has aged out will apply again. The key makes retries safe; making the *store* correct — right scope, atomic with the effect, retained past the retry window — is what makes the key safe.

**An idempotency key only delivers exactly-once effects when it is generated once per intent and reused across retries (never per-attempt, never derived from the payload so distinct operations stay distinct), and when the key's record commits atomically with the effect and is retained past the transport's retry horizon — otherwise the dedup misfires, races the effect, or expires, and the double charge returns.**

## External resources

Stripe's idempotency-key documentation and similar payment-API guides — the canonical treatment of client-generated keys, how long results are retained, and why the client reuses one key across retries of a single intent.

Any distributed-systems text on delivery semantics — at-most-once versus at-least-once versus the impossibility of exactly-once *delivery*, and how exactly-once *processing* is recovered by deduplication and idempotent effects rather than by the network.

The companion anti-entropy and failure-detector modules in this topic — like them, this is a case where an unreliable link forces the application layer to add the guarantee the transport cannot give, here by keying and storing the effect rather than trusting the message count.
