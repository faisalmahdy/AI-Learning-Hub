---
id: keepalive-inter-01
title: Reuse the connection (keep-alive) — opening a fresh TCP+TLS connection per request pays the handshake every time
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: Before a client can send a byte of a request, the connection must be established, and that is not free: a TCP three-way handshake, then — for HTTPS — a TLS handshake, together several round-trips of pure setup paid before the request even starts, plus CPU on both ends for the TLS cryptography. For one request that overhead is unavoidable; the waste appears when a client makes many requests to the same server and opens a new connection for each, repeating the entire handshake every time. On a burst of ten requests that is ten handshakes when one would do. Connection reuse — HTTP keep-alive and the connection pooling libraries build on it — keeps the connection open after a response and sends the next request over the same connection, so the handshake is paid once and every subsequent request skips to the request/response exchange. The per-request cost drops from "handshake + request" to just "request," and the total for N requests falls from N handshakes to one, with the saving growing as the number of requests grows. The stakes are latency (every avoided handshake is round-trips off the critical path, which dominates a small request on a high-latency link) and load (TLS handshakes are CPU-expensive, so reconnecting per request multiplies the server's crypto work). On a fixture of 10 requests where a handshake costs 3 round-trips and a request 1, no keep-alive totals 10×(3+1)=40 round-trips and 10 handshakes, while keep-alive totals 3+10×1=13 round-trips and 1 handshake — a 68% saving that equals (N−1) handshakes.
eli5: Imagine you need to ask a librarian ten quick questions. Every time you walk up, you first have to show your ID, sign in, and get a visitor badge before you're allowed to ask anything — that's the "handshake." The silly way is to leave the building and come back through security ten separate times, doing all the sign-in each time, just to ask one question per visit. The smart way is to sign in once and then ask all ten questions while you're standing there. Same ten answers, but you did the slow security routine once instead of ten times — and you also stopped making the security guard re-check your ID over and over.
---

## Why this module

A small HTTPS request can spend most of its time not talking to the server but getting permission to talk to the server. The TCP handshake and the TLS handshake are round-trips of setup that happen before the request is sent, and on any link with real latency they can dwarf the request itself. That cost is a fixed toll per connection — and the trap is that a client which opens a new connection for every request pays that toll on every request, turning a one-time setup into a per-request tax. Nothing errors; the requests all succeed; they are just each carrying the full weight of establishing a connection to a server the client was talking to a millisecond ago.

The waste appears when a client makes many requests to the same server and opens a new connection for each one: every request repeats the entire handshake, so the client pays the setup cost over and over. On a burst of ten requests, that is ten handshakes when one would do — and TLS handshakes are CPU-expensive on the server too, so reconnecting per request multiplies the server's cryptographic work and can exhaust its connection-accept capacity.

Connection reuse — HTTP keep-alive, and the connection pooling libraries build on it — keeps the connection open after a response and sends the next request over the same connection. The handshake is paid once, and every subsequent request skips straight to the request/response exchange, so the total for N requests falls from N handshakes to one. This module computes both.

**Reuse connections (keep-alive / a connection pool) for repeated requests to the same server, because establishing a connection costs a TCP + TLS handshake of several round-trips (and server CPU) that is paid once per connection — so a new connection per request repeats that handshake N times, while a reused connection pays it once and amortizes it over all the requests.**

## Concepts

**The two totals differ in where the handshake sits:** without reuse it multiplies with the requests; with reuse it is a one-time constant.

```python filename=modules/ship-and-operate/code/keepalive-inter-01/keepalive.py:53-60 COMPLETE
def total_without_keepalive(n, handshake, request):
    """A fresh connection per request: every request pays handshake + request."""
    return n * (handshake + request)


def total_with_keepalive(n, handshake, request):
    """One reused connection: pay the handshake once, then request per request."""
    return handshake + n * request
```

**The handshake count is the whole story** — N without reuse, 1 with it.

```python filename=modules/ship-and-operate/code/keepalive-inter-01/keepalive.py:63-68 COMPLETE
def handshakes_without(n):
    return n


def handshakes_with(n):
    return 1
```

<svg role="img" aria-label="Two request sequences: without keep-alive each request is a handshake block plus a request block, repeated; with keep-alive a single handshake block then a run of request blocks" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">handshake (H, 3 rt) + request (r, 1 rt) per exchange</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">no keep-alive</text>
  <g><rect x="80" y="24" width="26" height="14" fill="var(--s2)"/><rect x="106" y="24" width="9" height="14" fill="var(--s1)"/><rect x="118" y="24" width="26" height="14" fill="var(--s2)"/><rect x="144" y="24" width="9" height="14" fill="var(--s1)"/><rect x="156" y="24" width="26" height="14" fill="var(--s2)"/><rect x="182" y="24" width="9" height="14" fill="var(--s1)"/><text x="196" y="34" fill="var(--muted)" font-size="6">… H r H r H r</text></g>
  <text x="80" y="50" fill="var(--s2)" font-size="6">a handshake before every request</text>
  <text x="10" y="76" fill="var(--muted)" font-size="7">keep-alive</text>
  <g><rect x="80" y="66" width="26" height="14" fill="var(--s2)"/><rect x="106" y="66" width="9" height="14" fill="var(--s1)"/><rect x="118" y="66" width="9" height="14" fill="var(--s1)"/><rect x="130" y="66" width="9" height="14" fill="var(--s1)"/><rect x="142" y="66" width="9" height="14" fill="var(--s1)"/><rect x="154" y="66" width="9" height="14" fill="var(--s1)"/><text x="168" y="76" fill="var(--muted)" font-size="6">… H r r r r r</text></g>
  <text x="80" y="92" fill="var(--s1)" font-size="6">one handshake, then just requests</text>
  <text x="10" y="110" fill="var(--muted)" font-size="6">the wide blocks (handshakes) are the cost keep-alive pays once instead of N times</text>
</svg>
^ Without keep-alive each request is preceded by a full handshake block, so the wide handshake cost repeats for every request; with keep-alive a single handshake precedes a run of request blocks, so the handshake is paid once and the requests stream over the open connection.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/keepalive-inter-01/keepalive.py

The fixture is a burst of ten requests, with a handshake costing three round-trips and a request one.

```json filename=modules/ship-and-operate/code/keepalive-inter-01/keepalive.json:3-5 COMPLETE
  "num_requests": 10,
  "handshake_round_trips": 3,
  "request_round_trips": 1
```

Run `--latency`.

```text filename=--latency
LATENCY — total round-trips for 10 requests (handshake 3, request 1)
------------------------------------------------------------------
  no keep-alive: 10 x (3 + 1) = 40 round-trips  (handshake every request)
  keep-alive:    3 + 10 x 1   = 13 round-trips  (handshake once)
------------------------------------------------------------------
  keep-alive saves 27 round-trips (68%) on this burst.
```

Read the two formulas. Without keep-alive, each of the ten requests pays a handshake (3 round-trips) plus the request itself (1), so the total is 10 × 4 = 40 round-trips. With keep-alive, the handshake is paid once (3 round-trips) and then the ten requests each cost only their 1 round-trip, so the total is 3 + 10 = 13. The reuse cut the burst from 40 round-trips to 13 — a 68% reduction — and did it purely by not re-establishing a connection the client already had. The proportion is worth internalizing: of the 40 round-trips in the no-keep-alive case, 30 were handshake overhead and only 10 were actual request work, so three-quarters of the time was spent on connection setup that keep-alive collapses to almost nothing. On a real high-latency link, where a round-trip might be 100ms, that is 4 seconds versus 1.3 seconds for the same ten requests — the difference between a sluggish and a snappy client, from a single configuration choice.

## Build

The saving is not a fixed discount; it grows with the number of requests, because the handshake is a fixed cost being amortized.

```text filename=--handshakes
HANDSHAKES — how many times the handshake is paid, and the per-request tax
--------------------------------------------------------------
  no keep-alive: 10 handshakes  (30 round-trips of setup, 3 per request)
  keep-alive:    1 handshake   (3 round-trips of setup, 0.3 per request)
--------------------------------------------------------------
    at 1   requests, keep-alive saves 0 round-trips
    at 5   requests, keep-alive saves 12 round-trips
    at 10  requests, keep-alive saves 27 round-trips
    at 100 requests, keep-alive saves 297 round-trips
```

<svg role="img" aria-label="Total round-trips versus request count: without keep-alive the line rises at slope 4 per request, with keep-alive at slope 1, so the gap widens with every request" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">total round-trips grow at slope 4 (no reuse) vs 1 (keep-alive)</text>
  <line x1="30" y1="82" x2="30" y2="22" stroke="var(--grid)"/><line x1="30" y1="82" x2="285" y2="82" stroke="var(--grid)"/>
  <text x="34" y="94" fill="var(--muted)" font-size="6">0 requests →</text>
  <polyline points="30,78 90,62 150,46 210,30 270,14" fill="none" stroke="var(--s2)"/><text x="200" y="24" fill="var(--s2)" font-size="6">no keep-alive (slope 4)</text>
  <polyline points="30,78 90,72 150,66 210,60 270,54" fill="none" stroke="var(--s1)"/><text x="210" y="66" fill="var(--s1)" font-size="6">keep-alive (slope 1)</text>
  <line x1="270" y1="14" x2="270" y2="54" stroke="var(--line)" stroke-dasharray="1 2"/><text x="240" y="50" fill="var(--muted)" font-size="6">gap = (N-1)·H</text>
</svg>
^ Both totals grow with the request count, but without keep-alive the line climbs by handshake+request (4) per request while keep-alive climbs by just request (1), so the gap between them — the saving — widens by one handshake with every additional request.

Look at the per-request handshake tax and how the saving scales. Without keep-alive, every request carries a full 3 round-trips of handshake — the tax is constant per request, so the total setup cost grows linearly with the number of requests (30 round-trips of pure setup for 10 requests, 300 for 100). With keep-alive, the 3 round-trips of handshake are spread across all the requests: at 10 requests the amortized tax is 0.3 round-trips per request, and at 100 it is 0.03 — the more requests you make, the closer the per-request setup cost approaches zero. That is the signature of amortizing a fixed cost, and it is why the saving is exactly (N−1) handshakes: the first request needs its handshake either way, and every request after the first saves a whole handshake. At 1 request there is no saving (both pay one handshake); at 100 requests keep-alive saves 297 round-trips. The lesson generalizes to any per-operation fixed cost — a database connection, a process spawn, a cold-start warmup — the more operations you do, the more it pays to establish the expensive resource once and reuse it, and the anti-pattern is always the same: recreating it per operation.

```python filename=modules/ship-and-operate/code/keepalive-inter-01/keepalive.py:105-112 COMPLETE
    without_pays_per_request = wo == n * (h + r)
    print("  without keep-alive: total = N x (handshake + request) = %s (%d)" % (without_pays_per_request, wo))

    with_amortizes = wk == h + n * r
    print("  with keep-alive: total = handshake + N x request = %s (%d)" % (with_amortizes, wk))

    handshake_paid_once = handshakes_with(n) == 1 and handshakes_without(n) == n
    print("  keep-alive pays the handshake once, not N times = %s (1 vs %d)" % (handshake_paid_once, n))
```

## Definition of done

The self-test pins the two totals, the handshake counts, the fewer round-trips, and the (N−1)-handshake saving.

```python filename=modules/ship-and-operate/code/keepalive-inter-01/keepalive.py:114-117 COMPLETE
    keepalive_fewer = wk < wo
    print("  keep-alive uses fewer round-trips = %s (%d < %d)" % (keepalive_fewer, wk, wo))

    saving_is_n_minus_1_handshakes = (wo - wk) == (n - 1) * h
    print("  the saving equals (N-1) handshakes = %s (%d = %d x %d)" % (saving_is_n_minus_1_handshakes, wo - wk, n - 1, h))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — a new connection per request repeats the handshake N times; keep-alive pays it once and amortizes it
--------------------------------------------------------------------------------------------------------------------
  without keep-alive: total = N x (handshake + request) = True (40)
  with keep-alive: total = handshake + N x request = True (13)
  keep-alive pays the handshake once, not N times = True (1 vs 10)
  keep-alive uses fewer round-trips = True (13 < 40)
  the saving equals (N-1) handshakes = True (27 = 9 x 3)
```

<svg role="img" aria-label="Round-trips for the ten-request burst: no keep-alive 40 (30 handshake, 10 request), keep-alive 13 (3 handshake, 10 request)" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">40 round-trips (mostly handshake) vs 13 (mostly request)</text>
  <text x="10" y="36" fill="var(--muted)" font-size="7">no keep-alive</text>
  <rect x="90" y="26" width="150" height="14" fill="var(--s2)"/><rect x="240" y="26" width="50" height="14" fill="var(--s1)"/>
  <text x="150" y="52" fill="var(--s2)" font-size="6">30 handshake</text><text x="244" y="52" fill="var(--s1)" font-size="6">10 req</text>
  <text x="10" y="72" fill="var(--muted)" font-size="7">keep-alive</text>
  <rect x="90" y="62" width="15" height="14" fill="var(--s2)"/><rect x="105" y="62" width="50" height="14" fill="var(--s1)"/>
  <text x="160" y="72" fill="var(--muted)" font-size="6">3 handshake + 10 req = 13</text>
  <text x="10" y="90" fill="var(--muted)" font-size="6">keep-alive shrinks the handshake slab from 30 round-trips to 3</text>
</svg>
^ The no-keep-alive burst is 40 round-trips of which 30 are handshake overhead, while keep-alive is 13 round-trips with only 3 of handshake — the reuse collapses the large handshake slab to a single one, leaving mostly actual request work.

**Done means the amortization is proven on real counts: 10 requests without keep-alive cost 10×(3+1)=40 round-trips and 10 handshakes, while with keep-alive they cost 3+10×1=13 round-trips and 1 handshake — a saving of exactly (N−1) handshakes = 27 round-trips (68%) — so connections must be reused for repeated requests to the same server, not re-established per request.**

## Boss fight

Predict two ways connection reuse is more than "turn keep-alive on," because pooled connections are shared, expiring resources and reuse has newer and subtler forms.

The first trap is that a connection pool is a bounded, shared resource with its own failure modes, so "reuse connections" becomes "manage a pool correctly." The pool has a size limit, and if it is too small it becomes the bottleneck — requests queue waiting for a free connection even though the server has capacity (this is the Little's-law pool-sizing problem) — while too large a pool holds idle connections the server must keep alive, consuming its file descriptors and memory. Pooled connections also go stale: the server, a load balancer, or a firewall can close an idle connection without the client noticing, so the client must detect a dead connection (a failed write, a stale-check probe) and re-establish rather than reusing a corpse and failing the request — which is why pools have idle timeouts and validation. And keep-alive interacts with load balancing: a long-lived connection is pinned to one backend, so if you reuse connections aggressively across a fleet behind an L4 balancer, traffic can concentrate on the backends whose connections happen to be reused, defeating the balancing — which is one reason server-side keep-alive has a max-requests-per-connection and max-idle limit that periodically forces reconnection to redistribute. So reuse is a tuning problem: pool size matched to concurrency, idle and lifetime limits to shed stale and pin-prone connections, and validation to avoid reusing dead ones.

The second trap is that the handshake cost keep-alive amortizes has itself been attacked at the protocol level, and the modern picture is a layered set of optimizations, not just keep-alive. TLS 1.3 cut the TLS handshake from two round-trips to one (and offers 0-RTT resumption for repeat connections, with replay caveats), and session resumption lets even a new connection skip the full handshake — so the per-handshake cost in this module's model is smaller on modern stacks, though never zero. HTTP/2 goes further by MULTIPLEXING many concurrent requests over a single connection (so you get the reuse benefit even for parallel requests, which HTTP/1.1 keep-alive could not — it serialized requests on a connection or needed several connections), and HTTP/3 moves to QUIC over UDP, folding transport and crypto setup into fewer round-trips and surviving IP changes. The through-line is unchanged — connection and crypto setup is a fixed cost you want to pay rarely and amortize widely — but the toolkit is keep-alive plus session resumption plus multiplexing plus newer transports, and the right choice depends on the traffic pattern (many small requests to one host favor multiplexing; a few large transfers care less). The anti-pattern the module targets — a fresh full handshake per request — is defeated by all of these, and a well-configured modern client combines them.

**Connection reuse is pool management, not a boolean: size the pool to concurrency (too small bottlenecks, too large wastes server resources), validate connections and set idle/lifetime limits so you neither reuse a dead connection nor pin traffic to one backend behind a load balancer. And keep-alive is one layer of a stack: TLS 1.3 and session resumption shrink the handshake, HTTP/2 multiplexes many requests over one connection (reuse even for parallel requests), and HTTP/3/QUIC folds setup further — combine them per traffic pattern, but the invariant is unchanged: pay connection and crypto setup rarely and amortize it widely, never a full handshake per request.**

## External resources

The HTTP specifications and MDN documentation on keep-alive, connection management, and HTTP/2 multiplexing — persistent connections, the Connection header, and why HTTP/2 reuses one connection for concurrent requests.

TLS handshake and performance references (TLS 1.3, session resumption, 0-RTT) and connection-pool documentation for HTTP clients and databases — the round-trip and CPU cost of handshakes, resumption, and how pools are sized, validated, and expired.

The companion connection-pool-sizing, cold-start, and retry modules in this topic — connection reuse is the same amortize-a-fixed-cost principle as pooling any expensive resource and warming an instance before traffic, and a pool sized by Little's law is what makes keep-alive's shared connections a benefit rather than a bottleneck.
