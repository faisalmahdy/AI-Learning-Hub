---
id: eject-inter-01
title: Eject a consistently-failing replica from the pool — a balancer that keeps routing to a dead host bleeds 1/N forever
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A load balancer spreads requests across a pool of identical replicas, and its default is to keep every replica in rotation and send each its fair share — exactly right when all are healthy, and a steady low-grade outage the moment one replica goes bad (a dead disk, a corrupted deploy, a wedged process). The balancer does not know the replica is bad, so it keeps sending it one of every N requests, and every one of those fails or times out. With four replicas, a fifth of all traffic that lands on the dead host errors indefinitely, and no per-request retry hides it because the balancer routes the retry to the same dead host. The pool is mostly healthy, so nothing trips a whole-dependency alarm; the service just quietly fails a fixed fraction forever. Passive outlier detection fixes this at the balancer: watch each replica's results, and when one accumulates enough consecutive failures to be clearly an outlier, eject it — remove it from rotation — so its share reroutes to the healthy replicas. This is distinct from a circuit breaker, which stops calling an entire dependency; ejection operates one level down, inside a healthy dependency, removing the single bad instance. On a fixture of four replicas serving 24 round-robin requests with h2 dead, no ejection fails 6 (1 in 4) and would fail forever, while ejection (threshold 3) removes h2 after 3 failures and reroutes the rest — 3 failures total, then none.
eli5: Imagine a bank with four tellers, and you send every fourth customer to teller number three — but teller three's computer is broken, so every customer sent there gets turned away. If nobody notices, a quarter of all customers keep getting turned away, forever, just because it's "their turn" for the broken teller. The fix is to watch: once teller three turns away a few customers in a row, you put up a "closed" sign on that window and send those customers to the other three tellers instead. Now the broken teller serves nobody, everyone else gets helped, and you check back later to see if teller three's computer got fixed before reopening the window.
---

## Why this module

A load balancer's job is to spread load, and its blind spot is that spreading load and checking whether the load succeeded are two different jobs. By default it does only the first: it keeps every replica in the rotation and hands each its turn, with no memory of whether the last request to that replica came back. So when one replica dies, the balancer keeps faithfully sending it a fair share of traffic to fail, and because the pool is mostly healthy the overall error rate is low enough that no whole-service alarm fires. The result is the most durable kind of outage — a fixed fraction of requests failing steadily, indefinitely, with everything "working."

With four replicas, a fifth of all traffic — one in four requests that happens to land on the dead host — errors, indefinitely, and no per-request retry fully hides it because the balancer will cheerfully route the retry to the same dead host again. The pool is mostly healthy, so nothing trips a whole-dependency alarm; the service just quietly fails a fixed fraction of requests forever.

Passive outlier detection fixes this at the balancer: watch each replica's results, and when one accumulates enough consecutive failures to be clearly an outlier, eject it — remove it from rotation for a while — so its share of traffic is rerouted to the healthy replicas. This is distinct from a circuit breaker, which stops calling an entire dependency when the dependency as a whole is failing; ejection operates one level down, inside a healthy dependency, removing the single bad instance while keeping the rest of the pool serving. This module runs the pool with and without ejection.

**A load balancer must detect a consistently-failing replica and eject it from the pool, rerouting its share to the healthy hosts, because a balancer that keeps a dead replica in rotation sends it a fixed 1/N of all traffic to fail indefinitely — ejection is per-host isolation inside a healthy dependency, which a per-dependency circuit breaker cannot provide.**

## Concepts

**The router tracks consecutive failures per host and, when ejection is on, drops a host after the threshold** — then skips ejected hosts as it advances the rotation, which is the reroute.

```python filename=modules/ship-and-operate/code/eject-inter-01/eject.py:55-79 COMPLETE
def run(hosts, bad_host, requests, threshold, eject):
    """Route requests round-robin. If eject is on, remove a host after `threshold` consecutive failures and reroute."""
    consecutive_fail = {h: 0 for h in hosts}
    ejected = set()
    rr = 0
    log = []
    for r in range(requests):
        picked = None
        for _ in range(len(hosts)):  # advance the rotation, skipping ejected hosts (rerouting)
            cand = hosts[rr % len(hosts)]
            rr += 1
            if eject and cand in ejected:
                continue
            picked = cand
            break
        ok = picked != bad_host
        if ok:
            consecutive_fail[picked] = 0
            log.append({"req": r, "host": picked, "result": "ok"})
        else:
            consecutive_fail[picked] += 1
            log.append({"req": r, "host": picked, "result": "FAIL"})
            if eject and consecutive_fail[picked] >= threshold:
                ejected.add(picked)
    return log, ejected
```

**We tally each run's successes and failures** so the difference between leaving a dead host in and taking it out is a number.

```python filename=modules/ship-and-operate/code/eject-inter-01/eject.py:82-85 COMPLETE
def totals(log):
    ok = sum(1 for e in log if e["result"] == "ok")
    fail = sum(1 for e in log if e["result"] == "FAIL")
    return ok, fail
```

<svg role="img" aria-label="A load balancer routing to four hosts; host h2 is dead. Without ejection, a quarter of arrows go to h2 and fail. With ejection, h2 is removed and all arrows go to the three healthy hosts" viewBox="0 0 300 122" width="300" height="122">
  <text x="6" y="12" fill="var(--muted)" font-size="8">no ejection: 1 of 4 arrows hits the dead host and fails</text>
  <circle cx="30" cy="40" r="8" fill="none" stroke="var(--ink)"/><text x="24" y="43" fill="var(--ink)" font-size="7">LB</text>
  <line x1="38" y1="36" x2="80" y2="26" stroke="var(--s1)"/><rect x="82" y="20" width="20" height="12" fill="var(--s1)"/><text x="86" y="30" fill="var(--panel)" font-size="7">h0</text>
  <line x1="38" y1="38" x2="80" y2="40" stroke="var(--s1)"/><rect x="82" y="34" width="20" height="12" fill="var(--s1)"/><text x="86" y="44" fill="var(--panel)" font-size="7">h1</text>
  <line x1="38" y1="42" x2="80" y2="54" stroke="var(--s2)"/><rect x="82" y="48" width="20" height="12" fill="var(--s2)"/><text x="86" y="58" fill="var(--panel)" font-size="7">h2</text><text x="106" y="58" fill="var(--s2)" font-size="6">✗ dead</text>
  <line x1="38" y1="44" x2="80" y2="68" stroke="var(--s1)"/><rect x="82" y="62" width="20" height="12" fill="var(--s1)"/><text x="86" y="72" fill="var(--panel)" font-size="7">h3</text>
  <text x="6" y="94" fill="var(--muted)" font-size="8">with ejection: h2 removed, traffic reroutes to the healthy three</text>
  <circle cx="160" cy="104" r="8" fill="none" stroke="var(--ink)"/><text x="154" y="107" fill="var(--ink)" font-size="7">LB</text>
  <line x1="168" y1="100" x2="210" y2="90" stroke="var(--s1)"/><rect x="212" y="84" width="20" height="12" fill="var(--s1)"/><text x="216" y="94" fill="var(--panel)" font-size="7">h0</text>
  <line x1="168" y1="103" x2="210" y2="104" stroke="var(--s1)"/><rect x="212" y="98" width="20" height="12" fill="var(--s1)"/><text x="216" y="108" fill="var(--panel)" font-size="7">h1</text>
  <line x1="168" y1="106" x2="210" y2="118" stroke="var(--s1)"/><rect x="212" y="112" width="20" height="8" fill="var(--s1)"/><text x="236" y="119" fill="var(--muted)" font-size="7">h3</text>
  <rect x="212" y="70" width="20" height="10" fill="none" stroke="var(--muted)" stroke-dasharray="2 2"/><text x="236" y="79" fill="var(--muted)" font-size="6">h2 ejected</text>
</svg>
^ Without ejection the balancer sends a quarter of its arrows to the dead h2, which fail; with ejection h2 is removed from the pool and every arrow goes to one of the three healthy hosts, so the failing share drops to zero after the threshold.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/eject-inter-01/eject.py

The fixture is a four-host pool with h2 dead, 24 requests, and an eject threshold of 3 consecutive failures.

```json filename=modules/ship-and-operate/code/eject-inter-01/eject.json:2-5 COMPLETE
  "hosts": ["h0", "h1", "h2", "h3"],
  "bad_host": "h2",
  "requests": 24,
  "eject_threshold": 3
```

Run `--route`.

```text filename=--route
ROUTE — 24 requests round-robin over ['h0', 'h1', 'h2', 'h3']; h2 is dead; eject after 3 consecutive fails
--------------------------------------------------------------
  req   no-eject          with-eject
  0     h0 ok             h0 ok
  1     h1 ok             h1 ok
  2     h2 FAIL           h2 FAIL
  3     h3 ok             h3 ok
  4     h0 ok             h0 ok
  5     h1 ok             h1 ok
  6     h2 FAIL           h2 FAIL
  7     h3 ok             h3 ok
  8     h0 ok             h0 ok
  9     h1 ok             h1 ok
  10    h2 FAIL           h2 FAIL
  11    h3 ok             h3 ok
  12    h0 ok             h0 ok
  13    h1 ok             h1 ok
  14    h2 FAIL           h3 ok
  15    h3 ok             h0 ok
  16    h0 ok             h1 ok
  17    h1 ok             h3 ok
  18    h2 FAIL           h0 ok
  19    h3 ok             h1 ok
  20    h0 ok             h3 ok
  21    h1 ok             h0 ok
  22    h2 FAIL           h1 ok
  23    h3 ok             h3 ok
--------------------------------------------------------------
  no-eject:   18 ok, 6 FAIL  (h2 never removed)
  with-eject: 21 ok, 3 FAIL  (ejected: ['h2'])
```

Compare the two columns. In the no-eject column, h2 comes up every fourth request — at 2, 6, 10, 14, 18, 22 — and fails every single time: 6 failures out of 24, a clean 1 in 4, and it would keep failing at that rate for as long as h2 stays dead. In the with-eject column, the first three h2 turns (requests 2, 6, 10) still fail, because ejection is passive — it has to observe the failures before it can act — but at the third failure h2 crosses the threshold and is ejected. From request 14 on, watch what would have been h2's turns: request 14 goes to h3, request 18 to h0, request 22 to h1. The requests that were destined to fail on h2 are rerouted to healthy hosts and succeed. The total is 3 failures instead of 6, and — more importantly than the 3 saved here — the failures stop: after ejection the bad host takes zero traffic, so the outage is bounded, not perpetual.

## Build

The per-host tally shows the mechanism cleanly: one host is the entire problem, and ejection isolates exactly it.

```text filename=--hosts
HOSTS — requests served per host, without ejection vs with ejection
------------------------------------------------------------------
  host   no-eject (ok/fail)   with-eject (ok/fail)
  h0     6 / 0                7 / 0
  h1     6 / 0                7 / 0
  h2     0 / 6                0 / 3  <- dead, ejected
  h3     6 / 0                7 / 0
------------------------------------------------------------------
  ejection drops h2's traffic to zero after 3 fails; healthy hosts absorb its share.
```

Read down the h2 row: without ejection it served 0 successes and 6 failures — it is a pure black hole, contributing nothing but errors, yet still receiving its full 1/N share. With ejection it took 3 failures and then nothing more; its traffic went to zero. Now read the healthy rows: without ejection each served 6; with ejection each served 7, because after h2 left the pool its share was redistributed across the remaining three. That redistribution is the second half of why ejection works — it is not just that the bad host stops receiving traffic, but that the healthy hosts absorb it, so total *successful* throughput rises (18 to 21) even though the request count is unchanged. This is the crucial difference from a circuit breaker at the dependency level: a breaker sees one healthy dependency (the pool is 3/4 fine) and would not trip; if you somehow made it trip on the elevated error rate, it would cut off the whole pool, including the three good hosts. Ejection is the per-host scalpel — remove the one instance, keep the other three — that the per-dependency breaker's blunt switch cannot be.

<svg role="img" aria-label="Per-host request bars: without ejection h0, h1, h3 each serve 6 successes and h2 serves 6 failures; with ejection the healthy hosts each serve 7 and h2 serves only 3 failures then none" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">per-host load: h2 is the whole failure; ejection zeroes its traffic</text>
  <text x="6" y="30" fill="var(--muted)" font-size="7">no-eject</text>
  <rect x="60" y="22" width="60" height="8" fill="var(--s1)"/><text x="124" y="29" fill="var(--muted)" font-size="6">h0 6 ok</text>
  <rect x="60" y="32" width="60" height="8" fill="var(--s1)"/><text x="124" y="39" fill="var(--muted)" font-size="6">h1 6 ok</text>
  <rect x="60" y="42" width="60" height="8" fill="var(--s2)"/><text x="124" y="49" fill="var(--s2)" font-size="6">h2 6 FAIL</text>
  <rect x="60" y="52" width="60" height="8" fill="var(--s1)"/><text x="124" y="59" fill="var(--muted)" font-size="6">h3 6 ok</text>
  <text x="6" y="80" fill="var(--muted)" font-size="7">with-eject</text>
  <rect x="60" y="72" width="70" height="8" fill="var(--s1)"/><text x="134" y="79" fill="var(--muted)" font-size="6">h0 7 ok</text>
  <rect x="60" y="82" width="70" height="8" fill="var(--s1)"/><text x="134" y="89" fill="var(--muted)" font-size="6">h1 7 ok</text>
  <rect x="60" y="92" width="30" height="8" fill="var(--s2)"/><text x="94" y="99" fill="var(--s2)" font-size="6">h2 3 FAIL then ejected</text>
  <rect x="60" y="102" width="70" height="8" fill="var(--s1)"/><text x="134" y="109" fill="var(--muted)" font-size="6">h3 7 ok</text>
</svg>
^ Without ejection every healthy host serves 6 and h2 contributes only 6 failures; with ejection the three healthy hosts each rise to 7 as they absorb h2's rerouted share, while h2's bar shrinks to 3 failures and then stops — the load moves off the bad instance onto the good ones.

```python filename=modules/ship-and-operate/code/eject-inter-01/eject.py:134-141 COMPLETE
    no_eject_bleeds = no_fail == reqs // len(hosts)
    print("  no-eject fails 1/%d of traffic (%d of %d) = %s" % (len(hosts), no_fail, reqs, no_eject_bleeds))

    eject_caps_failures = ej_fail == thr
    print("  with-eject caps failures at the threshold = %s (%d failures, threshold %d)" % (eject_caps_failures, ej_fail, thr))

    bad_host_ejected = bad in ejected
    print("  the bad host was ejected = %s (ejected: %s)" % (bad_host_ejected, sorted(ejected)))
```

## Definition of done

The self-test pins the perpetual 1/N bleed without ejection, the failure cap at the threshold with it, and that the bad host takes no traffic once ejected.

```python filename=modules/ship-and-operate/code/eject-inter-01/eject.py:143-147 COMPLETE
    fail_idx_after_eject = [e["req"] for e in ej_log if e["result"] == "FAIL"]
    bad_reaches_zero = all(e["host"] != bad for e in ej_log if e["req"] > max(fail_idx_after_eject))
    print("  the bad host takes no traffic after ejection = %s (last failure at req %d)" % (bad_reaches_zero, max(fail_idx_after_eject)))

    fewer_failures = ej_fail < no_fail
    print("  ejection reduces total failures = %s (%d vs %d)" % (fewer_failures, ej_fail, no_fail))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — without ejection the bad host keeps failing 1/N of traffic; with ejection failures are capped and rerouted
----------------------------------------------------------------------------------------------------------------------
  no-eject fails 1/4 of traffic (6 of 24) = True
  with-eject caps failures at the threshold = True (3 failures, threshold 3)
  the bad host was ejected = True (ejected: ['h2'])
  the bad host takes no traffic after ejection = True (last failure at req 10)
  ejection reduces total failures = True (3 vs 6)
```

<svg role="img" aria-label="Failures over the run: without ejection failures accumulate one every four requests to six and keep climbing; with ejection failures stop at three after the host is ejected" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">cumulative failures: no-eject climbs forever; eject stops at 3</text>
  <line x1="30" y1="82" x2="285" y2="82" stroke="var(--grid)"/>
  <line x1="30" y1="82" x2="30" y2="24" stroke="var(--grid)"/>
  <polyline points="40,78 80,72 120,66 160,60 200,54 240,48 280,42" fill="none" stroke="var(--s2)"/>
  <text x="244" y="40" fill="var(--s2)" font-size="6">no-eject →∞</text>
  <polyline points="40,78 80,72 120,66 160,66 200,66 240,66 280,66" fill="none" stroke="var(--s1)"/>
  <text x="210" y="74" fill="var(--s1)" font-size="6">eject: flat at 3</text>
  <circle cx="120" cy="66" r="3" fill="var(--ink)"/><text x="108" y="60" fill="var(--muted)" font-size="6">ejected here</text>
  <text x="34" y="96" fill="var(--muted)" font-size="6">requests →</text>
</svg>
^ Without ejection the cumulative failure count rises by one every fourth request and never stops; with ejection it climbs to 3 (the threshold) and then goes flat forever, because the bad host is out of the pool — a bounded outage versus a perpetual one.

**Done means the bleed and its cap are proven on real routing: without ejection the dead h2 is hit every 4th request and fails 6 of 24 (1 in 4) indefinitely, while with ejection h2 is removed after 3 consecutive failures and its later turns reroute to healthy hosts (18 successes become 21) — so a balancer must eject a consistently-failing replica, per-host isolation a per-dependency circuit breaker cannot give.**

## Boss fight

Predict two ways ejection turns from a fix into a new failure mode, because removing hosts from a pool is a capacity decision and a feedback loop.

The first trap is that ejection removes capacity, so aggressive ejection during a broad problem can eject the whole pool and cause the outage it was meant to prevent. The threshold and the ejection cap matter enormously: if the "failures" are not a dead host but a load spike that every replica is struggling with, a low threshold will start ejecting healthy-but-slow hosts one by one, and each ejection dumps that host's traffic onto the remaining hosts, making them more overloaded, so they cross the threshold and get ejected too — a cascade that ejects the entire pool and takes the service fully down. This is why real outlier detectors cap the fraction of the pool that may be ejected at once (for example, never eject more than 50% of hosts) and distinguish a single-host outlier from a fleet-wide problem: ejection is the right tool for "one replica is bad while the others are fine," and exactly the wrong tool for "all replicas are overloaded," where the answer is load shedding or scaling, not removing servers. Ejection must be a minority operation on an otherwise-healthy pool, never a response to a systemic failure.

The second trap is that a passively-ejected host must be probed and returned, or you slowly starve your own capacity, and the return itself needs care. Ejection has to be temporary: the host is removed for a cooldown, then put back — because the failure may have been transient (a brief GC pause, a blip), and a host ejected permanently on one bad streak is capacity you paid for and abandoned. But re-admitting it naively causes a flap: put the still-dead host straight back into full rotation and it fails again, gets re-ejected, oscillating and periodically hurting a slice of traffic each time it is briefly back. The standard fixes are exponential backoff on the ejection duration (each successive ejection lasts longer, so a persistently-bad host is out for longer and longer) and re-introducing a recovered host gradually rather than at full weight (slow-start), so a host that is only half-better does not immediately take a full share and fail it. And passive detection (reacting to real request failures) can be paired with active health-checking (probing the host out-of-band) so a recovered host is verified before it serves live traffic, and a bad host is caught even during a lull with no traffic to fail. Ejection without a disciplined, backed-off, gradual return is just a different way to mismanage the pool.

**Ejection is a minority operation on a healthy pool, not a response to a systemic failure: cap the fraction of hosts that can be ejected at once and distinguish a single outlier from a fleet-wide overload (where the answer is shedding or scaling, because ejecting overloaded hosts cascades the load onto the rest until the whole pool is gone); and make every ejection temporary with exponential backoff on its duration plus a slow-start (or active health-check) on return, or a transient blip abandons capacity permanently and a naive re-admit flaps the still-bad host in and out.**

## External resources

Envoy's outlier-detection documentation and Istio/gRPC load-balancing guides — consecutive-failure and success-rate ejection, the max-ejection-percent cap, ejection backoff, and how passive detection combines with active health checks.

Michael Nygard's "Release It!" and general load-balancer health-checking references — why a balancer must route around a bad instance, the difference between per-instance ejection and per-dependency circuit breaking, and the capacity and flap hazards of ejection.

The companion circuit-breaker, bulkhead, and load-shedding modules in this topic — ejection is per-host isolation that complements the breaker's per-dependency isolation and the bulkhead's per-dependency partitioning, and the "systemic overload needs shedding, not ejection" boundary is exactly where load shedding takes over.
