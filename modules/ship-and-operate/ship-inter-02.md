---
id: ship-inter-02
title: Retries need idempotency, or you pay twice
topic: ship-and-operate
level: intermediate
status: ready
time: 8-10h
summary: A flaky channel that loses the server's ack after the effect is already committed leaves the client unable to tell "never happened" from "happened, reply lost", so it retries — and a naive server commits again, turning five intended charges totalling 95 into eleven charges totalling 169, a 74 overcharge. A stable idempotency key the client reuses on every retry lets the server dedup repeats and commit exactly once, back to five charges and 95. The trap is the word stable: a key that carries the attempt number changes on each retry, the server sees a fresh key every time, and the dedup commits all eleven charges again — the fix present but silently disabled.
eli5: If you mail a cheque, it never arrives, and you cannot tell whether it was cashed or lost, you might send another — and if it was actually cashed, you just paid twice. An idempotency key is like writing the same reference number on every copy so the bank knows they are all the one payment and cashes it once. But only if the number stays the same on every copy; change it and the bank thinks each is new.
---

## Why this module

Every network call can fail, so every serious client retries. Retrying is correct and unavoidable — but it quietly assumes the operation is safe to repeat, and the operations that matter most, the ones with real side effects, usually are not. This module builds the exact failure that assumption hides and the standard fix for it, because retrying a non-idempotent operation is one of the most common ways a shipped system does real damage: not a crash, not an error page, but a customer charged twice and a support ticket you cannot reproduce.

The failure lives in one specific gap. There are two ways a call can fail, and they are not symmetric. The benign one is the request never reaching the server: nothing was committed, the retry is a clean redo, no harm. The vicious one is the server committing the effect and then the acknowledgement getting lost on the way back. The client sees no ack. From where it sits, "the request never arrived" and "the request succeeded but the reply was lost" are indistinguishable — the same silence. So it does the only thing it safely can, which is retry, and a server that treats the retry as a fresh request commits the effect a second time. The client did nothing wrong; the server did nothing wrong locally; and the money is gone twice.

You need no prior module, only the idea of a client, a server, and a call between them that can drop. Everything runs offline against a delivery fixture — five operations, each labelled with how many of its attempts committed-then-lost-their-ack — stdlib Python 3, `$0.00`. The instinct to unlearn is that a retry is free. A retry is free only when the operation is idempotent; when it is not, every retry is a coin flip on a double effect, and over a flaky channel that coin comes up heads often.

Here is what a naive retry loop does to five simple charges:

```
# modules/ship-and-operate/code/ship-inter-02/ — COMPLETE, run from that directory
$ python3 idempotency.py --naive

NAIVE — retry with no idempotency key; every retry commits again
------------------------------------------------------------------
  charge-001   amount= 20.0  lost-acks=0  -> charged once
  charge-002   amount= 15.0  lost-acks=2  -> charged 3x
  charge-003   amount=  8.0  lost-acks=1  -> charged 2x
  charge-004   amount= 40.0  lost-acks=0  -> charged once
  charge-005   amount= 12.0  lost-acks=3  -> charged 4x
  intended: 5 charges totalling 95.0
  committed: 11 charges totalling 169.0  (overcharge 74.0)
```

run: 2026-08-26 · deterministic; delivery outcomes are a fixture · 5 ops · `python3 idempotency.py --naive`

Five charges the customer agreed to; eleven charges committed; 74 of overcharge. Nobody wrote a bug — the retry loop is textbook. The damage is entirely in the interaction between an at-least-once channel and a server that assumes at-most-once. This module closes that gap.

## Concepts

Named here so you can find them again; each is built below.

- **Idempotent operation** — one whose effect is the same whether applied once or many times; safe to retry.
- **Lost ack** — the server commits the effect, then the acknowledgement is lost; the client cannot tell it from a total failure.
- **At-least-once delivery** — a retrying client guarantees the request lands at least once, possibly more.
- **Idempotency key** — a stable id the client attaches to a logical operation and reuses on every retry.
- **Dedup** — the server remembers applied keys and, on a repeat, returns the stored result without committing again.
- **Stable key** — the same key on every retry; the property the whole fix depends on.

## Worked example

Source: the idempotency-key pattern every payment and messaging API ships (Stripe, cloud queues, any exactly-once effect over an at-least-once transport), distilled to its mechanism; the delivery outcomes here stand in for a real flaky channel so the double-charge is exact and checkable.

Script and fixture: `modules/ship-and-operate/code/ship-inter-02/` — `idempotency.py`, and `idempotency.json`, five operations each carrying how many attempts committed then lost their ack. Every command runs from there.

### The channel: why a retry can double an effect

The whole problem is one asymmetry, so make it concrete. The client sends a charge. The server receives it, commits it — the money moves — and sends back "done". If that "done" is lost, the client waits, times out, and sees exactly what it would see if the server had never received the charge at all: nothing. It has no way, from its side, to distinguish the two. The safe-looking move is to retry, and now the server, if it is naive, charges again.

The fixture encodes this per operation as `commits_before_ack`: how many attempts committed the effect but lost the ack before one finally got through. `charge-005` has three, so the client attempts it four times, the first three commit-and-lose-ack, the fourth commits-and-acks — four charges for one intended. The `lost-acks=0` operations show the benign case: one attempt, one ack, one charge.

<svg viewBox="0 0 700 200" role="img" aria-label="A sequence between client and server. Attempt 1: client sends charge, server commits (money moves), ack is lost on the way back. Client times out, cannot tell failure from lost-ack. Attempt 2: client retries, server commits again, ack returns. Result: two commits for one intended charge.">
  <g font-family="var(--mono)" font-size="9">
    <text x="60" y="18" fill="var(--muted)">client</text><text x="560" y="18" fill="var(--muted)">server</text>
    <line x1="80" y1="26" x2="80" y2="185" stroke="var(--grid)"></line>
    <line x1="580" y1="26" x2="580" y2="185" stroke="var(--grid)"></line>
    <line x1="80" y1="46" x2="580" y2="60" stroke="var(--ink)"></line><text x="200" y="44" fill="var(--ink)" font-size="8">charge -></text>
    <text x="586" y="64" fill="var(--s2)" font-size="8">commit (money moves)</text>
    <line x1="580" y1="72" x2="200" y2="88" stroke="var(--s2)" stroke-dasharray="3 3"></line><text x="300" y="80" fill="var(--s2)" font-size="8">ack LOST</text>
    <text x="90" y="104" fill="var(--muted)" font-size="8">timeout: failure or lost-ack? indistinguishable -> retry</text>
    <line x1="80" y1="120" x2="580" y2="134" stroke="var(--ink)"></line><text x="200" y="118" fill="var(--ink)" font-size="8">charge (retry) -></text>
    <text x="586" y="138" fill="var(--s2)" font-size="8">commit AGAIN</text>
    <line x1="580" y1="146" x2="80" y2="160" stroke="var(--s1)"></line><text x="300" y="154" fill="var(--s1)" font-size="8">ack ok</text>
    <text x="90" y="180" fill="var(--s2)" font-size="9">one intended charge, two commits — the naive double-charge</text>
  </g>
</svg>
^ The lost ack is the whole trap: the client cannot see the difference between "never committed" and "committed, reply lost", so it retries, and a server with no memory of the request commits twice. Everything downstream is this diagram repeated.

### The naive server: no memory, so every retry commits

The server just applies whatever it receives. Without a key it has no way to recognise a retry.

```
# idempotency.py:48-57 — COMPLETE (commit; with a key, dedup a repeat)
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
```

With `key=None` the dedup branch is dead, so every call commits. The client's retry loop drives exactly the number of calls the channel forces:

```
# idempotency.py:62-74 — COMPLETE (retry until the ack lands)
def send_with_retries(server, op, key_fn=None):
    """Retry until the ack lands. key_fn(op, attempt) builds the key sent on each attempt."""
    lost = op["commits_before_ack"]
    for attempt in range(lost + 1):  # attempts 0..lost; the last one's ack survives
        key = key_fn(op, attempt) if key_fn else None
        server.apply(op["amount"], key)
        # attempts < lost committed but the ack was lost -> client loops again
    # attempt == lost acked successfully; client stops
```

Run it and the totals are the cold open: 11 commits, 169 committed against 95 intended, 74 overcharge. The retry loop is correct — it does exactly what a robust client should, keep trying until acknowledged. The fault is that the server counts each try as new.

### The fix: a stable idempotency key

The client attaches an id to the logical operation and sends the same id on every retry. The server remembers ids it has applied and, on a repeat, returns the stored result instead of committing again.

```
# idempotency.py:77-78 — COMPLETE (the key builders; only one is correct)
STABLE_KEY = lambda op, attempt: op["id"]            # correct: same key every retry
UNSTABLE_KEY = lambda op, attempt: "%s#%d" % (op["id"], attempt)  # bug: key changes per attempt
```

`STABLE_KEY` ignores the attempt number, so all four attempts of `charge-005` carry `charge-005`. The first commits and stores the key; the next three hit the dedup branch and commit nothing. Exactly once:

```
# $ python3 idempotency.py --keyed
#   charge-005   amount= 12.0  key=charge-005  -> committed once
#   intended: 5 charges totalling 95.0
#   committed: 5 charges totalling 95.0  (overcharge 0.0)
```

run: 2026-08-26 · deterministic · `python3 idempotency.py --keyed`

Same channel, same lost acks, same retries — and the overcharge is gone, because the server can now recognise a retry for what it is. This is exactly-once effect built on top of at-least-once delivery, which is the only honest way to get it: you cannot make the channel deliver exactly once, so you make the effect idempotent and let the channel deliver as many times as it must.

**A retry over a lossy channel guarantees at-least-once delivery, so exactly-once effect has to come from the server deduping a stable idempotency key — reused unchanged on every retry — not from the channel ever behaving.**

### The bug that looks like the fix: an unstable key

Here is the failure that passes code review. Someone builds the key from something that varies per attempt — a timestamp, a retry counter — so it feels unique and correct. But a key that changes between retries defeats its own purpose: the server sees a brand-new key on every attempt and dedups nothing.

The self-test runs all three schemes and compares committed totals against intended:

```
# idempotency.py:122-139 — COMPLETE (the three-way comparison the check makes)
def check(ops):
    want_total, want_n = intended(ops)

    naive = run(ops, None)
    naive_overcharges = naive.total > want_total and naive.commits > want_n

    keyed = run(ops, STABLE_KEY)
    keyed_exact = keyed.total == want_total and keyed.commits == want_n

    unstable = run(ops, UNSTABLE_KEY)
    unstable_fails = unstable.total == naive.total
```

The decisive assertion is `unstable_fails`: the unstable key must commit exactly what the no-key server commits, proving the dedup never fired.

```
# $ python3 idempotency.py --check
#   naive retry overcharges = True (committed 169.0 vs intended 95.0)
#   stable key -> exactly once = True (committed 95.0, 5 charges)
#   UNSTABLE key dedups nothing = True (committed 169.0, same as naive)
#   SELF-TEST PASS  naive_overcharges=True  keyed_exact=True  unstable_fails=True
```

run: 2026-08-26 · deterministic · `python3 idempotency.py --check`

Read the third line. The unstable key commits 169 — identical to the naive server with no key at all. The idempotency machinery is fully present and fully wired; it just never fires, because `charge-005#0`, `charge-005#1`, `charge-005#2`, and `charge-005#3` are four different keys to the server. This is the dangerous version, because the code looks defended: there is a key, there is a dedup table, the review passes. Only a test that actually drives a retry with the real key builder catches it — which is exactly what the self-test does.

<svg viewBox="0 0 700 170" role="img" aria-label="Two columns for charge-005 with four attempts each. Left, STABLE key: all four attempts carry the same key charge-005; only the first commits, three are deduped. Right, UNSTABLE key: attempts carry charge-005#0 through #3, all four are new keys, all four commit.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">charge-005, four attempts (three lost acks + one that sticks)</text>
    <text x="60" y="42" fill="var(--ink)">STABLE key</text>
    <text x="60" y="62" fill="var(--s1)">charge-005</text><text x="60" y="78" fill="var(--muted)">charge-005</text><text x="60" y="94" fill="var(--muted)">charge-005</text><text x="60" y="110" fill="var(--muted)">charge-005</text>
    <text x="200" y="62" fill="var(--s1)" font-size="8">commit</text><text x="200" y="78" fill="var(--muted)" font-size="8">dedup</text><text x="200" y="94" fill="var(--muted)" font-size="8">dedup</text><text x="200" y="110" fill="var(--muted)" font-size="8">dedup</text>
    <text x="60" y="132" fill="var(--s1)">-> 1 charge</text>
    <text x="420" y="42" fill="var(--ink)">UNSTABLE key</text>
    <text x="420" y="62" fill="var(--s2)">charge-005#0</text><text x="420" y="78" fill="var(--s2)">charge-005#1</text><text x="420" y="94" fill="var(--s2)">charge-005#2</text><text x="420" y="110" fill="var(--s2)">charge-005#3</text>
    <text x="560" y="62" fill="var(--s2)" font-size="8">commit</text><text x="560" y="78" fill="var(--s2)" font-size="8">commit</text><text x="560" y="94" fill="var(--s2)" font-size="8">commit</text><text x="560" y="110" fill="var(--s2)" font-size="8">commit</text>
    <text x="420" y="132" fill="var(--s2)">-> 4 charges</text>
  </g>
</svg>
^ The only difference is whether the key carries the attempt number. Stable: one key, three dedups, one charge. Unstable: four keys, zero dedups, four charges — the naive result with a dedup table that never matches.

### The running tally

| scheme | committed charges | committed total | overcharge |
|---|---|---|---|
| naive (no key) | 11 | 169.0 | 74.0 |
| unstable key | 11 | 169.0 | 74.0 |
| stable key | 5 | 95.0 | 0.0 |

<svg viewBox="0 0 700 170" role="img" aria-label="Three horizontal bars of committed total. Naive: long bar to 169. Unstable key: identical long bar to 169. Stable key: shorter bar to 95, the intended amount, marked with a dashed intended line at 95.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">committed total by scheme; intended is 95</text>
    <line x1="150" y1="30" x2="150" y2="150" stroke="var(--grid)" stroke-dasharray="3 3"></line>
    <text x="150" y="164" text-anchor="middle" fill="var(--muted)" font-size="8">intended 95</text>
    <text x="20" y="52" fill="var(--ink)">naive</text><rect x="150" y="40" width="360" height="18" fill="var(--s2)"></rect><text x="518" y="54" fill="var(--s2)" font-size="9">169</text>
    <text x="20" y="88" fill="var(--ink)">unstable key</text><rect x="150" y="76" width="360" height="18" fill="var(--s2)"></rect><text x="518" y="90" fill="var(--s2)" font-size="9">169</text>
    <text x="20" y="124" fill="var(--ink)">stable key</text><rect x="150" y="112" width="0" height="18" fill="var(--s1)"></rect><rect x="150" y="112" width="2" height="18" fill="var(--s1)"></rect><text x="160" y="126" fill="var(--s1)" font-size="9">95 (exactly intended)</text>
  </g>
</svg>
^ Naive and unstable-key land on the identical overcharge of 169; only the stable key sits at the dashed intended line of 95. A structural check that asks "is there a key" cannot separate the top two bars.

The middle row is the one to remember. It has all the apparatus of the fix and none of the effect, and it sits at the exact same overcharge as having no fix at all. A test that checks "is there an idempotency key" would pass it; only a test that checks "does a retried operation commit once" tells naive and unstable apart from correct. Verify the property, not the presence of the mechanism.

### What we did not settle

This is the mechanism, not the whole engineering. Real systems bound the dedup table: keys expire, so a retry after the key ages out double-commits — you size the retention past the client's maximum retry horizon. The dedup store must itself be consistent, or two concurrent retries both miss the table and both commit — production uses an atomic insert-if-absent, not the read-then-write shown here. Keys should be scoped to the operation's parameters, so a client reusing a key for a genuinely different charge does not get the wrong stored result. And the effect being deduped must be the whole transaction, not half of it. The pattern is small; making it airtight under concurrency and expiry is the actual work.

## Build

The pattern in one paragraph: for any operation with a real side effect, have the client mint a stable key per logical operation and send it unchanged on every retry; have the server, before committing, atomically check whether the key was already applied and if so return the stored result; and retain keys longer than the client will ever retry. Then test the property that matters — a retried operation commits exactly once — not the presence of a key, because a key that varies per attempt passes every structural check and fixes nothing.

We opened on the naive overcharge. The number that proves the fix is the committed total:

```
# modules/ship-and-operate/code/ship-inter-02/ — COMPLETE, run from that directory
$ python3 idempotency.py --keyed
  committed: 5 charges totalling 95.0  (overcharge 0.0)
```

Now do it to your own operation. Take any call with a side effect — a write, a charge, a message send — put a stable idempotency key on it, and drive it through a retry loop that fires the operation more than once. Your number to beat is not "the key exists"; it is **the committed effect count under retries, which must equal the intended count**. Then deliberately build the key from the attempt number and watch the count blow back up, so you have seen the failure the structural check misses. Bring back both counts. Good luck.

## Definition of done

- [ ] A server that commits a side effect and can dedup by an idempotency key
- [ ] A client retry loop that fires an operation multiple times over a lossy channel
- [ ] The naive (no-key) run measured: committed effect exceeds intended
- [ ] The stable-key run measured: committed effect equals intended, exactly once
- [ ] The unstable-key run measured: it regresses to the naive overcharge
- [ ] `python3 idempotency.py --check` printing SELF-TEST PASS: naive overcharges, stable exact, unstable fails
- [ ] A test that asserts the committed count, not merely the presence of a key
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Name the two ways a call can fail and explain why the client cannot distinguish them — and why that indistinguishability is the whole source of the double-charge.
2. Why can you not get exactly-once delivery from the channel, and what property do you build instead to get an exactly-once effect?
3. A colleague's PR adds an idempotency key built from the current timestamp. It passes review. What breaks, and what committed count reveals it?
4. Why does "the code has an idempotency key" fail as an acceptance test, and what should the test assert instead?
5. Your own operation was driven through retries. What was the intended count, the committed count with a stable key, and the committed count when you sabotaged the key to vary per attempt?

## External resources

- Stripe, *Idempotent requests* — https://stripe.com/docs/api/idempotent_requests — my summary: the production spec for the exact pattern here — client-supplied keys, server-side dedup, key retention windows; read it for how a real payments API scopes keys to parameters and how long it remembers them.
- Brooker (AWS), *Idempotency and the lost-ack problem* — general distributed-systems writing on at-least-once delivery — my summary: why exactly-once delivery is impossible and exactly-once effect via idempotent operations is the achievable goal; read it for the delivery-vs-effect distinction this module is built around.
- This hub, *ship-inter-01* — modules/ship-and-operate/ship-inter-01.md — my summary: the other ship-and-operate failure where the mechanism is present but a subtle property defeats it (a compare that short-circuits); read it for the same lesson — test the property, not the presence of the guard.
