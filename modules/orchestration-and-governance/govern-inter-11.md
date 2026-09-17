---
id: govern-inter-11
title: Partition the worker pool into bulkheads — or one hung dependency holds every worker and starves the rest
topic: orchestration-and-governance
level: intermediate
status: ready
time: 22 min
summary: A shared worker pool couples the fate of every dependency: when one hangs, its stuck requests hold all the workers and unrelated requests starve. Splitting the pool into per-dependency bulkheads caps the damage. A 6-worker shared pool serves 0 of 5 healthy requests when a dependency hangs; two bulkheads of 3 serve all 5.
eli5: A ship's hull is split into sealed compartments so a hole in one doesn't sink the whole boat — only that compartment floods. If your workers all share one pool and one slow service jams them, everything stops. Give each service its own set of workers, and a jam in one leaves the others still moving.
---

## Why this module

The failure this prevents is one slow dependency taking down services that have nothing to do with it.

Picture a pool of workers — threads, connections, goroutines, whatever does your concurrent work — shared across every downstream dependency your service calls. Normally this is efficient: any worker can serve any request, so the pool flexes to wherever the load is. But it also means every dependency shares one finite resource, and that shared resource is a shared point of failure. When one dependency hangs — stops responding, so its requests block holding a worker and never release it — those stuck requests pile up. Each one occupies a worker indefinitely. Given enough hung requests, they hold every worker in the pool. Now a request arrives for a completely healthy, unrelated dependency, and there is no free worker for it. It is starved by a failure it had nothing to do with.

This is how a partial outage becomes total. Dependency X, some non-critical service, hangs. Its requests slowly consume the shared pool. Within seconds every worker is stuck on X, and requests for dependency Y — your core, healthy, fast service — cannot get a worker. Y is down, not because Y failed, but because X did and they shared a pool. The blast radius of X's failure is the entire service.

The fix is the bulkhead, named for the sealed compartments that keep a breach in one part of a ship's hull from flooding the whole vessel. Partition the pool: give each dependency a bounded share of workers, and let a request use only workers from its own partition. Now when X hangs, it can hold at most its share; the rest of the pool is untouched, and Y's requests draw from Y's own workers and keep being served. You give up some peak flexibility — no single dependency can burst across the whole pool anymore — in exchange for isolation.

We will run one hung dependency against a shared pool and against bulkheads. Shared, the six workers all end up held by the hung dependency and zero of five healthy requests get served. Split into two bulkheads of three, the hung dependency saturates only its three, and all five healthy requests are served.

**A shared worker pool couples every dependency to every other; one that hangs holds all the workers and starves the healthy ones, and bulkheads cap that damage to a partition.**

## Concepts

The mechanism of the failure is resource exhaustion through a shared pool. A worker is held for the duration of a request, and a hung dependency makes that duration effectively infinite — the request never completes, so the worker is never returned. Each hung request is a permanently lost worker. The pool has a fixed size, so it takes only as many hung requests as there are workers to exhaust it completely, after which every subsequent request of any kind blocks. The healthy dependency's requests are fast and would return their workers instantly — but they can never acquire one, because the hung dependency got there first and will not let go.

The bulkhead breaks the coupling by making the shared resource not shared. Instead of one pool of N workers, you have per-dependency partitions summing to N, and admission is scoped: an X request may only use X's partition, a Y request only Y's. This changes the exhaustion arithmetic entirely. X hanging can exhaust X's partition and no more; the moment X's share is full, further X requests are rejected or queued *within X's allocation*, and they cannot reach into Y's workers. Y's partition is mathematically untouchable by X, so Y's availability is now independent of X's health. Isolation is not a heuristic here — it is a hard bound set by the partition size.

The cost is real and worth naming. A shared pool can put all N workers on whichever dependency needs them right now, so it handles bursty, uneven load better; bulkheads cap each dependency below N, so a legitimate burst to one dependency cannot borrow idle workers from another and may be throttled while workers sit idle in other partitions. You are trading peak utilization for fault isolation. That trade is usually worth it for dependencies whose failures you cannot afford to let cascade, and the partition sizes are the dial: bigger shares for the hot paths, but never the whole pool for any one, so no single dependency can ever consume everything.

This is why mature systems isolate their dependency pools — separate connection pools per database, separate thread pools per downstream service, concurrency limits per route. The shared pool is the default because it is simplest and most efficient under healthy load, and it is exactly the wrong default the first time a dependency hangs.

**A hung request is a permanently lost worker, so a shared pool falls to whichever dependency hangs; a bulkhead makes each partition's availability a hard, independent bound.**

## Worked example

The fixture is an arrival stream, a pool size, and the bulkhead partition.

```json filename=modules/orchestration-and-governance/code/govern-inter-11/requests.json:7-12 COMPLETE
  "workers": 6,
  "bulkhead": {
    "X": 3,
    "Y": 3
  },
  "arrivals": [
```

Six workers, split three and three between dependencies X and Y. The arrival stream front-loads a burst of X — the hung dependency's backlog — before the healthy Y requests arrive.

```text filename=modules/orchestration-and-governance/code/govern-inter-11/bulkhead.py --stream
STREAM — 11 requests; X is hung (holds its worker), Y is healthy (releases at once)
----------------------------------------------------------
  arrivals: X X X X X X Y Y Y Y Y
  6 X (hung) and 5 Y (healthy); pool = 6 workers.
----------------------------------------------------------
  the X requests never free their worker; the question is whether Y can still get one.
```

Six hung X requests, then five healthy Y requests. The shared-pool admission holds a worker for every X and never releases it; a Y is served only if a worker is free when it arrives.

```python filename=modules/orchestration-and-governance/code/govern-inter-11/bulkhead.py:42-56 COMPLETE
def serve_shared(arrivals, workers):
    """One shared pool. X requests hold a worker forever; Y releases at once. Returns per-request served flags."""
    held = 0  # workers held by hung X requests (never released within the run)
    log = []
    for dep in arrivals:
        free = workers - held
        if dep == "X":
            if free > 0:
                held += 1            # X grabs a worker and hangs onto it
                log.append((dep, True))
            else:
                log.append((dep, False))
        else:  # Y needs a momentarily-free worker, then releases it immediately
            log.append((dep, free > 0))
    return log
```

The bulkhead admission is the same logic, but each dependency draws only from its own cap.

```python filename=modules/orchestration-and-governance/code/govern-inter-11/bulkhead.py:59-74 COMPLETE
def serve_bulkhead(arrivals, caps):
    """Partitioned pool: each dependency draws only from its own share. X can't touch Y's workers."""
    held = {dep: 0 for dep in caps}
    log = []
    for dep in arrivals:
        free = caps[dep] - held[dep]
        if dep == "X":
            if free > 0:
                held[dep] += 1
                log.append((dep, True))
            else:
                log.append((dep, False))
        else:
            log.append((dep, free > 0))
    return log
```

The metric is how many healthy Y requests got served.

```python filename=modules/orchestration-and-governance/code/govern-inter-11/bulkhead.py:76-77 COMPLETE
def y_served(log):
    return sum(1 for dep, ok in log if dep == "Y" and ok)
```

Predict: shared, the six X requests hold all six workers, so all five Y requests find nothing free — 0 of 5. Bulkhead, X fills its three (three more X rejected within X's partition) and Y's three workers are all free — 5 of 5. Run it.

```text filename=modules/orchestration-and-governance/code/govern-inter-11/bulkhead.py --serve
SERVE — healthy (Y) requests served, shared pool vs bulkheads
--------------------------------------------------------
  shared pool (6 workers):        Y served 0 of 5
  bulkheads (X:3, Y:3):           Y served 5 of 5
--------------------------------------------------------
  shared: the hung X requests hold every worker; bulkheads: Y keeps its own.
```

Shared, the healthy dependency is completely starved — zero of five, a total outage of a service that never failed. Bulkhead, all five served. The hung X requests are identical in both runs; the only difference is whether they could reach Y's workers. In the shared pool they held all six and Y got nothing; in the bulkhead they were capped at three and Y's three were untouchable. That is fault isolation as a hard number: 0 versus 5.

<svg role="img" aria-label="Healthy requests served out of five: shared pool zero, bulkheads five, from the same six workers" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">healthy (Y) requests served, of 5 — same 6 workers</text>
  <line x1="60" y1="120" x2="440" y2="120" stroke="var(--line)"/>
  <rect x="100" y="118" width="90" height="2" fill="var(--s2)" stroke="var(--line)"/><text x="124" y="112" font-family="var(--mono)" font-size="11" fill="var(--s2)">0</text><text x="98" y="138" font-family="var(--mono)" font-size="9" fill="var(--muted)">shared pool</text>
  <rect x="280" y="40" width="90" height="80" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="316" y="34" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">5</text><text x="288" y="138" font-family="var(--mono)" font-size="9" fill="var(--muted)">bulkheads</text>
</svg>
^ The same six workers serve zero healthy requests when pooled and all five when partitioned — the arrangement, not the resource, is the difference.

<svg role="img" aria-label="Shared pool: all six workers held by hung X requests, so five Y requests bounce off with no free worker" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">shared pool — one hung dependency holds everything</text>
  <g stroke="var(--line)">
    <rect x="30" y="40" width="50" height="34" fill="var(--s2)"/><rect x="90" y="40" width="50" height="34" fill="var(--s2)"/><rect x="150" y="40" width="50" height="34" fill="var(--s2)"/>
    <rect x="210" y="40" width="50" height="34" fill="var(--s2)"/><rect x="270" y="40" width="50" height="34" fill="var(--s2)"/><rect x="330" y="40" width="50" height="34" fill="var(--s2)"/>
  </g>
  <text x="150" y="62" font-family="var(--mono)" font-size="10" fill="var(--ink)">6 workers, all held by X (hung)</text>
  <text x="30" y="110" font-family="var(--mono)" font-size="10" fill="var(--s2)">Y Y Y Y Y  →  no free worker</text>
  <text x="30" y="132" font-family="var(--mono)" font-size="11" fill="var(--s2)">healthy requests served: 0 of 5</text>
</svg>
^ Six hung X requests hold all six shared workers, so every healthy Y request bounces off — a total outage caused by an unrelated dependency.

<svg role="img" aria-label="Bulkhead pool: X's partition of three is full of hung requests, Y's partition of three is free and serving all five Y requests" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">bulkheads — X's failure capped at its partition</text>
  <rect x="24" y="34" width="200" height="70" fill="none" stroke="var(--line)" stroke-dasharray="4 3"/><text x="34" y="50" font-family="var(--mono)" font-size="9" fill="var(--s2)">X partition (cap 3)</text>
  <g stroke="var(--line)"><rect x="34" y="60" width="50" height="34" fill="var(--s2)"/><rect x="94" y="60" width="50" height="34" fill="var(--s2)"/><rect x="154" y="60" width="50" height="34" fill="var(--s2)"/></g>
  <text x="40" y="120" font-family="var(--mono)" font-size="9" fill="var(--muted)">full (3 more X rejected here)</text>
  <rect x="240" y="34" width="200" height="70" fill="none" stroke="var(--acc-line)" stroke-dasharray="4 3"/><text x="250" y="50" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">Y partition (cap 3)</text>
  <g stroke="var(--acc-ink)"><rect x="250" y="60" width="50" height="34" fill="var(--acc-soft)"/><rect x="310" y="60" width="50" height="34" fill="var(--acc-soft)"/><rect x="370" y="60" width="50" height="34" fill="var(--acc-soft)"/></g>
  <text x="255" y="120" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">free — serves all 5 Y</text>
  <text x="30" y="150" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">healthy requests served: 5 of 5</text>
</svg>
^ X's hung requests can fill only X's partition; Y's three workers are mathematically out of X's reach, so every healthy request is served.

## Build

Reproduce the admissions. Pure standard library, deterministic, so 0 of 5 and 5 of 5 come out exactly.

Run `--stream` for the arrivals, `--serve` for the two pools, `--check` for the gate. The self-test pins the isolation claim: the shared pool starves every healthy request, the bulkhead serves every one, the caps use the whole pool, and the partition strictly helps.

```python filename=modules/orchestration-and-governance/code/govern-inter-11/bulkhead.py:117-122 COMPLETE
    sh = serve_shared(arr, w)
    bh = serve_bulkhead(arr, caps)

    shared_starves = y_served(sh) == 0
    print("  the shared pool starves every healthy Y request = %s (%d of %d served)" % (shared_starves, y_served(sh), yt))

    bulkhead_serves_all = y_served(bh) == yt
    print("  bulkheads serve every healthy Y request = %s (%d of %d served)" % (bulkhead_serves_all, y_served(bh), yt))
```

The `caps_sum_to_pool` check — that the bulkhead partitions add up to the whole pool — is the one that keeps the comparison honest. Without it, someone could "win" with bulkheads by secretly giving them more total workers than the shared pool had. Forcing the caps to sum to exactly the six workers the shared pool used proves the bulkhead's advantage comes from *partitioning* the same resource, not from having more of it. Same six workers, arranged two ways, opposite outcomes. Here is the full gate.

```text filename=modules/orchestration-and-governance/code/govern-inter-11/bulkhead.py --check
SELF-TEST — the shared pool starves the healthy dependency; bulkheads keep it served
------------------------------------------------------------------------------------
  the shared pool starves every healthy Y request = True (0 of 5 served)
  bulkheads serve every healthy Y request = True (5 of 5 served)
  the bulkhead caps sum to the whole pool (no workers lost) = True (6 = 6)
  partitioning isolates X's failure from Y = True (5 vs 0 Y served)
------------------------------------------------------------------------------------
SELF-TEST PASS  shared_starves=True  bulkhead_serves_all=True  caps_sum_to_pool=True  isolation=True
```

Four True flags. Shared_starves: the shared pool serves zero healthy requests. Bulkhead_serves_all: the partitioned pool serves every one. Caps_sum_to_pool: it does so with the same six workers, just arranged. Isolation: the partition strictly increases healthy throughput under X's failure. The third flag is the fairness guard — the win is from arrangement, not extra resources.

**The caps-sum-to-pool check forces the two designs to use the same six workers, so the bulkhead's win is proven to come from partitioning the resource, not from having more of it.**

## Definition of done

You are done when you reproduce the 0-versus-5 result and can explain the coupling.

Concretely: `--serve` shows the shared pool serving 0 of 5 healthy requests and the bulkhead serving 5 of 5; `--check` prints PASS with four True flags. You can explain why a hung request is a permanently lost worker and why a shared pool therefore falls entirely to whichever dependency hangs. You can describe the bulkhead as a scoped-admission partition that makes each dependency's availability an independent hard bound. And you can name the cost — lost peak flexibility, a legitimate burst throttled while other partitions sit idle — and say why it is usually worth paying.

The habit to carry: never let one worker or connection pool be shared across dependencies whose failures must not cascade. Give each its own bounded partition, size the partitions by importance, and never give any single dependency the whole pool.

## Boss fight

The instructive failure is a checkout page that goes down because the recommendations service got slow.

An e-commerce service uses one thread pool for all its downstream calls — the payment processor, the inventory service, and a recommendations service that suggests related products. Recommendations is non-critical; if it is slow, the page should just skip the suggestions. But it shares the thread pool, and one day it hangs. Its requests pile up, holding threads, and within a minute every thread in the pool is stuck waiting on recommendations. Now calls to the payment processor and inventory — the things that actually matter — cannot get a thread either. Checkout is down, hard, because a suggestion widget got slow. The postmortem finds no bug in payments or inventory; they were starved by a shared pool. A bulkhead giving recommendations its own small, capped partition would have let it hang harmlessly while checkout kept working.

Your turn, two moves. First, size the partitions under a real trade. Give X a cap of 5 and Y a cap of 1, still summing to 6, and predict what happens when the six-X burst hits: X fills its 5, and Y — with only 1 worker — serves its 5 requests one at a time as its single worker frees, so it still serves all 5 here (since Y releases instantly), but a Y burst would now be throttled hard. Then reverse it, X:1 Y:5, and see X's hung requests capped at a single lost worker. The caps are a policy: how much of the pool are you willing to lose to each dependency's worst day? Second, find the shared pool's exact tipping point. With the shared pool, how many hung X requests does it take to starve Y? Exactly as many as there are workers — six. Predict that five hung X still leaves one worker, so Y is served, and the sixth is the one that tips it to total starvation. That cliff — fine until one more hung request, then everything — is the signature of a shared pool, and the reason isolation should not wait until you are one request from the edge.

## External resources

Michael Nygard's "Release It!" introduces the bulkhead as a stability pattern alongside the circuit breaker; its treatment of pool exhaustion and blast-radius containment is the canonical source.

The Hystrix documentation (Netflix's resilience library) is the classic engineering reference for bulkheads via per-dependency thread pools and semaphore isolation, with exactly the "one slow dependency exhausts the shared pool" motivation this module builds.

For the modern version, service-mesh and gateway docs (Envoy, Istio, resilience4j) all provide per-route concurrency limits and connection-pool isolation; read them for how bulkheads are configured in systems where the pool is a mesh-level resource rather than an in-process thread pool.
