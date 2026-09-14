---
id: drain-inter-01
title: Drain on shutdown — stop accepting new work, finish the in-flight requests, then exit; a hard kill abandons everything in progress
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A worker in a fleet is stopped all the time — a deploy rolls it, an autoscaler scales it in, an operator restarts it — and at the instant of shutdown it is almost never idle; it is holding requests that are partway through. What happens to those requests is decided entirely by how the shutdown is done. A hard stop terminates the process immediately, so every in-flight request is abandoned mid-work: the client that was waiting gets an error or a timeout for work that may have been a millisecond from done, and any partial side effects are left dangling with no completion and no cleanup. A graceful drain does two things, in order. First it stops accepting new requests — it closes the door, so incoming work is rejected at the threshold and the load balancer routes it to a healthy worker; crucially this is a rejection, not a silent drop, so the caller learns immediately and retries elsewhere rather than being accepted here and then killed. Second, with no new work arriving, the worker processes the requests already in flight through to completion, and only then exits. The distinction between rejected and lost is the whole point: drain converts what would have been lost in-flight work into zero loss, and new arrivals from "accepted then abandoned" into "rejected up front so they go elsewhere". On a fixture where the worker holds three in-flight requests and two new ones arrive during shutdown, a hard stop loses all three (and drops the new ones too) while a drain completes all three, loses none, and rejects the two.
eli5: Imagine a shop that's about to close for the night. The rude way to close is to just switch off the lights and lock the door while three customers are still at the counter mid-purchase — their half-rung-up orders vanish, and they leave angry and empty-handed. The polite way has two steps: first you put up a "sorry, we're closed" sign on the door so no new customers walk in (they go to the shop down the street instead), and then you finish serving the three people already at the counter before you lock up. Nobody who was already being helped gets abandoned, and nobody new gets let in only to be kicked out. Shutting down a computer worker is the same: don't yank the plug while it's in the middle of jobs — turn away new jobs first, finish the ones in progress, then stop.
---

## Why this module

Shutdown is not a rare event in a fleet; it is a constant background process. Every deploy replaces workers, every autoscaling event removes them, every health check or operator action can restart one. So the behavior of a worker at the moment it stops is not an edge case — it is part of normal operation, executed thousands of times a day, and its correctness determines how many requests the fleet quietly drops.

The critical fact is that a busy worker at shutdown time is holding live work. Requests are in flight: accepted, partway processed, with a client blocked and waiting for the response. Those requests represent commitments the worker has already made. How the shutdown treats them is the entire question, and the two answers could not be more different in their effect on the caller.

A hard stop treats the process as disposable and the in-flight work as collateral. It exits immediately, and every held request dies with it — the client gets an error for work that was nearly done, and any half-applied side effect is orphaned. A graceful drain treats the in-flight work as a commitment to honor: it refuses new work so nothing more piles on, then finishes what it holds before exiting. This module runs a shutdown both ways and counts what is completed, lost, and rejected.

**A worker at shutdown holds in-flight requests it has already committed to; a hard stop abandons them as client errors, while a drain honors them by refusing new work first and finishing the rest before exiting.**

## Concepts

The key distinction is between a request that is lost and one that is rejected, because they look similar but mean opposite things to the caller. A lost request was accepted — the caller believes it is being handled — and then silently abandoned, so the caller waits, times out, and may not know whether the effect happened. A rejected request was turned away at the door before acceptance, so the caller gets an immediate, unambiguous signal and can retry on another worker. Rejection is a clean handoff; loss is a broken promise.

Drain works by ordering these two correctly. It rejects first — closing the door to new work — and only then drains. That order matters: if it kept accepting new requests while trying to finish, the in-flight set would never empty and shutdown would never complete. Refusing new work is what makes the in-flight set finite and lets the drain terminate. The two steps are a sequence, not a pair of independent switches.

There is a real bound that belongs with this: draining cannot take forever. A grace period caps how long the worker will wait for in-flight requests to finish before it gives up and hard-stops the stragglers. This is why the two designs are not opposites but endpoints — a hard stop is a drain with a zero-second grace period, and a good grace period is long enough for normal requests to finish but short enough that one stuck request cannot block a deploy indefinitely.

<svg role="img" aria-label="Two fates for a request: rejected before acceptance gives the caller an immediate signal to retry elsewhere, while lost after acceptance leaves the caller waiting on a broken promise" viewBox="0 0 440 130">
<rect x="20" y="30" width="180" height="70" fill="var(--panel)" stroke="var(--s1)"/>
<text x="110" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">rejected (before accept)</text>
<text x="110" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">immediate signal</text>
<text x="110" y="86" fill="var(--s1)" font-size="9" text-anchor="middle">caller retries elsewhere</text>
<rect x="240" y="30" width="180" height="70" fill="var(--panel)" stroke="var(--s2)"/>
<text x="330" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">lost (after accept)</text>
<text x="330" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">silent abandonment</text>
<text x="330" y="86" fill="var(--s2)" font-size="9" text-anchor="middle">caller waits, times out</text>
</svg>
^ A rejection reaches the caller as an immediate, actionable signal; a loss leaves them waiting on work that will never complete.

**A rejected request is a clean handoff and a lost one is a broken promise; drain rejects new work first so the in-flight set can empty, bounded by a grace period that makes a hard stop simply the zero-grace extreme.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/drain-inter-01. The fixture is the worker's state at the shutdown signal: the requests already in flight, and the new ones that arrive during the shutdown window.

```json filename=modules/orchestration-and-governance/code/drain-inter-01/drain.json:3-4 COMPLETE
  "inflight": ["r1", "r2", "r3"],
  "new_arrivals": ["r4", "r5"]
```

The hard stop terminates immediately — in-flight work is abandoned, and any new arrivals taken on are dropped too.

```python filename=modules/orchestration-and-governance/code/drain-inter-01/drain.py:34-36 COMPLETE
def hard_stop(inflight, new_arrivals):
    """Terminate immediately: in-flight work is abandoned, and any new arrivals taken on are dropped too."""
    return {"completed": [], "lost": list(inflight) + list(new_arrivals), "rejected": []}
```

The drain stops accepting new work, then finishes the in-flight requests before exiting.

```python filename=modules/orchestration-and-governance/code/drain-inter-01/drain.py:39-41 COMPLETE
def drain(inflight, new_arrivals):
    """Stop accepting new work (reject it), then finish the in-flight requests before exiting."""
    return {"completed": list(inflight), "lost": [], "rejected": list(new_arrivals)}
```

Before running it, predict: the hard stop should lose all five requests; the drain should complete the three in-flight, lose none, and reject the two new ones. Run `--outcome`:

```text filename=drain.py --outcome
OUTCOME — in-flight=['r1', 'r2', 'r3']  new arrivals during shutdown=['r4', 'r5']
------------------------------------------------------------
  hard stop  completed=[]  lost=['r1', 'r2', 'r3', 'r4', 'r5']  rejected=[]
  drain      completed=['r1', 'r2', 'r3']  lost=[]  rejected=['r4', 'r5']
```

The prediction holds. The hard stop completes nothing and loses all five — the three it was working on and the two it briefly accepted. The drain completes the three it had committed to, loses none, and turns the two new arrivals into rejections that route elsewhere. Same worker, same instant, opposite outcomes for every caller.

<svg role="img" aria-label="Two shutdown paths for the same three in-flight and two new requests: hard stop marks all five as lost, drain marks three completed and two rejected with none lost" viewBox="0 0 440 170">
<text x="110" y="18" fill="var(--ink)" font-size="11" text-anchor="middle">hard stop</text>
<rect x="30" y="30" width="160" height="24" fill="var(--panel)" stroke="var(--s2)"/>
<text x="110" y="46" fill="var(--s2)" font-size="10" text-anchor="middle">r1 r2 r3 lost</text>
<rect x="30" y="60" width="160" height="24" fill="var(--panel)" stroke="var(--s2)"/>
<text x="110" y="76" fill="var(--s2)" font-size="10" text-anchor="middle">r4 r5 lost</text>
<text x="110" y="104" fill="var(--s2)" font-size="10" text-anchor="middle">5 lost, 0 done</text>
<text x="330" y="18" fill="var(--ink)" font-size="11" text-anchor="middle">drain</text>
<rect x="250" y="30" width="160" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="46" fill="var(--s1)" font-size="10" text-anchor="middle">r1 r2 r3 completed</text>
<rect x="250" y="60" width="160" height="24" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="76" fill="var(--muted)" font-size="10" text-anchor="middle">r4 r5 rejected -&gt; elsewhere</text>
<text x="330" y="104" fill="var(--s1)" font-size="10" text-anchor="middle">0 lost, 3 done</text>
</svg>
^ The same five requests: a hard stop loses every one, a drain completes the committed three and cleanly rejects the two newcomers.

Now the number that matters to the fleet — how many requests each strategy abandons. Run `--tally`:

```text filename=drain.py --tally
TALLY — abandoned (lost) requests by shutdown strategy
--------------------------------------------
  hard stop  lost = 5   (completed 0, rejected 0)
  drain      lost = 0   (completed 3, rejected 2)
```

Five lost versus zero. The drain's two rejected requests are not in the loss column, because a rejection is a clean signal the caller acts on immediately — it is not a broken promise. That reclassification, from lost to rejected, is exactly what draining buys.

<svg role="img" aria-label="A timeline of the drain: at the signal the door closes rejecting new arrivals, then the in-flight requests finish one by one, then the process exits" viewBox="0 0 440 130">
<line x1="30" y1="60" x2="410" y2="60" stroke="var(--line)"/>
<circle cx="60" cy="60" r="5" fill="var(--ink)"/>
<text x="60" y="40" fill="var(--ink)" font-size="9" text-anchor="middle">signal</text>
<text x="60" y="80" fill="var(--muted)" font-size="8" text-anchor="middle">close door</text>
<line x1="60" y1="90" x2="60" y2="110" stroke="var(--muted)"/>
<text x="60" y="122" fill="var(--muted)" font-size="8" text-anchor="middle">reject r4,r5</text>
<circle cx="160" cy="60" r="4" fill="var(--s1)"/>
<text x="160" y="48" fill="var(--s1)" font-size="8" text-anchor="middle">r1 done</text>
<circle cx="240" cy="60" r="4" fill="var(--s1)"/>
<text x="240" y="48" fill="var(--s1)" font-size="8" text-anchor="middle">r2 done</text>
<circle cx="320" cy="60" r="4" fill="var(--s1)"/>
<text x="320" y="48" fill="var(--s1)" font-size="8" text-anchor="middle">r3 done</text>
<circle cx="390" cy="60" r="5" fill="var(--ink)"/>
<text x="390" y="40" fill="var(--ink)" font-size="9" text-anchor="middle">exit</text>
</svg>
^ Drain in sequence: the signal closes the door and rejects newcomers, the in-flight requests finish, and only then does the process exit.

## Build

The self-test plants the failure and names each claim as a boolean flag. It runs both strategies on the same worker state and then compares their outcomes.

```python filename=modules/orchestration-and-governance/code/drain-inter-01/drain.py:73-75 COMPLETE
    inflight, new = data["inflight"], data["new_arrivals"]
    h = hard_stop(inflight, new)
    d = drain(inflight, new)
```

It checks that the hard stop loses every in-flight request and completes nothing, while the drain completes every in-flight request, loses nothing, and rejects the new arrivals rather than accepting-then-losing them.

```python filename=modules/orchestration-and-governance/code/drain-inter-01/drain.py:77-89 COMPLETE
    hard_loses_inflight = all(r in h["lost"] for r in inflight) and len(inflight) > 0
    print("  hard stop: every in-flight request is lost = %s (%s)" % (hard_loses_inflight, h["lost"]))

    hard_completes_nothing = h["completed"] == []
    print("  hard stop: nothing is completed after the signal = %s" % hard_completes_nothing)

    drain_completes_inflight = d["completed"] == list(inflight)
    print("  drain: every in-flight request completes = %s (%s)" % (drain_completes_inflight, d["completed"]))

    drain_loses_nothing = d["lost"] == []
    print("  drain: no request is lost = %s" % drain_loses_nothing)

    drain_rejects_new = d["rejected"] == list(new) and all(n not in d["lost"] for n in new)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the drain ever loses an in-flight request or accepts a new one instead of rejecting it:

```text filename=drain.py --check
SELF-TEST — a hard stop abandons the in-flight requests; draining finishes them and rejects new arrivals, losing none
------------------------------------------------------------------------------------------------------------------------
  hard stop: every in-flight request is lost = True (['r1', 'r2', 'r3', 'r4', 'r5'])
  hard stop: nothing is completed after the signal = True
  drain: every in-flight request completes = True (['r1', 'r2', 'r3'])
  drain: no request is lost = True
  drain: new arrivals are rejected (not accepted-then-lost) = True (['r4', 'r5'])
------------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  hard_loses_inflight=True  hard_completes_nothing=True  drain_completes_inflight=True  drain_loses_nothing=True  drain_rejects_new=True
```

**The self-test checks that new arrivals land in rejected and not in lost — the distinction that separates a clean handoff from a broken promise, which a drain that merely stopped accepting-and-dropping would fail.**

## Definition of done

You can explain why shutdown is a constant, normal event in a fleet, not an edge case, and why a busy worker holds committed in-flight work at that moment.
You can distinguish a lost request (accepted then abandoned) from a rejected one (turned away before acceptance) and say why the caller experiences them oppositely.
You can state drain's two steps in order — reject new work, then finish in-flight — and explain why the order is what lets shutdown terminate.
You can describe the grace period and frame a hard stop as a drain with zero grace.
You can predict what a hard stop does to a half-applied side effect and why in-flight work needs completion or cleanup, not silent abandonment.

## Boss fight

Add a grace period that is too short: suppose one in-flight request needs longer than the grace window allows. The drain finishes the requests that fit, then hard-stops whatever remains when the window expires — so a stuck or very slow request still becomes a loss, just a smaller set than a zero-grace hard stop. The lesson sharpens: draining is bounded, and the grace period is a real tuning knob. Too short and it degenerates toward a hard stop; too long and one hung request stalls every deploy. The right value clears the normal request-duration distribution with margin but does not wait on the pathological tail.

Now consider the ordering failure. Suppose the worker starts draining but forgets to close the door first, so new requests keep arriving and being accepted while it tries to finish. The in-flight set never shrinks to empty — every completion is replaced by a fresh arrival — and the drain never terminates, so the deploy hangs until it is force-killed, at which point everything still in flight is lost. This is why reject-first is not optional: without it, drain has no stopping condition. The two steps must happen in sequence, closing the door before emptying the room.

**Draining is reject-first and time-bounded: without closing the door the in-flight set never empties and shutdown hangs, and without a grace period a single stuck request would block the deploy forever — so the grace period turns an unbounded wait into a bounded one that still loses only the pathological tail.**

## External resources

Kubernetes documents the pod termination lifecycle — SIGTERM, the terminationGracePeriodSeconds window, then SIGKILL — which is exactly reject-first draining with a bounded grace period.
Load-balancer "connection draining" or "deregistration delay" features (in AWS, GCP, and Envoy) implement the door-closing step: stop routing new connections to an instance while letting existing ones finish.
The topic's own modules on backpressure and on dead-lettering cover the adjacent question of what to do with work a healthy worker cannot currently accept.
