---
id: poolleak-inter-01
title: Release a pooled connection in a finally block — leaking one on the error path bleeds the pool to exhaustion and then rejects healthy requests
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A connection pool hands out a fixed number of reusable connections; each request acquires one, does its work, and must return it so the next request can. The bug is releasing only on the success path: the code acquires, runs the work, then releases — but if the work raises before the release line, control skips it and the connection is never returned. It is leaked. One leak is invisible, but every failing request leaks another, so the available count ratchets downward one per failure and never recovers; once it hits zero the pool is exhausted, and the next request — however healthy — cannot acquire a connection and is rejected. A handful of failures on one code path silently becomes a total outage on all paths, and the symptom (healthy requests rejected for lack of a connection) points nowhere near the cause (an unreleased connection on an unrelated error path). The fix is to make release unconditional — a finally block, or a context manager whose exit returns the connection — so it runs whether the work returned or threw, and a failing request fails alone with its connection reclaimed. On a fixture where a pool of 3 serves 7 requests of which 3 error, the leaky caller leaks all 3, drains the pool to zero, and rejects a healthy request, while the finally caller leaks nothing and rejects nobody, holding the pool at 3 of 3.
eli5: Imagine a library with three reference books that must stay in the building — you borrow one at the desk, use it, and hand it back. The rule is you hand it back no matter what. Now suppose people only remember to return the book when they finish reading happily, but if they get interrupted and leave upset, they walk out with it. Each upset visitor takes a book that never comes back, so after three bad visits all three books are gone, and the very next person — calm, ready to read — is turned away because there are no books left, even though nothing is wrong with them. The one who caused the shortage is long gone; the person who suffers is innocent. The fix is a rule that the book goes back on the way out every time, happy or upset — a hand-back that always happens.
---

## Why this module

Pooled resources — database connections, HTTP clients, file handles, threads — exist because creating them is expensive, so a fixed set is created once and lent out. The contract is a loan: acquire, use, return. The whole system depends on the return, because the pool is finite and the next request is waiting for a connection this one is holding.

The natural way to write the loan is acquire, do the work, release — three lines in order. It reads correctly and it runs correctly, every time the work succeeds. The gap is the failure path: if the work throws, an exception unwinds the stack past the release line, and the release simply does not execute. The connection was acquired and never returned. It is not closed, not freed, not back in the pool — it is leaked, held forever by a request that is already gone.

What makes this a nasty production bug rather than a small inefficiency is accumulation and misdirection. Each failure on that path leaks one more connection, so the pool bleeds down monotonically, and nothing visibly breaks until it hits empty. Then requests start failing with "cannot acquire connection" or "pool timeout" — and those failing requests are the healthy ones, on completely different code paths, that simply arrived after the pool ran dry. The error you see is nowhere near the error that caused it.

**A pooled connection released only on the success path is leaked whenever the work throws, and the leaks accumulate until the pool is exhausted — after which healthy requests on every path are rejected, far from the error path that drained it.**

## Concepts

The mechanism is entirely about control flow, so look at where the release sits relative to the failure. In the leaky version, `acquire` runs, then the work runs inside a try, and `release` sits after the try — on the normal path. When the work raises, the except handler returns (or the exception propagates) before reaching the release, so the acquired connection is orphaned. The release is written; it is just on a line the failure path never visits.

<svg role="img" aria-label="Two control-flow paths. Leaky: acquire, then work; on success reach release; on error jump to a return that skips release, leaking the connection. Safe: acquire, then work in a try with release in a finally that both the success and error paths pass through." viewBox="0 0 440 170">
<text x="110" y="14" fill="var(--muted)" font-size="9" text-anchor="middle">leaky: release after the try</text>
<rect x="70" y="24" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="110" y="36" fill="var(--ink)" font-size="8" text-anchor="middle">acquire</text>
<rect x="70" y="48" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="110" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">work</text>
<line x1="110" y1="64" x2="110" y2="72" stroke="var(--line)"/>
<rect x="30" y="72" width="70" height="16" fill="var(--panel)" stroke="var(--s2)"/><text x="65" y="84" fill="var(--s2)" font-size="8" text-anchor="middle">error: return</text>
<rect x="120" y="72" width="70" height="16" fill="var(--panel)" stroke="var(--s1)"/><text x="155" y="84" fill="var(--s1)" font-size="8" text-anchor="middle">release</text>
<text x="65" y="104" fill="var(--s2)" font-size="7" text-anchor="middle">skips release</text>
<text x="155" y="104" fill="var(--s1)" font-size="7" text-anchor="middle">only on success</text>
<text x="330" y="14" fill="var(--muted)" font-size="9" text-anchor="middle">safe: release in finally</text>
<rect x="290" y="24" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="330" y="36" fill="var(--ink)" font-size="8" text-anchor="middle">acquire</text>
<rect x="290" y="48" width="80" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="330" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">work</text>
<rect x="250" y="72" width="70" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="285" y="84" fill="var(--ink)" font-size="8" text-anchor="middle">error</text>
<rect x="340" y="72" width="70" height="16" fill="var(--panel)" stroke="var(--line)"/><text x="375" y="84" fill="var(--ink)" font-size="8" text-anchor="middle">success</text>
<rect x="290" y="98" width="80" height="16" fill="var(--s1)"/><text x="330" y="110" fill="var(--ink)" font-size="8" text-anchor="middle">finally: release</text>
<line x1="285" y1="88" x2="320" y2="98" stroke="var(--s1)"/>
<line x1="375" y1="88" x2="340" y2="98" stroke="var(--s1)"/>
<text x="330" y="128" fill="var(--s1)" font-size="7" text-anchor="middle">both paths pass through it</text>
</svg>
^ Leaky puts release on the success path, so the error path returns without it; finally puts release on a line both paths must pass through on the way out.

The safe version moves the release into a finally block. A finally block runs on the way out of the try no matter how the try is left — normal return, exception, even a return inside the handler — so the connection is released on the success path and the error path alike. In many languages the same guarantee is packaged as a context manager or scope guard: acquire in the "enter" step, release in the "exit" step, and the language runs the exit whenever control leaves the block. Either way, the release is welded to the acquire, not left dangling after the work.

Now trace the pool. Each leak lowers the available count by one and it never comes back up, because the connection is gone, not busy — no future release will return it. So the available count is monotonically non-increasing across failures, a one-way ratchet toward zero. This is the signature that distinguishes a leak from mere contention: under load, contention makes the pool oscillate (borrow, return, borrow); a leak makes it decline and stay down, even during idle periods, until a restart resets it.

<svg role="img" aria-label="A pool of three connections drawn as three slots, losing one to a leak on each of three errors until all three are gone, after which a healthy request finds no slot and is rejected." viewBox="0 0 440 130">
<text x="20" y="16" fill="var(--muted)" font-size="9">available connections as errors leak them</text>
<text x="30" y="46" fill="var(--ink)" font-size="8">start</text>
<rect x="80" y="36" width="16" height="16" fill="var(--s1)"/><rect x="100" y="36" width="16" height="16" fill="var(--s1)"/><rect x="120" y="36" width="16" height="16" fill="var(--s1)"/><text x="150" y="48" fill="var(--muted)" font-size="8">3</text>
<text x="30" y="70" fill="var(--ink)" font-size="8">2 errs</text>
<rect x="80" y="60" width="16" height="16" fill="var(--s1)"/><rect x="100" y="60" width="16" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="2 2"/><rect x="120" y="60" width="16" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="150" y="72" fill="var(--muted)" font-size="8">1</text>
<text x="30" y="94" fill="var(--ink)" font-size="8">3 errs</text>
<rect x="80" y="84" width="16" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="2 2"/><rect x="100" y="84" width="16" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="2 2"/><rect x="120" y="84" width="16" height="16" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="150" y="96" fill="var(--muted)" font-size="8">0</text>
<text x="185" y="96" fill="var(--s2)" font-size="8">next healthy request: rejected</text>
</svg>
^ Each leaked connection is gone for good, so the pool ratchets down 3, 1, 0 and never recovers — then a healthy request finds no free connection and is rejected.

**Release only on the success path leaves the error path skipping it; a finally block or context manager runs release on every exit, so the connection returns whether the work threw or not — and a monotone decline in available connections, not oscillation, is the fingerprint of a leak.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/poolleak-inter-01. The fixture is a pool size and a sequence of requests, some flagged to error.

```json filename=modules/ship-and-operate/code/poolleak-inter-01/poolleak.json:3-12 COMPLETE
  "pool_size": 3,
  "requests": [
    {"id": "r1", "error": false},
    {"id": "r2", "error": true},
    {"id": "r3", "error": false},
    {"id": "r4", "error": true},
    {"id": "r5", "error": false},
    {"id": "r6", "error": true},
    {"id": "r7", "error": false}
  ]
```

The pool tracks a fixed number of connections; acquire fails when none are free.

```python filename=modules/ship-and-operate/code/poolleak-inter-01/poolleak.py:32-48 COMPLETE
class Pool:
    """A fixed pool of reusable connections."""

    def __init__(self, size):
        self.size = size
        self.available = size

    def acquire(self):
        """Take a connection, or return False if the pool is exhausted."""
        if self.available <= 0:
            return False
        self.available -= 1
        return True

    def release(self):
        """Return a connection to the pool."""
        self.available += 1
```

The leaky caller releases after the work, so an exception returns before the release.

```python filename=modules/ship-and-operate/code/poolleak-inter-01/poolleak.py:57-66 COMPLETE
def leaky_serve(pool, request):
    """BUG: release only after the work returns -- an exception skips the release and leaks the connection."""
    if not pool.acquire():
        return "rejected"
    try:
        do_work(request)
    except RuntimeError:
        return "error-leaked"    # returned without releasing: the connection is lost
    pool.release()
    return "ok-released"
```

The safe caller releases in a finally, so every exit returns the connection.

```python filename=modules/ship-and-operate/code/poolleak-inter-01/poolleak.py:69-79 COMPLETE
def safe_serve(pool, request):
    """FIX: release in finally -- the connection returns whether the work returned or threw."""
    if not pool.acquire():
        return "rejected"
    try:
        do_work(request)
        return "ok-released"
    except RuntimeError:
        return "error-released"
    finally:
        pool.release()
```

Before running it, predict: three requests error, each leaking a connection from a pool of three, so by the third error the pool is empty and the next request — the healthy r7 — is rejected. Run `--leaky`:

```text filename=poolleak.py --leaky
LEAKY — release only on success (the error path skips release)
------------------------------------------------------------
  request  outcome          available after
  r1       ok-released      3
  r2       error-leaked     2
  r3       ok-released      2
  r4       error-leaked     1
  r5       ok-released      1
  r6       error-leaked     0
  r7       rejected         0
------------------------------------------------------------
  leaked=3  rejected=['r7']  available=0/3
  every error leaks a connection; the pool drains and then rejects a healthy request
```

The prediction holds exactly. Watch the available column: it holds at 3 through the first success, then drops to 2 at r2's error and stays there — the leaked connection never comes back — then to 1 at r4, then to 0 at r6. The successful requests in between (r3, r5) borrow and return cleanly, so they do not move the floor; only the errors ratchet it down. By r7, a perfectly healthy request, the pool is empty and it is rejected. Three failures on the error path took down a request on the success path.

Now the same sequence with the finally fix. Run `--safe`:

```text filename=poolleak.py --safe
SAFE — release in a finally block (every path returns the connection)
------------------------------------------------------------
  request  outcome          available after
  r1       ok-released      3
  r2       error-released   3
  r3       ok-released      3
  r4       error-released   3
  r5       ok-released      3
  r6       error-released   3
  r7       ok-released      3
------------------------------------------------------------
  leaked=0  rejected=[]  available=3/3
  a failing request fails alone; the pool stays whole
```

Identical requests, identical errors — the connection comes back every time. The errored requests still error (r2, r4, r6 report error-released; the failure is real and still surfaces to their callers), but each one returns its connection on the way out, so the available count never drops below 3 and r7 is served. The errors are contained to the requests that caused them; nothing leaks, nothing else is affected. The only difference from the leaky version is which line the release sits on.

<svg role="img" aria-label="Available connections over the seven requests. The leaky line steps down 3, 2, 1, 0 as errors leak and stays at 0. The safe line stays flat at 3 throughout." viewBox="0 0 440 140">
<line x1="45" y1="115" x2="410" y2="115" stroke="var(--line)"/>
<line x1="45" y1="20" x2="45" y2="115" stroke="var(--line)"/>
<text x="30" y="30" fill="var(--muted)" font-size="8" text-anchor="middle">3</text>
<text x="30" y="113" fill="var(--muted)" font-size="8" text-anchor="middle">0</text>
<text x="225" y="132" fill="var(--muted)" font-size="8" text-anchor="middle">r1 ... r7</text>
<line x1="45" y1="30" x2="405" y2="30" stroke="var(--s1)"/>
<text x="360" y="26" fill="var(--s1)" font-size="8">safe (flat at 3)</text>
<path d="M45 30 L 100 30 L 100 58 L 160 58 L 160 86 L 220 86 L 220 115 L 405 115" fill="none" stroke="var(--s2)"/>
<text x="300" y="108" fill="var(--s2)" font-size="8">leaky (bleeds to 0)</text>
</svg>
^ The leaky pool steps down with each error and stays at zero; the safe pool holds at three — the same requests, the release on a different line.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the leaky caller leaks one connection per error, that it drains the pool to zero, that it rejects a healthy request, that the finally caller leaks nothing and keeps the pool full, and that the finally caller rejects no requests.

```python filename=modules/ship-and-operate/code/poolleak-inter-01/poolleak.py:130-142 COMPLETE
    leaky_leaks_every_error = leaky["leaked"] == n_errors
    print("  the leaky caller leaks one connection per error = %s (%d leaked, %d errors)" % (leaky_leaks_every_error, leaky["leaked"], n_errors))

    leaky_exhausts_pool = leaky["available"] == 0
    print("  the leaky caller drains the pool to zero = %s (available %d)" % (leaky_exhausts_pool, leaky["available"]))

    leaky_rejects_healthy = any(rid not in err_ids for rid in leaky["rejected"])
    print("  the leaky caller rejects a healthy request = %s (rejected %s)" % (leaky_rejects_healthy, leaky["rejected"]))

    safe_no_leak = safe["leaked"] == 0 and safe["available"] == pool_size
    print("  the finally caller leaks nothing and keeps the pool full = %s (available %d/%d)" % (safe_no_leak, safe["available"], pool_size))

    safe_no_rejection = len(safe["rejected"]) == 0
    print("  the finally caller rejects no requests = %s" % safe_no_rejection)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the leaky caller ever stopped leaking or the finally caller ever dropped a connection:

```text filename=poolleak.py --check
SELF-TEST — the leaky caller bleeds the pool and rejects a healthy request; the finally caller keeps the pool whole
----------------------------------------------------------------------------------------------------------------
  the leaky caller leaks one connection per error = True (3 leaked, 3 errors)
  the leaky caller drains the pool to zero = True (available 0)
  the leaky caller rejects a healthy request = True (rejected ['r7'])
  the finally caller leaks nothing and keeps the pool full = True (available 3/3)
  the finally caller rejects no requests = True
```

**The self-test asserts specifically that the rejected request is a healthy one, not an errored one — pinning the cross-path nature of the bug: the failure lands on a request that did nothing wrong, which is exactly why a leak is diagnosed far from its cause.**

## Definition of done

You can explain the acquire/use/return contract of a pool and why the return is mandatory.
You can explain why releasing only after the work leaks the connection when the work throws.
You can explain why leaks accumulate monotonically and why the outage surfaces on healthy requests far from the error path.
You can describe the finally / context-manager fix and why it releases on every exit.
You can name the diagnostic signature — a monotone decline in available connections rather than oscillation — that distinguishes a leak from contention.

## Boss fight

Suppose you fix the release with a finally, but the work sometimes hangs rather than throws — it neither returns nor raises, it just blocks forever. Reason about whether finally saves you. It does not: a finally block runs when control leaves the try, and control never leaves a hang, so the connection is held indefinitely — a different way to lose it from the pool, indistinguishable from a leak in the available count. The fix for this is a timeout on the work (and on the acquire itself), so a hung operation is converted into an exception after a bounded wait, at which point the finally fires and reclaims the connection. The lesson generalizes: finally handles the paths that leave the block, but you must also ensure the block is always left, which is what timeouts guarantee. Release-in-finally and a work timeout are complementary, not alternatives.

Now the trap that makes leaks invisible until a specific moment: the pool's overflow and validation behavior. Many pools are configured to create a few extra connections beyond the nominal size under load, or to silently discard and recreate a connection that fails validation, which masks a slow leak — the pool keeps papering over the missing connections by making new ones, so the available count looks healthy while the real connection count to the database climbs past its server-side limit. Then the failure moves: instead of "pool exhausted" in your app, you get "too many connections" at the database, even further from the leaking code. The defenses are to monitor the pool's live and in-use counts as first-class metrics (a rising in-use count with flat throughput is a leak), to set a max lifetime so even a leaked-then-recreated connection is eventually reaped, and to leak-test in code review by asking of every acquire: is there a path that reaches here and does not reach a release? The invariant is one release per acquire on every path, hangs included.

**A finally block reclaims a connection only when control leaves the block, so a hung operation still holds it — pair release-in-finally with a work timeout; and because pools mask slow leaks by overflowing or recreating connections, monitor in-use counts and set a max lifetime rather than trusting the available count to look healthy.**

## External resources

The documentation for connection pools (HikariCP, database driver pools, HTTP client pools) stresses returning connections in a finally / try-with-resources / context manager and documents leak-detection thresholds and max-lifetime settings.
Language guides on resource management — Python's with-statement and contextlib, Java's try-with-resources, Go's defer, C#'s using — cover the scope-guard pattern that welds release to acquire.
The topic's own modules on sizing the pool by Little's law and on graceful shutdown cover the neighboring concerns — how big the pool must be, and returning in-flight connections on exit — that this one complements with the per-request release guarantee.
