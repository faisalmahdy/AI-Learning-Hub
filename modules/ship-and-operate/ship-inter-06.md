---
id: ship-inter-06
title: Graceful shutdown drains in-flight requests — a hard stop drops them all
topic: ship-and-operate
level: intermediate
status: ready
time: 8-10h
summary: A deploy or scale-down sends a shutdown signal to a service still working, and what it does next decides whether those users get a result or an error — a graceful shutdown stops accepting new requests, rejects them cleanly so the client retries another instance, lets the in-flight requests finish up to a drain deadline, then exits, completing four of five in-flight requests and force-dropping only the straggler past the deadline. A hard shutdown exits immediately and drops all five in-flight requests, connection reset, work lost, for errors the user did nothing to cause. Draining is bounded by the deadline so shutdown cannot hang forever, so the trade is exact: graceful drops only the stragglers that exceed the deadline while a hard stop drops everything in flight — and the difference is entirely in whether the process waits for its own in-flight work before exiting.
eli5: When a shop closes, the good version locks the front door so no new customers come in, but still serves everyone already inside before turning off the lights. The bad version just flips off the lights and shoves everyone out mid-purchase. Both close the shop; only one treats the people already being helped like they matter.
---

## Why this module

Services restart constantly — every deploy, every scale-down, every node recycle sends a shutdown signal to a process that is, at that moment, in the middle of serving real requests. What the process does in the seconds after that signal is one of the most user-visible pieces of operational behavior, and the naive implementation — exit when told — drops every request in flight, turning routine deploys into a stream of user-facing errors. This module builds graceful shutdown, the draining behavior that finishes in-flight work before exiting, and the hard-stop bug that does not.

<svg viewBox="0 0 700 130" role="img" aria-label="A left-to-right sequence: shutdown signal arrives, then 'stop accepting new (reject cleanly)', then 'drain in-flight to deadline', then 'exit'. Below, a shorter arrow labelled hard stop jumps straight from signal to exit, skipping the middle.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">the graceful sequence — and the hard stop that skips the middle</text>
    <rect x="30" y="34" width="90" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="75" y="51" text-anchor="middle" fill="var(--ink)">signal</text>
    <path d="M120 47 L150 47" stroke="var(--muted)"></path>
    <rect x="150" y="34" width="140" height="26" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="220" y="51" text-anchor="middle" fill="var(--acc-ink)">stop accept (reject)</text>
    <path d="M290 47 L320 47" stroke="var(--muted)"></path>
    <rect x="320" y="34" width="150" height="26" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="395" y="51" text-anchor="middle" fill="var(--acc-ink)">drain to deadline</text>
    <path d="M470 47 L500 47" stroke="var(--muted)"></path>
    <rect x="500" y="34" width="80" height="26" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="540" y="51" text-anchor="middle" fill="var(--ink)">exit</text>
    <path d="M75 68 Q 75 100 300 100 Q 540 100 540 62" fill="none" stroke="var(--s2)" stroke-dasharray="4 3"></path>
    <text x="300" y="118" text-anchor="middle" fill="var(--s2)">hard stop: signal -&gt; exit, skipping stop-accept and drain</text>
  </g>
</svg>
^ Graceful walks signal → stop-accept → drain → exit; the hard stop's dashed path jumps straight from signal to exit, dropping the in-flight work the middle two steps would have saved.

The shape is stop-accept, drain, exit. When the shutdown signal arrives, the service first stops accepting new requests — and rejects the ones still arriving cleanly, with a response that tells the client to retry another instance, rather than dropping the connection. Then it drains: it lets the requests already in flight run to completion. Only when they are done does it exit. The one subtlety is that draining must be bounded, or a single slow request could hang the shutdown forever, so a drain deadline caps the wait — an in-flight request still running when the deadline hits is force-terminated. The hard-stop bug skips all of this: it exits the moment the signal arrives, and every in-flight request is dropped mid-flight, a connection reset the client sees as a failure. The difference between the two is entirely whether the process waits for its own in-flight work, and it is the difference between a silent deploy and a spike of errors.

You need no prior module, only the idea of a service handling requests. Everything runs offline against a shutdown fixture — five in-flight requests with remaining work, a drain deadline, and new requests arriving — stdlib Python 3, `$0.00`. Ticks stand in for time, so the run is deterministic. The instinct to unlearn is that shutting down means exiting. Shutting down gracefully means refusing new work, finishing the work you already accepted, and only then exiting — because the requests in flight are ones you already promised to answer.

Here is the graceful shutdown draining its in-flight work:

```
# modules/ship-and-operate/code/ship-inter-06/ — COMPLETE, run from that directory
$ python3 drain.py --drain

DRAIN — graceful shutdown (drain deadline = 5 ticks)
------------------------------------------------------------------
  completed (finished before exit): ['r1', 'r2', 'r3', 'r4']
  force-dropped (past the deadline): ['r5']
  new requests cleanly rejected:     3  (client retries another instance)
```

run: 2026-08-26 · deterministic; ticks are a fixture · 5 in-flight · `python3 drain.py --drain`

Four of five in-flight requests finish before the process exits, only r5 — which needed longer than the drain deadline — is force-dropped, and the three new requests are cleanly rejected so their clients retry elsewhere. This module is that outcome and what a hard stop does instead.

## Concepts

Named here so you can find them again; each is built below.

- **Shutdown signal** — the deploy/scale-down event telling the service to stop.
- **In-flight request** — a request already being processed when the signal arrives.
- **Graceful shutdown (draining)** — stop accepting new work, finish in-flight, then exit.
- **Clean rejection** — refusing a new request with a retry-able response, not a dropped connection.
- **Drain deadline** — the bound on how long to wait for in-flight requests before force-terminating.
- **Hard stop** — the bug: exit immediately, dropping every in-flight request.

## Worked example

Source: the graceful-shutdown pattern every server framework and orchestrator implements (SIGTERM handling, connection draining, Kubernetes preStop and terminationGracePeriod); the in-flight requests here stand in for real connections so the completed and dropped counts are exact and checkable.

Script and fixture: `modules/ship-and-operate/code/ship-inter-06/` — `drain.py`, and `shutdown.json`, five in-flight requests, a drain deadline of 5, three arriving requests. Every command runs from there.

### Graceful: finish in-flight, bounded by the deadline

The graceful shutdown lets each in-flight request finish if it fits the drain window, and force-terminates only those that do not.

```
# drain.py:38-51 — COMPLETE (drain in-flight to the deadline; reject new cleanly)
def graceful_shutdown(data):
    """Stop new requests; finish in-flight up to the drain deadline; force-drop stragglers."""
    deadline = data["drain_deadline"]
    completed, force_dropped = [], []
    for req in data["in_flight"]:
        if req["ticks_remaining"] <= deadline:   # finishes within the drain window
            completed.append(req["id"])
        else:                                    # still running at the deadline -> terminated
            force_dropped.append(req["id"])
    new_rejected = data["new_requests"]          # cleanly rejected -> client retries elsewhere
    return completed, force_dropped, new_rejected
```

Each in-flight request is checked against the deadline: r1 through r4 need 2, 3, 1, and 4 ticks, all within the 5-tick window, so they complete; r5 needs 9, past the deadline, so it is force-dropped. The new requests are rejected cleanly — the `new_rejected` count — which in a real service means a 503 with a retry hint, so the client immediately tries another instance instead of seeing a dropped connection. The deadline is what makes this safe to run: without it, r5's 9 ticks (or a hung request's infinity) would hold the shutdown open indefinitely, so draining is generous but bounded.

<svg viewBox="0 0 700 200" role="img" aria-label="A timeline from 0 to the drain deadline at 5 ticks. Bars for r1 (2), r2 (3), r3 (1), r4 (4) all end at or before the deadline line and are marked completed. r5's bar extends to 9, past the deadline, and is cut off at the line and marked force-dropped.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">in-flight requests draining; the deadline at 5 bounds the wait</text>
    <line x1="120" y1="30" x2="120" y2="180" stroke="var(--grid)"></line>
    <line x1="470" y1="30" x2="470" y2="180" stroke="var(--acc)" stroke-dasharray="4 3"></line>
    <text x="470" y="28" text-anchor="middle" fill="var(--acc-ink)" font-size="8">deadline 5</text>
    <rect x="120" y="42" width="140" height="16" fill="var(--s1)"></rect><text x="270" y="54" fill="var(--s1)" font-size="8">r1 (2) done</text>
    <rect x="120" y="66" width="210" height="16" fill="var(--s1)"></rect><text x="340" y="78" fill="var(--s1)" font-size="8">r2 (3) done</text>
    <rect x="120" y="90" width="70" height="16" fill="var(--s1)"></rect><text x="200" y="102" fill="var(--s1)" font-size="8">r3 (1) done</text>
    <rect x="120" y="114" width="280" height="16" fill="var(--s1)"></rect><text x="410" y="126" fill="var(--s1)" font-size="8">r4 (4) done</text>
    <rect x="120" y="138" width="350" height="16" fill="var(--s2)"></rect><rect x="470" y="138" width="140" height="16" fill="var(--s2)" opacity="0.25"></rect><text x="470" y="168" fill="var(--s2)" font-size="8">r5 (9) cut at the deadline -> force-dropped</text>
  </g>
</svg>
^ Every request that fits inside the drain window runs to completion; only r5, which extends past the deadline, is cut off. The deadline is the vertical line that turns an unbounded wait into a bounded one.

### Hard stop: drop everything in flight

The bug exits the instant the signal arrives, with no draining at all.

```
# drain.py:54-58 — COMPLETE (the bug: exit now, drop every in-flight request)
def hard_shutdown(data):
    """The bug: exit immediately. Every in-flight request is dropped."""
    dropped = [req["id"] for req in data["in_flight"]]
    new_dropped = data["new_requests"]           # dropped mid-connection, not cleanly rejected
    return dropped, new_dropped
```

Every in-flight request — all five, including r1 which needed just 2 more ticks — is dropped, the connection reset under the client mid-response. Run it:

```
# $ python3 drain.py --hard
#   in-flight DROPPED (connection reset): ['r1', 'r2', 'r3', 'r4', 'r5']
#   new requests dropped mid-connection:  3
```

run: 2026-08-26 · deterministic · `python3 drain.py --hard`

Five in-flight requests lost, and the three arriving requests dropped mid-connection rather than cleanly rejected, so their clients see a hard failure instead of a retry hint. Every one of these is an error a user did nothing to cause — they made a normal request to a healthy service that happened to be redeploying, and the process threw their work away because it could not be bothered to wait a few ticks. Multiply by the request rate and every deploy becomes a visible blip of errors.

<svg viewBox="0 0 700 150" role="img" aria-label="Two bars comparing requests saved. Graceful: 4 completed (green) out of 5 in-flight, 1 dropped. Hard: 0 completed, 5 dropped (all red). The graceful bar is mostly green, the hard bar entirely red.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">in-flight requests saved vs dropped (of 5)</text>
    <text x="20" y="52" fill="var(--ink)">graceful</text>
    <rect x="130" y="40" width="360" height="20" fill="var(--s1)"></rect><text x="310" y="55" text-anchor="middle" fill="var(--panel)" font-size="8">4 completed</text>
    <rect x="490" y="40" width="90" height="20" fill="var(--s2)"></rect><text x="535" y="55" text-anchor="middle" fill="var(--panel)" font-size="8">1</text>
    <text x="20" y="92" fill="var(--ink)">hard</text>
    <rect x="130" y="80" width="450" height="20" fill="var(--s2)"></rect><text x="355" y="95" text-anchor="middle" fill="var(--panel)" font-size="8">5 dropped</text>
    <text x="130" y="128" fill="var(--muted)" font-size="8">graceful saves four requests the hard stop throws away — the same deploy, seconds apart</text>
  </g>
</svg>
^ Graceful completes four of five and drops only the straggler; the hard stop drops all five. The work is identical; the only variable is whether the process waited for its in-flight requests.

**Graceful shutdown stops accepting new requests, rejects them cleanly, finishes the in-flight work up to a drain deadline, and only then exits — a hard stop exits immediately and drops every in-flight request, so the difference between a silent deploy and a spike of user-facing errors is whether the process waits for the work it already accepted.**

### The self-test

The `--check` mode asserts the drain and the failure: graceful completes what fits the deadline, force-drops only stragglers, is bounded, while hard drops everything and graceful saves work hard loses.

```
# $ python3 drain.py --check
#   drain completes the in-flight within the deadline = True (['r1', 'r2', 'r3', 'r4'])
#   drain force-drops only stragglers past the deadline = True (['r5'])
#   drain is bounded but does not drop everything = True (1 of 5 dropped)
#   hard shutdown drops ALL in-flight requests = True (5)
#   graceful shutdown saves work a hard stop loses = True (4 completed vs 0)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 drain.py --check`

The decisive comparison is the two policies' fates for the in-flight set — graceful completing what fits, hard dropping all:

```
# drain.py:92-105 — COMPLETE (graceful completes the deadline-fitting set; hard drops all)
    should_complete = [r["id"] for r in data["in_flight"] if r["ticks_remaining"] <= deadline]
    drain_completes = completed == should_complete and len(completed) > 0

    dropped, _ = hard_shutdown(data)
    hard_drops_all = set(dropped) == set(in_flight_ids)
```

`drain_completes` requires graceful to complete exactly the requests that fit the deadline; `hard_drops_all` requires the hard stop to drop the entire in-flight set — one policy honoring its accepted work, the other abandoning it.

The `drain_completes` line is the correctness anchor: exactly the in-flight requests that fit the deadline must complete, and if the drain loop were wrong that set would change. The `only_stragglers` line guards the deadline's semantics — nothing under the deadline may be dropped, and nothing over it kept — so the force-termination is proven to hit only genuine stragglers. The payoff assertion compares what each policy salvages from the in-flight set:

```
# drain.py:108 — COMPLETE (graceful saves work a hard stop loses)
    drain_saves_more = len(completed) > len(in_flight_ids) - len(dropped)
```

And `drain_saves_more` makes the payoff explicit: graceful completes four requests that the hard stop loses entirely, which is the whole reason to drain.

### The running tally

| shutdown | in-flight completed | in-flight dropped | new requests |
|---|---|---|---|
| graceful (drain) | 4 (r1–r4) | 1 (r5, past deadline) | 3 cleanly rejected |
| hard (exit now) | 0 | 5 (all) | 3 dropped mid-connection |

The completed column is the difference: graceful finishes four requests, the hard stop finishes none. And the new-requests column is the quieter half — graceful rejects them cleanly so clients retry, while the hard stop drops them mid-connection, converting even the requests it was never going to serve into hard errors. Both shut the process down; only one honors the requests it already accepted and redirects the ones it cannot. The drop count under a hard stop scales with your traffic, which is why graceful shutdown is not a nicety but the baseline for deploying a service without an error spike.

### What we did not settle

Draining is one piece of a clean shutdown. It must coordinate with the load balancer: the instance has to be removed from rotation before or as it stops accepting, or new requests keep arriving at a draining instance — Kubernetes handles this with a preStop hook and a readiness probe that fails first. The drain deadline needs to exceed your longest normal request, or you routinely force-drop legitimate work; it is usually set from the p99 latency plus margin. Long-lived connections (websockets, streams, long polls) need their own handling, since they never naturally complete within a deadline. And in-flight requests with side effects should be idempotent, so a client's retry of a force-dropped request is safe — which ties back to the idempotency module. The core here — stop accept, drain to a deadline, then exit — is the invariant every graceful shutdown builds on.

## Build

The practice in one paragraph: on a shutdown signal, stop accepting new requests and reject arrivals with a retry-able response; drain the in-flight requests, letting them finish; bound the drain with a deadline sized above your p99 latency, force-terminating only stragglers; and remove the instance from the load balancer first so new work stops arriving. Make side-effecting requests idempotent so a client's retry of a dropped request is safe, and handle long-lived connections explicitly.

We opened on the graceful drain. The number that separates it from a hard stop is the completed count:

```
# modules/ship-and-operate/code/ship-inter-06/ — COMPLETE, run from that directory
$ python3 drain.py --hard
  in-flight DROPPED (connection reset): ['r1', 'r2', 'r3', 'r4', 'r5']
```

Now build it yourself. Model a service with in-flight requests and a shutdown signal, and implement both a graceful drain (bounded by a deadline) and a hard stop. Your number to beat is not shutdown speed; it is **the count of in-flight requests completed before exit, which graceful maximizes and a hard stop leaves at zero**, plus force-dropping only the stragglers past the deadline. Then hard-stop and watch the in-flight work vanish. Bring back both policies' completed and dropped counts. Good luck.

## Definition of done

- [ ] A service with in-flight requests and a shutdown signal
- [ ] A graceful shutdown that stops accepting new requests and rejects them cleanly
- [ ] In-flight requests drained to completion, bounded by a drain deadline
- [ ] Only stragglers past the deadline force-terminated
- [ ] A hard-stop policy that drops every in-flight request, for contrast
- [ ] Confirmation graceful completes the in-flight that fit the deadline and hard completes none
- [ ] `python3 drain.py --check` printing SELF-TEST PASS: drain-completes, only-stragglers, bounded, hard-drops-all, drain-saves-more
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What are the three steps of a graceful shutdown, in order?
2. Why must a new request be cleanly rejected rather than have its connection dropped during shutdown?
3. What is the drain deadline for, and what goes wrong without it? What goes wrong if it is set too short?
4. A hard stop drops requests the user did nothing wrong to cause. Explain how a routine deploy becomes an error spike.
5. Your own service was shut down both ways. How many in-flight requests completed under each, and which were force-dropped?

## External resources

- Kubernetes documentation on pod termination (SIGTERM, preStop, terminationGracePeriodSeconds) — my summary: the production shutdown sequence — remove from endpoints, run preStop, send SIGTERM, wait the grace period, then SIGKILL — that implements exactly the drain-then-exit pattern here; read it for how draining coordinates with the load balancer.
- Server-framework graceful-shutdown guides (e.g. Go net/http Shutdown, Node server.close) — my summary: the stop-accepting-then-wait-for-in-flight APIs and their timeouts; read it for the concrete calls that drain connections in a real server.
- This hub, *ship-inter-02* — modules/ship-and-operate/ship-inter-02.md — my summary: the idempotency module; read it for why a force-dropped request's retry must be idempotent to be safe, the guarantee that makes bounded draining acceptable.
