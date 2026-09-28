---
id: retryamp-inter-01
title: Retries at every layer multiply — one request becomes attempts^depth at the bottom, a storm exactly during an incident
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A retry is a good idea in isolation, but a modern request passes through a stack of services — frontend calls api calls storage calls disk — and each layer sensibly retries on a failure from the layer below, and those retries compound. When the api retries storage 3 times, storage retries disk 3 times, and the frontend retries the api 3 times, one top-level request becomes 3×3×3 = 27 requests at the disk, because each retry at a layer re-drives the entire subtree beneath it: the amplification is the product of the per-layer retry counts and grows exponentially with the depth of the chain. The danger is the timing — retries fire precisely when something is failing, which is precisely when the failing layer can least afford extra load — so a briefly slow disk gets hit with many times its normal traffic, fails more, and the retries multiply further into a retry storm (a metastable failure) that keeps the system down after the trigger is gone. The fixes attack the multiplication: retry at only one layer (linear, not a product), impose a retry budget (retries capped to a small fraction of requests), and propagate a deadline. On a fixture chain of frontend→api→storage→disk with each of the three upper layers retrying 3 times, load grows 1→3→9→27 down the chain (amplification ×27), while retrying at only the edge makes it 3 and not retrying at all makes it 1.
eli5: Imagine you ask a friend to fetch something, and if they fail you ask them to try three times. Fine. But your friend, to do it, asks their friend, who tries three times each go; and that friend asks another friend, who also tries three times. Suddenly one favor from you turns into twenty-seven trips for the person at the bottom of the chain — and this all happens right when that person is already struggling, which is why they were failing in the first place. Piling on more tries makes the jam worse. The fix is to let only one person in the chain retry, and to set a total time limit so nobody keeps trying after it's clearly hopeless.
---

## Why this module

Every service adds a retry because retries make that service more reliable in a demo. Stacked across a real call chain, those same retries turn a small downstream hiccup into a self-sustaining flood — and the flood is largest at exactly the service that was already in trouble, which is how a brief blip becomes an outage that will not end on its own.

A retry is a good idea in isolation: a request fails transiently, you try again, it succeeds. The trouble is that a modern request passes through a stack of services — a frontend calls an api, which calls storage, which calls a disk layer — and each of them, sensibly, retries on a failure from the layer below. Those retries compound. When the api retries its call to storage 3 times, and storage retries its call to disk 3 times, and the frontend retries the api 3 times, a single top-level request can become 3 × 3 × 3 = 27 requests at the disk, because each retry at a layer re-drives the entire subtree beneath it. The amplification is the product of the per-layer retry counts, and it grows exponentially with the depth of the call chain.

The reason this is dangerous, and not just wasteful, is the timing: retries fire precisely when something is failing, which is precisely when the failing layer can least afford extra load. A disk layer that is briefly slow returns some errors; every layer above dutifully retries; the disk is now hit with many times its normal traffic while it is already struggling; it fails more; the retries multiply further. This is a retry storm, a metastable failure that can keep a service down long after the original trigger is gone, because the retries themselves have become the load. The fixes all attack the multiplication — retry at only one layer, impose a retry budget, propagate a deadline. This module computes the amplification down a chain and the budgeted alternatives.

**Retries at every layer of a call chain multiply into the product of the per-layer counts, so one request becomes attempts^depth at the bottom — a retry storm that peaks exactly when the failing downstream can least afford it — and the fix is to cap the multiplication with single-layer retries, retry budgets, and propagated deadlines.**

## Concepts

**The inbound load** at each layer is the running product of the retry counts above it: the top gets 1 request, and each layer multiplies what it received by its own retry count before passing it down.

```python filename=modules/ship-and-operate/code/retryamp-inter-01/retryamp.py:48-53 COMPLETE
def inbound_per_layer(attempts):
    """Requests reaching each layer for one top-level request: the running product of the attempts above it (top = 1)."""
    load = [1]
    for a in attempts:
        load.append(load[-1] * a)
    return load
```

**The amplification** is the load at the very bottom — the product of every layer's retry count. It is exponential in the depth, so a modest per-layer retry count becomes an enormous factor over a few layers.

```python filename=modules/ship-and-operate/code/retryamp-inter-01/retryamp.py:56-58 COMPLETE
def amplification(attempts):
    """Total requests reaching the bottom layer per top-level request: the product of every layer's retry count."""
    return prod(attempts)
```

<svg role="img" aria-label="A tree of retries: one frontend request fans out to 3 api calls, 9 storage calls, and 27 disk calls, showing the load tripling at each layer" viewBox="0 0 300 132" width="300" height="132">
  <text x="6" y="12" fill="var(--muted)" font-size="8">each layer triples the load it received: 1 → 3 → 9 → 27</text>
  <text x="240" y="34" fill="var(--muted)" font-size="7">frontend: 1</text>
  <circle cx="150" cy="30" r="4" fill="var(--s1)"/>
  <text x="248" y="60" fill="var(--muted)" font-size="7">api: 3</text>
  <circle cx="90" cy="56" r="4" fill="var(--s1)"/><circle cx="150" cy="56" r="4" fill="var(--s1)"/><circle cx="210" cy="56" r="4" fill="var(--s1)"/>
  <text x="252" y="86" fill="var(--muted)" font-size="7">storage: 9</text>
  <g fill="var(--s2)">
  <circle cx="70" cy="84" r="3"/><circle cx="90" cy="84" r="3"/><circle cx="110" cy="84" r="3"/>
  <circle cx="130" cy="84" r="3"/><circle cx="150" cy="84" r="3"/><circle cx="170" cy="84" r="3"/>
  <circle cx="190" cy="84" r="3"/><circle cx="210" cy="84" r="3"/><circle cx="230" cy="84" r="3"/>
  </g>
  <text x="252" y="116" fill="var(--muted)" font-size="7">disk: 27</text>
  <rect x="30" y="108" width="215" height="8" fill="var(--muted)"/>
  <line x1="150" y1="34" x2="90" y2="52" stroke="var(--line)"/><line x1="150" y1="34" x2="150" y2="52" stroke="var(--line)"/><line x1="150" y1="34" x2="210" y2="52" stroke="var(--line)"/>
</svg>
^ One frontend request becomes 3 api calls, each of those 3 storage calls (9), each of those 3 disk calls (27) — the load triples at every layer, so the bottom sees the product of the retry counts.

**The load at the bottom of a call chain is the product of the per-layer retry counts, so retrying independently at each of D layers turns one request into attempts^D — exponential in the depth, not the sum.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/retryamp-inter-01/retryamp.py

The fixture is a four-layer chain where each of the three upper layers retries its downstream call 3 times.

```json filename=modules/ship-and-operate/code/retryamp-inter-01/retryamp.json:3-4 COMPLETE
  "layers": ["frontend", "api", "storage", "disk"],
  "attempts": [3, 3, 3]
```

Run `--amplify` to trace the load down the chain.

```text filename=--amplify
AMPLIFY — load reaching each layer, per-layer retry (attempts=[3, 3, 3])
------------------------------------------------------------
  layer        retries downstream   requests reaching it
  frontend     3                    1
  api          3                    3
  storage      3                    9
  disk         -                    27
```

Follow the last column down: the frontend handles 1 request, retries the api up to 3 times so the api sees 3, the api retries storage 3 times per call so storage sees 9, and storage retries the disk 3 times per call so the disk sees 27. A single user request has become 27 requests at the bottom — a 27× amplification from three layers of a 3× retry. The numbers are small here to fit, but the shape is the point: this is exponential in depth, so a five-layer chain at 3× is 3^5 = 243×, and a chain where a couple of layers retry 4 or 5 times is worse still. And every one of those 27 disk requests happens because the disk was returning errors — the retries are not spread over calm periods, they are concentrated exactly on the failing component. The layer that triggered the retries is the layer that gets buried by them.

## Build

Where you allow retries decides whether the factor is a product or a single number. Run `--budget`.

```text filename=--budget
BUDGET — where you allow retries decides the multiplier
----------------------------------------------------------
  per-layer retry (all 3): attempts=[3, 3, 3] -> bottom load 27
  edge-only retry        : attempts=[3, 1, 1] -> bottom load 3
  no retry (baseline)    : attempts=[1, 1, 1] -> bottom load 1
```

The same chain, three retry policies. Retrying at every layer gives the product, 27. Retrying at only the edge — the frontend retries 3 times, but the api and storage each make a single attempt and propagate the failure up — gives 3, because there is no multiplication: one layer's retries times ones is just that layer's count. No retries anywhere gives 1. The edge-only policy still gets most of the benefit of retrying (a transient failure anywhere in the chain is retried by the frontend, re-driving the whole request) while capping the load amplification at a linear factor instead of an exponential one. This is the core discipline: decide, deliberately, at which single layer retries live, and make every other layer fail fast and propagate. The alternative fixes — a retry budget that caps retries at a fraction of traffic, and deadline propagation that refuses a retry once the time budget is spent — do the same job by bounding the total rather than the location.

```python filename=modules/ship-and-operate/code/retryamp-inter-01/retryamp.py:61-63 COMPLETE
def edge_only(attempts):
    """Retry only at the edge (top) layer; every layer below does a single attempt."""
    return [attempts[0]] + [1] * (len(attempts) - 1)
```

<svg role="img" aria-label="Bottom-layer load under three policies: per-layer retry 27, edge-only 3, no retry 1" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">bottom-layer load: 27 (all layers) vs 3 (edge) vs 1 (none)</text>
  <line x1="40" y1="92" x2="290" y2="92" stroke="var(--line)"/>
  <g transform="translate(60,0)">
  <rect x="0" y="20" width="44" height="72" fill="var(--s2)"/><text x="6" y="104" fill="var(--muted)" font-size="7">per-layer</text><text x="14" y="16" fill="var(--muted)" font-size="7">27</text>
  </g>
  <g transform="translate(150,0)">
  <rect x="0" y="84" width="44" height="8" fill="var(--s1)"/><text x="6" y="104" fill="var(--muted)" font-size="7">edge-only</text><text x="18" y="80" fill="var(--muted)" font-size="7">3</text>
  </g>
  <g transform="translate(240,0)">
  <rect x="0" y="89" width="44" height="3" fill="var(--muted)"/><text x="6" y="104" fill="var(--muted)" font-size="7">no retry</text><text x="18" y="85" fill="var(--muted)" font-size="7">1</text>
  </g>
</svg>
^ Retrying at every layer drives the bottom to 27× load; retrying at only the edge caps it at 3× (linear in that one layer's attempts); not retrying is the 1× baseline — the policy, not the chain, sets the multiplier.

## Definition of done

The self-test pins the product law, the explosion, the linear edge-only factor, and the baseline.

```python filename=modules/ship-and-operate/code/retryamp-inter-01/retryamp.py:103-111 COMPLETE
    load = inbound_per_layer(attempts)
    amp_is_product = load[-1] == prod(attempts)
    print("  the bottom-layer load equals the product of attempts = %s (%d == %s)" % (amp_is_product, load[-1], "*".join(map(str, attempts))))

    deep_explodes = amplification(attempts) >= 27
    print("  three layers each retrying 3x reach 27x load = %s (%d)" % (deep_explodes, amplification(attempts)))

    edge_linear = amplification(edge_only(attempts)) == attempts[0]
    print("  retrying only at the edge is linear in its attempts = %s (%d)" % (edge_linear, amplification(edge_only(attempts))))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the amplification is the product of per-layer attempts; deep per-layer retry explodes; edge-only is linear
--------------------------------------------------------------------------------------------------------------------------
  the bottom-layer load equals the product of attempts = True (27 == 3*3*3)
  three layers each retrying 3x reach 27x load = True (27)
  retrying only at the edge is linear in its attempts = True (3)
  no retries anywhere is 1x load = True
  edge-only load is far below per-layer load = True (3 < 27)
```

**Done means the multiplication and its cure are proven on real load figures: per-layer retry drives the bottom to the product of the attempts (27 = 3×3×3), retrying at only the edge is linear in that layer's attempts (3), no retries is the 1× baseline, and edge-only load is far below per-layer load — so the amplification is a property of where retries live, and bounding it is a design choice, not luck.**

## Boss fight

Predict two ways this is worse and subtler than the clean product suggests, because the real dynamics are a feedback loop and the fixes interact.

The first trap is that the static product is the *floor*, and the real behavior during an incident is a feedback loop that can be far worse and self-sustaining. The 27× assumes each retry is independent, but retries fire on failures, failures rise with load, and load rises with retries — so once a downstream tips into overload, retries add load, which causes more failures, which triggers more retries. This is a metastable failure: the system has two stable states, healthy and collapsed, and a brief trigger can push it into the collapsed state where the retry load alone keeps it there even after the original cause is gone. That is why you cannot fix a retry storm by waiting; you often have to shed load or turn retries off to let the downstream recover.

<svg role="img" aria-label="A feedback loop of four nodes: more load causes more failures, which cause more retries, which cause more load, a self-sustaining cycle" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the retry storm is a loop that feeds itself</text>
  <rect x="110" y="20" width="80" height="18" fill="none" stroke="var(--s2)"/><text x="126" y="32" fill="var(--muted)" font-size="7">more load</text>
  <rect x="210" y="52" width="80" height="18" fill="none" stroke="var(--line)"/><text x="220" y="64" fill="var(--muted)" font-size="7">more failures</text>
  <rect x="110" y="84" width="80" height="18" fill="none" stroke="var(--s2)"/><text x="122" y="96" fill="var(--muted)" font-size="7">more retries</text>
  <rect x="10" y="52" width="80" height="18" fill="none" stroke="var(--line)"/><text x="26" y="64" fill="var(--muted)" font-size="7">overload</text>
  <path d="M190,29 L214,52" stroke="var(--s2)" fill="none"/><text x="196" y="46" fill="var(--muted)" font-size="9">→</text>
  <path d="M240,70 L180,86" stroke="var(--s2)" fill="none"/><text x="206" y="86" fill="var(--muted)" font-size="9">→</text>
  <path d="M110,95 L60,70" stroke="var(--s2)" fill="none"/><text x="78" y="90" fill="var(--muted)" font-size="9">→</text>
  <path d="M60,52 L120,32" stroke="var(--s2)" fill="none"/><text x="86" y="42" fill="var(--muted)" font-size="9">→</text>
</svg>
^ Retries close a loop — load raises failures, failures raise retries, retries raise load — so once a downstream tips over, the retry traffic alone keeps it collapsed until load is shed or retries are stopped. The structural defenses are circuit breakers (stop sending to a downstream that is failing, so retries do not pile onto a dying service) and backoff with jitter (space retries out and desynchronize them, so they do not arrive as a synchronized thundering herd). Retries without a circuit breaker and jitter are the ingredients of the storm; adding them turns retries back into the safety mechanism they were meant to be.

The second trap is that the fixes have to compose correctly, and each has a failure mode of its own. A retry budget (allow retries only up to, say, 10% of requests, via a token bucket) is the most robust single fix because it caps total retry load regardless of depth — but it must be per-downstream and observable, or you cannot tell a healthy retry rate from a budget that is silently exhausted and dropping legitimate retries. Deadline propagation (pass the remaining time budget down the chain, and refuse to start a retry that cannot finish in time) is essential and commonly missing: without it, a deep layer keeps retrying against a deadline the caller has already given up on, doing pure waste, and the caller's own retry then re-drives the whole doomed subtree. And "retry at only the edge" is clean but not always possible — sometimes an inner layer genuinely must retry a specific idempotent sub-operation — so the real rule is that retries must be *idempotent* (retrying a non-idempotent write, per the companion idempotency module, corrupts state) and *accounted for*: every retry policy in the chain should be visible in one place, budgeted together, and bounded by a shared deadline, rather than each team adding a local retry that looks harmless alone and multiplies with all the others.

**The clean attempts^depth product is only the floor: during an incident retries become a load-driven feedback loop (a metastable failure that outlives its trigger), so retries need circuit breakers and jittered backoff to be safe, a per-downstream retry budget to cap total load regardless of depth, propagated deadlines so no layer retries past the caller's giving-up time, and idempotent operations — and every layer's retry policy must be visible and budgeted together, because each looks harmless alone and multiplies with the rest.**

## External resources

Google's SRE Book chapters on handling overload and cascading failures, and AWS's writing on retry storms and retry budgets — the multiplication of retries across layers, token-bucket retry budgets, and why retries need circuit breakers and backoff.

Writing on metastable failures in distributed systems — why a retry-driven overload has two stable states and can persist after its trigger, and how load shedding and turning off retries are needed to recover.

The companion idempotency and coordinated-omission modules in this topic — retries are only safe on idempotent operations, and the load they add is exactly the kind of tail-latency and overload pressure that a naive measurement (coordinated omission) will under-report during the incident.
