---
id: ship-inter-16
title: Retry at one layer, not every layer — or retries multiply into a storm on the failing dependency
topic: ship-and-operate
level: intermediate
status: ready
time: 21 min
summary: Retries at a single layer ride out a blip; retries at every layer of a call stack multiply. If each of L layers retries its downstream R times, a struggling backend is hit R^L times per request — the retry meant to help pours a multiplied flood on the exact component that was failing. A retry budget (retry at one layer, or cap total retries) keeps the load bounded. On a 3-layer stack retrying 3 times, retrying everywhere hits the backend 27 times per request; retrying at one layer hits it 3.
eli5: If one person asks again when they don't get an answer, fine. But if a message passes through five people and each one re-asks three times when they don't hear back, the poor person at the end gets swamped with re-asks multiplying at every step. Better: let only the first person re-ask, and everyone else just pass the failure along.
---

## Why this module

A retry is a sensible fix at one place and a multiplier at every place, and stacking retries through a call chain quietly turns a small failure into a self-inflicted flood.

Retries are the reflex response to a flaky call: it failed, so try again, and a transient blip is smoothed over. That reasoning is sound applied once. The trouble is that a modern request does not make one call — it passes through a stack of services, each calling the next: the edge calls service A, A calls service B, B calls the database. If every layer independently retries its downstream on failure, the retries do not add, they multiply. The edge retries A; but each attempt at A already retried B; and each of those retried the database. The retry counts compound at every hop.

Do the arithmetic and it is alarming. With L layers each retrying R times, the deepest dependency is called R^L times for a single user request — not R times, not R×L times, but R to the power of L. And this multiplication kicks in exactly when calls are failing, which is exactly when the backend is already struggling. So at the worst possible moment, the retry machinery pours an exponentially multiplied flood onto the component that was already failing, guaranteeing it stays down. A transient dip that one layer of retries would have smoothed becomes a self-inflicted outage, because every layer piled on at once. This is retry amplification, and it is a leading cause of cascading failures.

The fix is a retry budget: do not let every layer retry independently. Retry at a single layer — usually the edge, closest to the user, where one retry covers the whole request — and have the inner layers fail fast and propagate the error up. Or cap the total number of retries per request across the whole stack, regardless of depth. Either way the extra load on a failing dependency is bounded by a small constant, not an exponential in the stack depth. A struggling backend then sees a survivable number of retries instead of a pile-on that scales with how deep your architecture happens to be.

On the fixture, a request crosses 3 retrying layers to reach a failing backend, each layer retrying 3 times. Retrying at every layer hits the backend 3^3 = 27 times for one request. Retrying at only one layer hits it 3 times. Same per-layer retry count; the entire difference is whether the retries multiply.

**Retries at every layer of an L-deep call stack multiply, so a failing backend is called retries^layers times per request — an exponential flood that arrives precisely when it is already failing; a retry budget (retry at one layer, or cap total retries) bounds the extra load by a constant instead.**

## Concepts

The multiplication is structural, not a bug in any one layer. Each layer, viewed alone, is doing the reasonable thing: it retries its immediate downstream a few times to absorb a transient failure. But "its downstream" is itself a retrying layer, so one attempt from above becomes several attempts below, and that fans out at every level. The call count reaching depth d is retries^d — it multiplies by the retry factor at each hop, so the growth is exponential in the number of layers. No single layer is misbehaving; the emergent product is the problem, which is what makes it easy to build accidentally and hard to see from inside any one service.

<svg role="img" aria-label="A call tree: one entry fans out to 3 at layer 1, 9 at layer 2, and 27 at the backend, each node branching by the retry factor" viewBox="0 0 470 185" width="470" height="185">
  <rect x="0" y="0" width="470" height="185" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">retry-every-layer: one request fans out to 27 backend calls</text>
  <circle cx="235" cy="38" r="6" fill="var(--acc-line)"/>
  <text x="245" y="42" font-family="var(--mono)" font-size="8" fill="var(--muted)">1 entry</text>
  <g fill="var(--s2)"><circle cx="150" cy="80" r="5"/><circle cx="235" cy="80" r="5"/><circle cx="320" cy="80" r="5"/></g>
  <text x="335" y="84" font-family="var(--mono)" font-size="8" fill="var(--s2)">3</text>
  <line x1="235" y1="44" x2="150" y2="75" stroke="var(--line)"/><line x1="235" y1="44" x2="235" y2="75" stroke="var(--line)"/><line x1="235" y1="44" x2="320" y2="75" stroke="var(--line)"/>
  <g fill="var(--s2)"><circle cx="120" cy="120" r="3"/><circle cx="150" cy="120" r="3"/><circle cx="180" cy="120" r="3"/><circle cx="205" cy="120" r="3"/><circle cx="235" cy="120" r="3"/><circle cx="265" cy="120" r="3"/><circle cx="290" cy="120" r="3"/><circle cx="320" cy="120" r="3"/><circle cx="350" cy="120" r="3"/></g>
  <text x="360" y="124" font-family="var(--mono)" font-size="8" fill="var(--s2)">9</text>
  <line x1="150" y1="85" x2="120" y2="117" stroke="var(--line)"/><line x1="150" y1="85" x2="150" y2="117" stroke="var(--line)"/><line x1="150" y1="85" x2="180" y2="117" stroke="var(--line)"/>
  <rect x="60" y="150" width="350" height="14" fill="var(--s2)" opacity="0.3"/>
  <text x="150" y="161" font-family="var(--mono)" font-size="8" fill="var(--s2)">27 calls hit the failing backend</text>
</svg>
^ Each retrying node branches by the retry factor, so one request becomes 3, then 9, then 27 calls — the tree's exponential growth landing entirely on the backend.

The danger is that amplification and failure coincide. Retries only fire on failure, so the multiplication is dormant when everything is healthy and switches on the instant the backend starts failing — a brief overload, a deploy, a dependency hiccup. At that moment the backend, already at or over capacity, receives R^L times its normal request rate, which pushes it further down, which causes more failures, which triggers more retries. The retry loop becomes a positive feedback loop that converts a recoverable dip into a sustained outage. This is why retry storms are a classic cause of cascading failure: the recovery mechanism becomes the load that prevents recovery.

A retry budget breaks the multiplication by making retries additive or capped rather than compounding. Retrying at only one layer means the backend sees R calls total (that layer's retries) no matter how many layers sit above it — the load is independent of stack depth, which is the property you want, because your architecture's depth should not determine your dependency's overload factor. Capping total retries per request at a small budget B achieves the same bound differently: the whole stack shares B retries, so the backend sees at most B+1 calls. Both replace an exponential in L with a constant. The key design rule is that retries should be owned at one level (or centrally budgeted), and inner layers should fail fast and let the failure propagate to whoever owns the retry.

This composes with the other overload defenses and is often discussed alongside them. Exponential backoff with jitter spaces retries out in time so even the bounded retries do not arrive in a synchronized burst; circuit breakers stop retrying a dependency that is clearly down, cutting the load to zero rather than a bounded trickle; and deadline propagation ensures retries do not continue past the point where the client has given up. Retry budgets are the piece that specifically kills the multiplicative blow-up across layers. The unifying principle is that a retry is load, and load on a failing system must be bounded — by where you retry, how many times, how spaced out, and whether you retry at all.

**Retries compound to retries^depth because each layer's retry fans out over the retrying layer below, and the multiplication switches on exactly when the backend fails, creating a feedback loop; a retry budget makes the load additive or capped — owned at one layer or centrally bounded — so it stays constant in the stack depth.**

## Worked example

The fixture is a stack depth and a per-layer retry count.

```json filename=modules/ship-and-operate/code/ship-inter-16/stack.json:3-4 COMPLETE
  "layers": 3,
  "retries": 3
```

Three layers between the entry and the failing backend, each retrying its downstream 3 times. Under retry-everywhere, the calls reaching each layer are retries to the power of the depth; under retry-at-one-layer, the retries happen at a single hop and do not compound.

```python filename=modules/ship-and-operate/code/ship-inter-16/retry.py:42-49 COMPLETE
def calls_per_layer_naive(layers, retries):
    """Calls reaching each layer when every layer retries its downstream: retries**depth."""
    return [retries ** d for d in range(layers + 1)]   # index 0 = the entry, index `layers` = the backend


def calls_per_layer_edge(layers, retries):
    """Calls reaching each layer when only the edge retries: retries at every hop, no compounding."""
    return [1] + [retries] * layers
```

The backend load is the last entry — the calls that reach the deepest layer.

```python filename=modules/ship-and-operate/code/ship-inter-16/retry.py:52-53 COMPLETE
def backend_calls(per_layer):
    return per_layer[-1]
```

<svg role="img" aria-label="Backend load grows exponentially with the number of retrying layers under retry-everywhere, but stays flat under retry-one-layer" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">backend calls vs number of retrying layers (retries=3)</text>
  <line x1="45" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="45" y1="40" x2="45" y2="150" stroke="var(--line)"/>
  <polyline points="70,146 160,140 250,122 340,68 430,40" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <g fill="var(--s2)"><circle cx="70" cy="146" r="3"/><circle cx="160" cy="140" r="3"/><circle cx="250" cy="122" r="3"/><circle cx="340" cy="68" r="3"/></g>
  <text x="250" y="80" font-family="var(--mono)" font-size="8" fill="var(--s2)">retry every layer: 3,9,27,81,243...</text>
  <line x1="70" y1="147" x2="430" y2="147" stroke="var(--acc-line)" stroke-width="2"/>
  <text x="120" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">retry one layer: flat 3</text>
  <text x="60" y="166" font-family="var(--mono)" font-size="7" fill="var(--muted)">1 layer</text>
  <text x="405" y="166" font-family="var(--mono)" font-size="7" fill="var(--muted)">5 layers</text>
</svg>
^ Retry-everywhere's backend load curves up exponentially as layers are added, while retry-one-layer's stays pinned at the retry count — so architecture depth stops determining dependency overload.

Predict: retry-everywhere escalates 1 → 3 → 9 → 27 as calls fan out at each hop; retry-at-one-layer stays at 3 from the first hop on. Trace both.

```text filename=modules/ship-and-operate/code/ship-inter-16/retry.py --trace
TRACE — calls reaching each layer (3 layers, 3 retries each)
--------------------------------------------------------
  reaches    retry-every-layer   retry-one-layer
  entry      1                   1
  layer1     3                   3
  layer2     9                   3
  backend    27                  3
--------------------------------------------------------
  retry-every-layer multiplies by 3 each hop; retry-one-layer does not.
```

Under retry-everywhere the calls triple at every hop — 1 at the entry, 3 reaching layer1, 9 reaching layer2, 27 reaching the backend. Each layer faithfully retried three times, and the effect compounded into 27. Under retry-at-one-layer the entry retries three times, so 3 calls reach layer1, and from there each is passed through once — 3 to layer2, 3 to the backend. The retries did not multiply because only one layer owned them. Now the backend load.

```text filename=modules/ship-and-operate/code/ship-inter-16/retry.py --amplify
AMPLIFY — backend load per request
--------------------------------------------------------
  retry every layer: 27 calls  (3^3)
  retry one layer:   3 calls
  amplification of retry-every-layer over retry-one-layer: 9x
--------------------------------------------------------
  the failing backend sees 27 calls instead of 3 for one request.
```

The failing backend is called 27 times per user request under retry-everywhere and 3 times under retry-at-one-layer — a 9× amplification, which is retries^(layers−1). And 9× is only the toy: a real stack of five layers each retrying three times would hit the backend 243 times per request, so a backend at 1× normal load during a blip is suddenly at 243× — no dependency survives that. The retry-at-one-layer number, 3, is independent of how deep the stack is, which is exactly the property that keeps a struggling backend from being buried.

<svg role="img" aria-label="Calls per layer: retry-everywhere escalates 1, 3, 9, 27 as growing bars; retry-one-layer stays flat at 3" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">calls reaching each layer (entry → backend)</text>
  <line x1="40" y1="165" x2="450" y2="165" stroke="var(--line)"/>
  <text x="60" y="34" font-family="var(--mono)" font-size="8" fill="var(--s2)">retry every layer: 1, 3, 9, 27</text>
  <g fill="var(--s2)"><rect x="55" y="161" width="30" height="4"/><rect x="105" y="153" width="30" height="12"/><rect x="155" y="129" width="30" height="36"/><rect x="205" y="57" width="30" height="108"/></g>
  <text x="200" y="50" font-family="var(--mono)" font-size="8" fill="var(--s2)">27</text>
  <text x="270" y="34" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">retry one layer: 1, 3, 3, 3</text>
  <g fill="var(--acc-line)"><rect x="265" y="161" width="30" height="4"/><rect x="315" y="153" width="30" height="12"/><rect x="365" y="153" width="30" height="12"/><rect x="415" y="153" width="30" height="12"/></g>
  <text x="410" y="148" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">3</text>
  <text x="60" y="185" font-family="var(--mono)" font-size="7" fill="var(--muted)">bars grow multiplicatively (exponential in depth)</text>
  <text x="290" y="185" font-family="var(--mono)" font-size="7" fill="var(--muted)">bars stay flat (constant in depth)</text>
</svg>
^ Retry-everywhere's bars grow by the retry factor at each hop, towering to 27 at the backend; retry-one-layer's bars stay flat at 3 no matter the depth.

## Build

Reproduce the escalation. Pure standard library, deterministic, so the 1-3-9-27 fan-out and the 9× amplification come out exactly.

Run `--trace` for the per-layer calls, `--amplify` for the backend load, `--check` for the gate. The self-test pins the exponential growth, the bounded alternative, and its independence from depth.

```python filename=modules/ship-and-operate/code/ship-inter-16/retry.py:94-98 COMPLETE
    naive_is_exponential = naive_backend == retries ** layers
    print("  retry-every-layer hits the backend retries**layers times = %s (%d = %d^%d)"
          % (naive_is_exponential, naive_backend, retries, layers))

    grows_multiplicatively = all(naive[i + 1] == retries * naive[i] for i in range(layers))
    print("  each hop multiplies the calls by the retry count = %s (%s)" % (grows_multiplicatively, naive))
```

The two edge-config flags encode the whole benefit: the load is a fixed retry count, and it does not grow when the stack gets deeper (checked by pretending five more layers exist).

```python filename=modules/ship-and-operate/code/ship-inter-16/retry.py:101-104 COMPLETE
    edge_is_bounded = edge_backend == retries
    print("  retry-one-layer hits the backend a fixed retries times = %s (%d)" % (edge_is_bounded, edge_backend))

    edge_independent_of_depth = edge_backend == backend_calls(calls_per_layer_edge(layers + 5, retries))
    print("  retry-one-layer's backend load does not grow with depth = %s" % edge_independent_of_depth)
```

```text filename=modules/ship-and-operate/code/ship-inter-16/retry.py --check
SELF-TEST — retrying at every layer amplifies multiplicatively; retrying at one layer bounds the load
------------------------------------------------------------------------------------------------
  retry-every-layer hits the backend retries**layers times = True (27 = 3^3)
  each hop multiplies the calls by the retry count = True ([1, 3, 9, 27])
  retry-one-layer hits the backend a fixed retries times = True (3)
  retry-one-layer's backend load does not grow with depth = True
  retry-every-layer's backend load dwarfs retry-one-layer = True (27 vs 3, 9x)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_is_exponential=True  grows_multiplicatively=True  edge_is_bounded=True  edge_independent_of_depth=True  amplification=True
```

Five True flags. Naive_is_exponential: retry-everywhere hits the backend 3^3 = 27 times. Grows_multiplicatively: the per-layer calls are 1, 3, 9, 27, each triple the last. Edge_is_bounded: retry-one-layer hits the backend a fixed 3 times. Edge_independent_of_depth: that 3 does not change even if the stack were five layers deeper — the property that matters. Amplification: 27 versus 3, a 9× flood. The depth-independence flag is the design goal in one line: the load a dependency absorbs should be set by your retry budget, not by how many layers your architecture happens to have.

**The depth-independence flag is the point of a retry budget — retry-one-layer's backend load stays constant however deep the stack grows, so a dependency's overload factor is bounded by policy, not left to explode with every layer added to the architecture.**

## Definition of done

You are done when you reproduce the exponential fan-out and its bounded fix, and can explain why every-layer retries multiply.

Concretely: `--trace` shows retry-everywhere escalating 1, 3, 9, 27 while retry-one-layer stays at 3; `--amplify` shows 27 versus 3 backend calls, a 9× amplification; `--check` prints PASS with five True flags. You can explain that each layer's retry fans out over the retrying layer below so calls reach depth d as retries^d, that the multiplication switches on exactly when the backend fails (a feedback loop), and that a retry budget — retry at one layer, or cap total retries — makes the load constant in depth. You can name the companions: backoff with jitter, circuit breakers, and deadline propagation.

The habit to carry: own retries at one layer (usually the edge) and have inner layers fail fast, or enforce a per-request retry budget across the stack — never let every layer retry independently. When a dependency's load spikes far above the request rate during a partial failure, or a brief dip turns into a sustained outage, suspect retry amplification and count the retrying layers: R^L grows fast. Bound the retries by policy, not by architecture depth.

## Boss fight

The instructive failure is a brief database hiccup that a retry-happy stack turns into an hour-long outage.

A four-layer service (gateway → API → service → database) has retries configured at every layer "for resilience," each retrying three times. The database has a 20-second blip under a load spike; during those seconds every failing call is retried, and because all four layers retry, the database receives 3^4 = 81× its normal request rate at the exact moment it is struggling. The extra load keeps it pinned, so the failures continue, so the retries continue — the blip that should have lasted 20 seconds becomes an hour-long outage that only ends when traffic is manually shed. The fix is a retry budget: retry only at the gateway (or cap total retries per request), and have the inner layers fail fast and propagate — so the database sees at most 3× extra load and rides out the blip. The tell is dependency load that scales with the number of retrying layers, not with traffic.

Your turn, two moves. First, feel the exponential: raise layers to 5 and confirm the backend load jumps to 3^5 = 243 while retry-one-layer stays at 3 — the amplification grows with depth without bound, which is why deep architectures are especially exposed. Second, model the budget-cap variant: instead of retry-at-one-layer, cap total retries per request at a small budget B (say 3) shared across the stack, and confirm the backend load is bounded by B regardless of where the retries happen — showing that a central budget achieves the same constant bound as owning retries at one layer, and is the pattern for stacks where you cannot centralize retries in a single service.

## External resources

Google's SRE book chapter on addressing cascading failures covers retry amplification directly, recommending per-request retry budgets and retrying at a single level to bound the multiplicative load on a failing dependency.

The AWS Builders' Library article "Timeouts, retries, and backoff with jitter" and similar practitioner writeups explain retry storms and the combination of bounded retries, backoff, jitter, and circuit breakers this module places retry budgets among.

Service-mesh retry documentation (Istio, Linkerd) exposes per-route retry budgets and warns about the multiplicative blow-up when retries are configured independently at multiple hops, which is the production form of the choice this module isolates.
