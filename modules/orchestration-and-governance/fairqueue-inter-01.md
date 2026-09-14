---
id: fairqueue-inter-01
title: Schedule a shared server with fair queuing, not one shared FIFO — a tenant that floods the queue monopolizes the capacity and starves the rest
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A single FIFO queue has exactly one notion of fairness — first come, first served — which sounds fair and is not when the server is shared across tenants, because it ties a tenant's share of the service to how many requests it submitted. A tenant that sends a burst lands its requests at the front, gets served in bulk, and pushes every other tenant's requests back; if capacity is exhausted before those are reached, they are not just delayed but starved. One heavy user shuts out everyone else on the shared resource — the noisy-neighbor problem — and FIFO has no defense. Fair queuing breaks the link between how much you submit and how much you are served: keep a separate queue per tenant and serve them round-robin, one request from each per cycle, skipping empty queues, so each active tenant gets an equal share of capacity regardless of how many requests it enqueued, and a burst piles up in its own queue without crowding out the others. Because the scheme is work-conserving, capacity a light tenant does not use flows to the tenants that need it, so fair queuing guarantees each tenant a floor share (max-min fairness) rather than a rigid equal cut. On a fixture where tenant A bursts 6 requests ahead of B's 2 and C's 1, a FIFO server with capacity 6 serves all 6 of A's and starves B and C completely, while fair queuing serves 3 of A's, both of B's, and C's one — every tenant served, each guaranteed its floor share of 2.
eli5: Imagine one line at a coffee shop and a tour group of six people rushes in ahead of you and one other person. With a single line, the barista just serves whoever is next, so all six of the group get their drinks before the two of you get anything — and if the barista's shift ends, you never get served at all. The fix is to give each separate party its own little line and have the barista take one order from each party in turn: the group's line, your line, the other person's line, round and round. Now you get your coffee quickly even though the group is huge, because the barista only takes one of theirs before coming back to you. Turning the crowd into one big line rewards whoever shoved in first and most; taking turns by party gives everyone a fair share.
---

## Why this module

A shared service — a queue of jobs, an API, a worker pool — receives work from many clients, and the simplest way to decide what to run next is a single queue in arrival order. FIFO is the default because it feels obviously fair: nobody jumps ahead, everyone waits their turn, first come first served. For a single client that is fine.

Across many clients it is not fair at all, because FIFO measures "turn" in requests, not in clients. A client that submits one request and a client that submits a hundred are treated identically per request, which means the hundred-request client gets a hundred times the service. Fairness per request is unfairness per client, and the gap is entirely under the clients' control — anyone can take a bigger share just by sending more.

The sharp edge is capacity. When the server can only handle so much work in a window, a client that bursts a large batch to the front of the queue does not merely get served first — it consumes the capacity, and the requests behind it, from other clients, are never reached. Those clients are starved: not slow, but shut out, by a neighbor doing nothing more than being greedy. This is the noisy-neighbor failure, and a single FIFO invites it.

**A shared FIFO serves in arrival order, so a client's share of service is proportional to how many requests it submits — a client that floods the queue monopolizes the capacity and starves the others, and FIFO's per-request fairness offers no protection.**

## Concepts

Fair queuing changes what a "turn" means: a turn belongs to a tenant, not to a request. Instead of one shared line, give each tenant its own queue, and have the scheduler visit the queues in rotation, taking one request from each non-empty queue per cycle. A tenant's burst now piles up inside that tenant's own queue, where it waits its owner's turns — it cannot push into anyone else's line.

<svg role="img" aria-label="Left: one shared FIFO queue with six A requests at the front, then B, B, C, and a capacity cut after the sixth request, so only A requests are served and B and C are past the cut. Right: three per-tenant queues (A with six, B with two, C with one) feeding a round-robin scheduler that takes one from each in turn." viewBox="0 0 440 160">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">shared FIFO</text>
<rect x="30" y="30" width="16" height="16" fill="var(--s2)"/><rect x="48" y="30" width="16" height="16" fill="var(--s2)"/><rect x="66" y="30" width="16" height="16" fill="var(--s2)"/><rect x="84" y="30" width="16" height="16" fill="var(--s2)"/><rect x="102" y="30" width="16" height="16" fill="var(--s2)"/><rect x="120" y="30" width="16" height="16" fill="var(--s2)"/>
<rect x="140" y="30" width="16" height="16" fill="var(--s1)"/><rect x="158" y="30" width="16" height="16" fill="var(--s1)"/><rect x="176" y="30" width="16" height="16" fill="var(--muted)"/>
<line x1="138" y1="24" x2="138" y2="52" stroke="var(--ink)"/>
<text x="138" y="64" fill="var(--ink)" font-size="7" text-anchor="middle">capacity cut</text>
<text x="80" y="82" fill="var(--s2)" font-size="7" text-anchor="middle">6 A served</text>
<text x="168" y="82" fill="var(--muted)" font-size="7" text-anchor="middle">B,C starved</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">fair queuing</text>
<text x="270" y="42" fill="var(--s2)" font-size="8">A</text><rect x="282" y="32" width="80" height="12" fill="var(--s2)"/>
<text x="270" y="62" fill="var(--s1)" font-size="8">B</text><rect x="282" y="52" width="28" height="12" fill="var(--s1)"/>
<text x="270" y="82" fill="var(--muted)" font-size="8">C</text><rect x="282" y="72" width="14" height="12" fill="var(--muted)"/>
<circle cx="390" cy="58" r="14" fill="var(--panel)" stroke="var(--line)"/>
<text x="390" y="61" fill="var(--ink)" font-size="7" text-anchor="middle">RR</text>
<text x="330" y="104" fill="var(--muted)" font-size="7" text-anchor="middle">one from each queue per cycle</text>
</svg>
^ A shared FIFO puts A's burst ahead of everyone and the capacity cut starves B and C; per-tenant queues with a round-robin scheduler take one from each, so the burst waits in A's own queue.

The result is that capacity is divided by tenant, not by volume. Each active tenant gets a turn every cycle, so a tenant that submitted one request and a tenant that submitted a thousand are both served one-per-round — the light tenants get through promptly, and the heavy tenant is metered out at its fair rate instead of dumping all at once. Its total work still gets done eventually; it just cannot seize the whole server to do it now.

Fair queuing is also work-conserving, which sharpens the fairness into a precise guarantee. The scheduler skips empty queues, so capacity a light tenant does not use is not wasted — it flows to the tenants that still have work. This means fair queuing does not impose a rigid equal cut; it guarantees each tenant a floor share (its equal slice, or all its requests if fewer), and hands any surplus to whoever can use it. That is max-min fairness: raise the smallest allocations as high as possible before giving more to the already-large.

<svg role="img" aria-label="A round-robin cycle diagram. Cycle 1 serves A, B, C. Cycle 2 serves A, B (C empty). Cycle 3 serves A (B and C empty). The greedy tenant A gets the leftover turns after the light tenants are satisfied." viewBox="0 0 440 130">
<text x="20" y="18" fill="var(--muted)" font-size="9">round-robin cycles (capacity 6)</text>
<text x="30" y="45" fill="var(--ink)" font-size="8">cycle 1</text>
<rect x="80" y="34" width="26" height="16" fill="var(--s2)"/><text x="93" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">A</text>
<rect x="110" y="34" width="26" height="16" fill="var(--s1)"/><text x="123" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">B</text>
<rect x="140" y="34" width="26" height="16" fill="var(--muted)"/><text x="153" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">C</text>
<text x="30" y="73" fill="var(--ink)" font-size="8">cycle 2</text>
<rect x="80" y="62" width="26" height="16" fill="var(--s2)"/><text x="93" y="74" fill="var(--ink)" font-size="8" text-anchor="middle">A</text>
<rect x="110" y="62" width="26" height="16" fill="var(--s1)"/><text x="123" y="74" fill="var(--ink)" font-size="8" text-anchor="middle">B</text>
<text x="175" y="74" fill="var(--muted)" font-size="7">C empty</text>
<text x="30" y="101" fill="var(--ink)" font-size="8">cycle 3</text>
<rect x="80" y="90" width="26" height="16" fill="var(--s2)"/><text x="93" y="102" fill="var(--ink)" font-size="8" text-anchor="middle">A</text>
<text x="145" y="102" fill="var(--muted)" font-size="7">B, C empty — A takes the surplus</text>
</svg>
^ Round-robin skips empty queues, so after B and C are satisfied their unused turns flow to A — max-min fairness: each tenant's floor first, surplus to whoever can use it.

**Fair queuing gives each tenant its own queue served round-robin, so a turn belongs to a tenant not a request, and because it skips empty queues it is work-conserving — guaranteeing each tenant a floor share (max-min fairness) rather than letting volume decide.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/fairqueue-inter-01. The fixture is a server capacity and a FIFO-ordered arrival sequence where tenant A bursts ahead of B and C.

```json filename=modules/orchestration-and-governance/code/fairqueue-inter-01/fairqueue.json:3-4 COMPLETE
  "capacity": 6,
  "arrivals": ["A", "A", "A", "A", "A", "A", "B", "B", "C"]
```

The pending count per tenant is what each submitted.

```python filename=modules/orchestration-and-governance/code/fairqueue-inter-01/fairqueue.py:31-36 COMPLETE
def pending(arrivals):
    """Requests waiting, per tenant, in first-appearance order."""
    counts = OrderedDict()
    for t in arrivals:
        counts[t] = counts.get(t, 0) + 1
    return counts
```

FIFO service is simply the first `capacity` arrivals in order.

```python filename=modules/orchestration-and-governance/code/fairqueue-inter-01/fairqueue.py:39-44 COMPLETE
def fifo_serve(arrivals, capacity):
    """One shared FIFO: serve the first `capacity` arrivals in order."""
    served = OrderedDict((t, 0) for t in pending(arrivals))
    for t in arrivals[:capacity]:
        served[t] += 1
    return served
```

Fair service cycles through the tenants, taking one from each non-empty queue until capacity is spent.

```python filename=modules/orchestration-and-governance/code/fairqueue-inter-01/fairqueue.py:47-58 COMPLETE
def fair_serve(arrivals, capacity):
    """Fair queuing: one queue per tenant, served round-robin one each per cycle."""
    remaining = pending(arrivals)
    served = OrderedDict((t, 0) for t in remaining)
    total = 0
    while total < capacity and any(remaining[t] > 0 for t in remaining):
        for t in remaining:
            if remaining[t] > 0 and total < capacity:
                served[t] += 1
                remaining[t] -= 1
                total += 1
    return served
```

Before running it, predict: A's six requests are all at the front, and capacity is six, so FIFO will serve only A and leave nothing for B or C. Run `--fifo`:

```text filename=fairqueue.py --fifo
FIFO — one shared queue, capacity 6, served in arrival order
----------------------------------------------------
  pending  : {'A': 6, 'B': 2, 'C': 1}
  served   : {'A': 6, 'B': 0, 'C': 0}
  starved  : ['B', 'C']
----------------------------------------------------
  the flooding tenant takes the capacity; the rest are starved
```

The prediction holds, in its worst form. A submitted six, all ahead of the others, and consumed the entire capacity of six — B and C received zero. Two of the three tenants are starved outright, not delayed: the server did a full window of work and served exactly one tenant, the one that flooded. Nothing here is broken; this is FIFO working as designed, which is the problem.

Now fair queuing on the identical arrivals. Run `--fair`:

```text filename=fairqueue.py --fair
FAIR — one queue per tenant, capacity 6, served round-robin
----------------------------------------------------
  pending  : {'A': 6, 'B': 2, 'C': 1}
  served   : {'A': 3, 'B': 2, 'C': 1}
  starved  : []
----------------------------------------------------
  every tenant gets a turn each cycle; the burst fills only its own queue
```

Same six requests served, but shared: A gets 3, B gets 2, C gets 1, and nobody is starved. Notice the max-min shape — the equal floor share is 2 (six slots, three tenants), and B and C ask for at most that, so they are fully served; A, the heavy tenant, gets its floor of 2 plus the one surplus slot C did not use, landing at 3. Fair queuing did not throttle A to a rigid 2; it satisfied the light tenants first and let A have what was left over, which is exactly the work-conserving guarantee.

<svg role="img" aria-label="Two grouped bar charts of requests served per tenant. Under FIFO, A is 6, B is 0, C is 0. Under fair queuing, A is 3, B is 2, C is 1. FIFO starves B and C; fair serves all three." viewBox="0 0 440 150">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">FIFO served</text>
<line x1="40" y1="115" x2="200" y2="115" stroke="var(--line)"/>
<rect x="55" y="35" width="26" height="80" fill="var(--s2)"/><text x="68" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">A 6</text>
<text x="118" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">B 0</text>
<text x="168" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">C 0</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">fair served</text>
<line x1="255" y1="115" x2="415" y2="115" stroke="var(--line)"/>
<rect x="268" y="75" width="26" height="40" fill="var(--s2)"/><text x="281" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">A 3</text>
<rect x="308" y="88" width="26" height="27" fill="var(--s1)"/><text x="321" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">B 2</text>
<rect x="348" y="102" width="26" height="13" fill="var(--muted)"/><text x="361" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">C 1</text>
</svg>
^ FIFO gives the flooding tenant all six and starves B and C; fair queuing serves 3/2/1 — everyone served, each at least its floor share.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that FIFO's top tenant takes more than fair's does, that FIFO starves at least one tenant, that fair queuing serves every tenant, that fair queuing guarantees each tenant its floor share, and that both schemes serve the same total.

```python filename=modules/orchestration-and-governance/code/fairqueue-inter-01/fairqueue.py:104-119 COMPLETE
    fifo_lets_one_dominate = fifo_max > fair_max
    print("  FIFO's top tenant takes more than fair's does = %s (%d > %d)" % (fifo_lets_one_dominate, fifo_max, fair_max))

    fifo_starves_someone = len(starved(fifo)) > 0
    print("  FIFO starves at least one tenant that had requests = %s (%s)" % (fifo_starves_someone, starved(fifo)))

    fair_serves_everyone = len(starved(fair)) == 0
    print("  fair queuing serves every tenant that had requests = %s" % fair_serves_everyone)

    pend = pending(arrivals)
    floor_share = cap // n_tenants
    fair_guarantees_floor_share = all(fair[t] >= min(pend[t], floor_share) for t in fair)
    print("  fair queuing guarantees each tenant its floor share (max-min) = %s (floor %d)" % (fair_guarantees_floor_share, floor_share))

    same_total_served = sum(fifo.values()) == sum(fair.values()) == cap
    print("  both schemes serve the same total = %s (%d)" % (same_total_served, sum(fair.values())))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if FIFO ever stopped starving anyone or fair queuing ever dropped a tenant below its floor:

```text filename=fairqueue.py --check
SELF-TEST — FIFO lets the flooding tenant monopolize and starves the others; fair queuing serves every tenant and guarantees each its floor share
----------------------------------------------------------------------------------------------------------------
  FIFO's top tenant takes more than fair's does = True (6 > 3)
  FIFO starves at least one tenant that had requests = True (['B', 'C'])
  fair queuing serves every tenant that had requests = True
  fair queuing guarantees each tenant its floor share (max-min) = True (floor 2)
  both schemes serve the same total = True (6)
```

**The self-test checks the floor-share guarantee, not a rigid equal split — so a pass certifies fair queuing protects every tenant's minimum while still letting the greedy tenant use surplus capacity, which is the actual promise of max-min fairness rather than a blunt equal cap.**

## Definition of done

You can explain why FIFO's per-request fairness becomes per-client unfairness on a shared server.
You can explain why capacity makes the failure starvation, not just delay, and name it as the noisy-neighbor problem.
You can describe fair queuing — per-tenant queues, round-robin service — and why a burst then fills only its own queue.
You can explain why work-conserving round-robin yields max-min fairness (a floor share plus surplus to who needs it), not a rigid equal split.
You can state how weighting the round-robin turns generalizes fair queuing to unequal shares.

## Boss fight

Suppose requests are not all the same size — some tenants send cheap requests and one sends expensive ones. Reason about whether round-robin is still fair. It is not, because round-robin counts requests, and a tenant whose requests each cost ten times as much gets ten times the actual resource per turn, so counting turns is the wrong currency once request cost varies. The fix is to schedule by cost, not count: deficit round-robin and weighted fair queuing track each tenant's accumulated service in work units (CPU time, bytes, tokens) and serve whoever is furthest below its fair share of that work, which restores fairness in the resource that actually matters. The lesson generalizes the module: fairness must be measured in the scarce resource, and when requests are uniform that is just their count, but when they are not, you must weight by cost.

Now the trap that makes fair queuing quietly fail: how you identify a tenant. Fair queuing protects tenants only if the scheduler can tell them apart, so if the tenant key is something a client controls and can multiply — a per-connection queue when one client opens a thousand connections, or a per-request-id queue — then the greedy client simply spawns many identities and gets many queues, and you are back to volume winning. The key must be a real, hard-to-forge principal (an authenticated account, an API key, a billing id), and the mapping from request to principal must be enforced server-side. Fair queuing is only as fair as its notion of who a tenant is, so the identity boundary is part of the design, not an afterthought.

**Round-robin is fair only when requests cost the same; when they differ, schedule by accumulated work (deficit round-robin, weighted fair queuing) in the scarce resource — and fair queuing protects tenants only if the tenant key is a hard-to-forge authenticated principal, or a client wins back its advantage by spawning many identities.**

## External resources

The networking literature on fair queuing — Demers, Keshav, and Shenker's weighted fair queuing, and deficit round robin (Shreedhar and Varghese) — develops the per-flow queue and the cost-weighted generalization.
Guides on multi-tenant system design and API rate limiting discuss per-tenant queues, quotas, and the noisy-neighbor problem, and how fairness interacts with the tenant-identity boundary.
The topic's own modules on head-of-line blocking, bulkheads, and priority aging cover neighboring scheduling failures — a slow task blocking a lane, a dependency starving a pool, and strict priority starving low-priority work — that fair queuing is distinct from.
