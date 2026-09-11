---
id: retryafter-inter-01
title: Wait the server's Retry-After, not your own backoff — a server that says "come back in 5s" means it, and guessing is worse
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: When a server rate-limits or is overloaded, it does not just reject your request — it usually tells you when to come back. An HTTP 429 (Too Many Requests) or 503 carries a Retry-After header: "do not retry for N seconds." That header is the server speaking authoritatively about its own state — it knows when the rate-limit window resets, when the overloaded queue drains, when maintenance ends — information the client cannot have. The correct behavior is to honor it: wait exactly that long, then retry once. The common mistake is to ignore Retry-After and fall back to the client's own generic backoff, as if the 429 were an ordinary transient error. This is wrong in both directions: the client's backoff is a blind guess at a delay the server already gave exactly, so it retries too soon (before the window resets, each early retry another 429 that the retry storm is making worse — hammering a server that explicitly asked it to stop) and then, because backoff doubles, too late (overshooting past the moment the limit lifted, adding latency for nothing). Ignoring the header costs both extra load on a struggling server and extra latency for the client. On a fixture where the server is limited until t=5, the honoring client retries once at t=5 and succeeds in 2 requests, while the ignoring client backs off 1,2,4 — retrying at t=1 and t=3 (both still limited, more 429s) and finally succeeding at t=7 in 4 requests, later and with more load.
eli5: Imagine knocking on a shop door that has a sign: "Back in 5 minutes." The smart move is to wait 5 minutes and knock once. But some people ignore the sign and just keep knocking on their own rhythm — knock, wait a bit, knock, wait a bit — so they pound on the door three times while the shop is still closed (annoying the owner who's trying to get ready), and because their waits keep doubling, they don't knock again until 7 minutes have passed, missing the moment the shop actually reopened. Reading the sign and waiting exactly 5 minutes gets you in sooner AND stops you banging on a closed door — the sign knew the answer you were only guessing at.
---

## Why this module

A 429 is not a mysterious failure to retry blindly through — it is a message with an answer attached. The server that rejected you also told you precisely when it will say yes, and that Retry-After value is the one piece of timing information in the whole exchange that is authoritative, because only the server knows when its rate window resets or its queue drains. Treating the 429 like any other transient error and reaching for the client's generic backoff throws that answer away and substitutes a guess, and the guess is wrong in a way that is worse than useless: it retries during the exact window the server asked you to avoid, adding to the load that caused the limit.

An HTTP 429 or 503 carries a Retry-After header saying "do not retry for N seconds" — the server speaking authoritatively about its own state, information the client cannot have. The correct behavior is to honor it: wait exactly that long, then retry once. Ignoring it and falling back to the client's own backoff is wrong in both directions: too soon (retrying before the window resets, each early retry another 429 that the retry storm makes worse) and then too late (overshooting past the moment the limit lifted, adding latency for nothing).

So ignoring the header costs both extra load on an already-struggling server and extra latency for the client — the rare case where the disciplined thing is strictly better on every axis. This module runs a client that honors the header against one that ignores it.

**When a response carries a Retry-After header (on a 429 or 503), wait that duration before retrying instead of applying the client's own backoff, because the server knows exactly when it will accept traffic again and generic backoff both retries too early — adding load during the very window the server asked you to avoid — and too late, overshooting the moment the limit lifts.**

## Concepts

**One retry loop, one choice of wait:** honor the server's Retry-After, or fall back to the client's blind backoff schedule.

```python filename=modules/ship-and-operate/code/retryafter-inter-01/retryafter.py:52-70 COMPLETE
def run(limit_until, honor, backoff):
    """Simulate a client retrying against a server limited until limit_until. Returns the list of (time, response)."""
    t = 0
    attempt = 0
    log = []
    while True:
        if t >= limit_until:
            log.append((t, "200 OK"))
            return log
        retry_after = limit_until - t          # the server tells the client exactly how long to wait
        log.append((t, "429 (Retry-After %d)" % retry_after))
        if honor:
            wait = retry_after                 # trust the server's own timing
        else:
            wait = backoff[min(attempt, len(backoff) - 1)]   # blind generic backoff
        t += wait
        attempt += 1
        if attempt > 20:
            return log
```

**We score each client on load and latency** — total requests, how many were wasted 429 retries, and when it finally succeeded.

```python filename=modules/ship-and-operate/code/retryafter-inter-01/retryafter.py:73-82 COMPLETE
def requests_count(log):
    return len(log)


def success_time(log):
    return log[-1][0] if log[-1][1].startswith("200") else None


def wasted_429s(log):
    return sum(1 for _, resp in log if resp.startswith("429"))
```

<svg role="img" aria-label="A timeline from 0 to 8 with the limit window shaded from 0 to 5; the honoring client retries once at 5, the ignoring client retries at 1 and 3 inside the window (both 429) and succeeds at 7" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">server limited until t=5 (shaded); when each client retries</text>
  <rect x="30" y="28" width="150" height="60" fill="var(--grid)" opacity="0.45"/><text x="70" y="24" fill="var(--muted)" font-size="6">limited window [0,5)</text>
  <line x1="30" y1="88" x2="285" y2="88" stroke="var(--grid)"/>
  <text x="27" y="100" fill="var(--muted)" font-size="6">0</text><text x="177" y="100" fill="var(--muted)" font-size="6">5</text><text x="267" y="100" fill="var(--muted)" font-size="6">8</text>
  <text x="10" y="44" fill="var(--s1)" font-size="7">honor</text>
  <circle cx="30" cy="44" r="3" fill="var(--s2)"/><circle cx="180" cy="44" r="3" fill="var(--s1)"/><text x="184" y="42" fill="var(--s1)" font-size="6">200 at t=5</text>
  <text x="10" y="70" fill="var(--s2)" font-size="7">ignore</text>
  <circle cx="30" cy="70" r="3" fill="var(--s2)"/><circle cx="60" cy="70" r="3" fill="var(--s2)"/><circle cx="120" cy="70" r="3" fill="var(--s2)"/><circle cx="240" cy="70" r="3" fill="var(--s1)"/>
  <text x="120" y="66" fill="var(--s2)" font-size="6">429s at 1,3</text><text x="216" y="66" fill="var(--s1)" font-size="6">200 at t=7</text>
</svg>
^ The limit lifts at t=5; the honoring client's single retry lands exactly there and succeeds, while the ignoring client fires retries at t=1 and t=3 inside the shaded window (each a wasted 429) and only succeeds at t=7, having overshot the reset.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/retryafter-inter-01/retryafter.py

The fixture is the server's limit window and the backoff schedule a header-ignoring client would use.

```json filename=modules/ship-and-operate/code/retryafter-inter-01/retryafter.json:3-4 COMPLETE
  "limit_until": 5,
  "backoff_schedule": [1, 2, 4, 8, 16]
```

Run `--timeline`.

```text filename=--timeline
TIMELINE — server limited until t=5; honor Retry-After vs ignore it (backoff [1, 2, 4, 8, 16])
------------------------------------------------------------------
  HONOR the Retry-After header:
    t=0   429 (Retry-After 5)
    t=5   200 OK
  IGNORE it, use own backoff:
    t=0   429 (Retry-After 5)
    t=1   429 (Retry-After 4)
    t=3   429 (Retry-After 2)
    t=7   200 OK
------------------------------------------------------------------
  honor succeeds at t=5 in 2 requests; ignore at t=7 in 4 requests.
```

Read the two timelines. Both clients make their first request at t=0 and get the same 429, which says Retry-After 5 — the server is telling them, exactly, that it will accept traffic at t=5. The honoring client does the obvious thing: it waits 5 seconds and retries at t=5, which succeeds. Two requests, done at t=5. The ignoring client throws the header away and applies its backoff schedule: it waits 1 second and retries at t=1 (still limited — the server even repeats Retry-After 4, "you're four seconds early"), waits 2 more and retries at t=3 (still limited, Retry-After 2), and only on its fourth attempt, at t=7 (having waited the backoff's 4 seconds from t=3), does it succeed. Every one of those extra retries at t=1 and t=3 hit the server *during the window it asked to be left alone* — the ignoring client is adding load precisely when the server is struggling — and after all that it still finishes two seconds later than the client that simply read the header.

## Build

Tally the two costs the ignoring client pays, both of which the header would have saved.

```text filename=--cost
COST — requests, wasted 429 retries, and success time
----------------------------------------------------------
  client   requests   wasted-429s   succeeds-at
  honor    2          1             5
  ignore   4          3             7
----------------------------------------------------------
  ignoring the header adds load during the limit and finishes later -- worse on both axes.
```

Two numbers tell the story. Load: the honoring client made 2 requests (1 unavoidable initial 429, then the success); the ignoring client made 4 (3 wasted 429s, then the success). On a server that is rate-limiting because it is under pressure, those extra retries are the worst possible thing to send — they are the retry storm that turns a transient limit into a sustained overload, and a whole fleet of clients ignoring Retry-After can keep a server pinned in its limited state far longer than the limit was meant to last. Latency: the honoring client succeeded at t=5, the ignoring one at t=7. This is the counterintuitive part — you might expect that "trusting the server" and "waiting the full 5 seconds" would be slower than aggressively retrying, but it is faster, because the aggressive retries are all wasted (they cannot succeed before t=5) and the backoff then overshoots the reset. The server knew the answer was exactly 5; any client-side guess is either too small (wasted attempts) or too big (overshoot), and exponential backoff manages to be both in sequence. Reading the header is the only strategy that hits t=5 on the nose.

<svg role="img" aria-label="On a timeline the reset is at t=5; the ignoring client's backoff retries at 1 and 3 undershoot the reset and its retry at 7 overshoots it, while the honoring client's single retry lands exactly on 5" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">backoff undershoots (1,3) then overshoots (7); header hits 5 exactly</text>
  <line x1="30" y1="60" x2="285" y2="60" stroke="var(--grid)"/>
  <line x1="180" y1="40" x2="180" y2="80" stroke="var(--ink)"/><text x="164" y="34" fill="var(--ink)" font-size="7">reset t=5</text>
  <circle cx="60" cy="60" r="3" fill="var(--s2)"/><text x="44" y="52" fill="var(--s2)" font-size="6">t=1 too early</text>
  <circle cx="120" cy="60" r="3" fill="var(--s2)"/><text x="104" y="52" fill="var(--s2)" font-size="6">t=3 too early</text>
  <circle cx="240" cy="60" r="3" fill="var(--s2)"/><text x="220" y="76" fill="var(--s2)" font-size="6">t=7 too late</text>
  <circle cx="180" cy="60" r="4" fill="var(--s1)"/><text x="150" y="94" fill="var(--s1)" font-size="6">honor: t=5 exactly ✓</text>
</svg>
^ Exponential backoff misses the reset in both directions — its early retries (t=1, t=3) are too soon to succeed and its next (t=7) is too late — while honoring the header places the one retry exactly on the reset at t=5, the only value that is neither wasted nor overshoot.

```python filename=modules/ship-and-operate/code/retryafter-inter-01/retryafter.py:124-131 COMPLETE
    honor_two_requests = requests_count(honor) == 2
    print("  honor makes exactly 2 requests (one 429, one success) = %s" % honor_two_requests)

    honor_retries_at_reset = honor[-1][0] == lu
    print("  honor's retry lands exactly at the reset t=%d = %s" % (lu, honor_retries_at_reset))

    ignore_more_requests = requests_count(ignore) > requests_count(honor)
    print("  ignore makes more requests than honor = %s (%d vs %d)" % (ignore_more_requests, requests_count(ignore), requests_count(honor)))
```

## Definition of done

The self-test pins the honoring client's single well-timed retry against the ignoring client's extra in-window retries and later finish.

```python filename=modules/ship-and-operate/code/retryafter-inter-01/retryafter.py:133-138 COMPLETE
    ignore_retries_while_limited = sum(1 for t, r in ignore[1:] if r.startswith("429")) > 0
    early = [t for t, r in ignore if r.startswith("429") and t > 0]
    print("  ignore retries WHILE still limited (extra 429s) = %s (at t=%s, all < %d)" % (ignore_retries_while_limited, early, lu))

    honor_finishes_no_later = success_time(honor) <= success_time(ignore)
    print("  honor finishes no later than ignore = %s (t=%d vs t=%d)" % (honor_finishes_no_later, success_time(honor), success_time(ignore)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — ignoring Retry-After makes extra requests during the limit and finishes later; honoring retries once at the reset
--------------------------------------------------------------------------------------------------------------------------
  honor makes exactly 2 requests (one 429, one success) = True
  honor's retry lands exactly at the reset t=5 = True
  ignore makes more requests than honor = True (4 vs 2)
  ignore retries WHILE still limited (extra 429s) = True (at t=[1, 3], all < 5)
  honor finishes no later than ignore = True (t=5 vs t=7)
```

<svg role="img" aria-label="Honor wins on both axes: it uses 2 requests vs 4, and finishes at t=5 vs t=7" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">honoring the header wins on load AND latency</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">requests</text>
  <rect x="80" y="26" width="60" height="12" fill="var(--s1)"/><text x="144" y="36" fill="var(--muted)" font-size="7">honor 2</text>
  <rect x="80" y="40" width="120" height="12" fill="var(--s2)"/><text x="204" y="50" fill="var(--muted)" font-size="7">ignore 4</text>
  <line x1="14" y1="60" x2="286" y2="60" stroke="var(--grid)"/>
  <text x="10" y="76" fill="var(--muted)" font-size="7">succeeds at</text>
  <rect x="80" y="68" width="100" height="10" fill="var(--s1)"/><text x="184" y="77" fill="var(--muted)" font-size="7">honor t=5</text>
  <rect x="80" y="80" width="140" height="10" fill="var(--s2)"/><text x="224" y="89" fill="var(--muted)" font-size="7">ignore t=7</text>
</svg>
^ The honoring client uses fewer requests (2 vs 4) and finishes sooner (t=5 vs t=7) — ignoring Retry-After is not a speed-for-load trade-off, it loses on both, because the server's stated time is the exact answer the client can only mis-guess.

**Done means the double cost of ignoring the header is proven on real timing: honoring Retry-After makes 2 requests and its single retry lands exactly at the reset t=5, while ignoring it and backing off makes 4 requests — retrying at t=1 and t=3 inside the still-limited window — and finishes later at t=7, so a client must wait the server's Retry-After rather than apply its own backoff.**

## Boss fight

Predict two ways honoring Retry-After must be done carefully, because "trust the server's number" cannot be unconditional and the header comes in more than one form.

The first trap is that a Retry-After is untrusted input that can be absent, malformed, or absurd, so honoring it needs bounds and a fallback. The value can be huge — a misconfigured or hostile server can send Retry-After: 86400 (a full day) and a client that blindly obeys will stall for a day on a single request; so cap the honored wait at a sane maximum and, past that, treat the request as failed or fall back to bounded backoff rather than sleeping indefinitely. The header can also be missing entirely (many 429s and most 503s omit it) or malformed, and Retry-After has two legal formats — a delta in seconds (`Retry-After: 5`) and an HTTP date (`Retry-After: Wed, 21 Oct 2026 07:28:00 GMT`) — so a parser must handle both and, on a date, compute the delay against the client's own clock, which introduces clock-skew to guard (a slightly-off client clock can make the delay negative or too long). The disciplined design is: parse both forms, clamp to [0, max_wait], and when the header is absent or unparseable, fall back to the client's normal bounded exponential backoff — honor the header as the default and the best information available, but never as an unbounded command.

The second trap is that honoring the exact time synchronizes every client, so the reset moment needs jitter and the retry still needs an overall budget. If a thousand clients all received Retry-After 5 at the same instant (which is exactly what happens when a shared rate-limit window resets), and all of them honor it precisely, they all retry at the same t=5 and recreate the stampede that tripped the limit in the first place — a thundering herd synchronized by the very header meant to prevent overload. So a robust client adds a small random jitter on top of the honored wait (retry at 5 plus a random fraction of a second) to spread the herd across the reset, trading a tiny bit of latency for smoothing the load spike. And Retry-After governs one retry's timing, not whether to keep retrying forever: the request still needs an overall deadline / attempt budget, because a server that keeps returning 429 with Retry-After will otherwise loop indefinitely — at some point the client must give up, shed the request, or surface backpressure to its own caller. Honoring the header is the right timing for each retry; jitter and a retry budget are what keep a fleet of honoring clients from becoming a synchronized, unbounded load of their own.

**Honor Retry-After as the default but not unconditionally: it is untrusted input, so parse both its delta-seconds and HTTP-date forms (guarding clock skew on dates), clamp the wait to a sane maximum so an absurd value cannot stall you for a day, and fall back to bounded backoff when the header is absent or unparseable. And because honoring an exact time synchronizes every client whose window reset together, add a small jitter on top of the honored wait to break the thundering herd, and keep an overall retry budget / deadline so a server that keeps sending 429 does not loop the client forever.**

## External resources

The HTTP specifications for 429 and 503 and the Retry-After header (RFC 6585 and RFC 9110) — the two header formats, when servers send it, and the requirement that clients respect it.

Cloud provider and API rate-limiting guides (AWS, Google, Stripe, GitHub) — how production APIs signal rate limits with Retry-After / rate-limit headers and the client behavior they expect, including the jitter and cap guidance.

The companion backoff-jitter, circuit-breaker, and load-shedding modules in this topic — Retry-After is the server-directed version of retry timing that backoff guesses at, jitter keeps honoring clients from stampeding the reset, and a persistent 429 is a signal a circuit breaker or load shedding should ultimately act on.
