---
id: ship-inter-09
title: Stamp every log line with a correlation id — or concurrent requests interleave into a jumble
topic: ship-and-operate
level: intermediate
status: ready
time: 5-8h
summary: A service handles many requests at once and each emits log lines as it moves through its steps — start, query, done — and those lines all land in one stream, interleaved, because the requests run concurrently, so without a correlation id on each line you cannot tell which "query" belongs to which request and the log is a pile of steps with no way to reassemble any single request's path. The naive attempt — assume the lines are in request order and chunk them — mis-attributes steps across requests, reconstructing paths that never happened because it stitched one request's start to another's query. A correlation id fixes it for free: generate an id per request, stamp it on every line, and propagate it downstream so the whole distributed path shares one id; then reconstructing a request is a filter — keep the lines with its id, in time order, and you have its exact path. On the fixture three requests interleave as start,start,start,query,query,query,done,done,done; filtering by id recovers all three exact start-query-done paths while chunking the id-stripped log reconstructs zero valid requests. The lesson is that in a concurrent system a log without correlation ids records what happened but not to whom, and the id is the one field that turns an unreadable interleaving back into per-request stories.
eli5: Imagine three people telling you their days at the same time, one sentence each, taking turns — "I woke up." "I woke up." "I woke up." "I ate." ... If you didn't write down who said what, you could never untangle whose day was whose. But if you put each person's name on every sentence, you just filter by name and read one person's whole day back perfectly. A correlation id is that name tag on every log line, and without it three requests talking at once become one unreadable blur.
---

## Why this module

A log is supposed to let you answer "what happened to this request?" — trace it from the moment it arrived, through each service and step, to its response or its error. On a system handling one request at a time, the log does this automatically: the lines are in order, so you just read them top to bottom. But real services handle many requests concurrently, and the instant they do, the log stops being one story and becomes many stories told at once, their lines shuffled together in time order. A line that says "query executed" is now ambiguous — which of the five in-flight requests executed a query?

Without something on each line identifying its request, that ambiguity is unresolvable. The log faithfully records every step that happened, but it has thrown away the association between steps and requests, and you cannot reconstruct it after the fact from the step names and timestamps alone, because the same step names recur across every request. The tempting reconstruction — assume the log is basically in request order and slice it into per-request chunks — is worse than useless: under concurrency the chunks straddle request boundaries, so you get "paths" that stitch one request's start onto another's middle, phantom requests that never happened, and you draw conclusions from them.

The fix is a correlation id: a unique identifier generated when a request enters the system and stamped onto every log line that request produces, then propagated to every downstream service it calls so the entire distributed trace shares one id.

<svg viewBox="0 0 700 150" role="img" aria-label="A request entering at a gateway that generates id abc123, then flowing through service A, service B, and service C, each passing the id along in a request header and logging lines tagged with abc123. Filtering all services' logs by abc123 gives the whole cross-service path.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the id is generated once at the gateway and propagated to every hop</text>
    <rect x="20" y="45" width="90" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="65" y="60" text-anchor="middle" fill="var(--acc-ink)" font-size="7">gateway</text><text x="65" y="70" text-anchor="middle" fill="var(--acc-ink)" font-size="7">id=abc123</text>
    <line x1="110" y1="60" x2="150" y2="60" stroke="var(--ink)"></line><text x="130" y="54" text-anchor="middle" fill="var(--muted)" font-size="6">header</text>
    <rect x="150" y="45" width="80" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="190" y="63" text-anchor="middle" fill="var(--ink)" font-size="7">service A</text>
    <line x1="230" y1="60" x2="270" y2="60" stroke="var(--ink)"></line>
    <rect x="270" y="45" width="80" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="310" y="63" text-anchor="middle" fill="var(--ink)" font-size="7">service B</text>
    <line x1="350" y1="60" x2="390" y2="60" stroke="var(--ink)"></line>
    <rect x="390" y="45" width="80" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="430" y="63" text-anchor="middle" fill="var(--ink)" font-size="7">service C</text>
    <text x="30" y="100" fill="var(--s1)" font-size="7">[abc123]</text><text x="170" y="100" fill="var(--s1)" font-size="7">[abc123]</text><text x="290" y="100" fill="var(--s1)" font-size="7">[abc123]</text><text x="410" y="100" fill="var(--s1)" font-size="7">[abc123]</text>
    <text x="30" y="114" fill="var(--muted)" font-size="7">every service logs the same id →</text>
    <text x="500" y="63" fill="var(--acc-ink)" font-size="8">filter abc123 →</text><text x="500" y="77" fill="var(--muted)" font-size="7">whole path, all services</text>
    <text x="30" y="138" fill="var(--muted)" font-size="8">forget to propagate the header and each service's trace becomes an isolated island</text>
  </g>
</svg>
^ The id is minted once at the entry point and carried in a request header to every downstream service, which logs it too. Filtering all the services' logs by that one id reassembles the whole cross-service path — the payoff, and the reason propagation is not optional. With it, reconstructing a request is a filter — select the lines carrying its id, order by time, and you have its exact path, cleanly separated from every other request running alongside it. This module makes the contrast concrete: three requests interleaved in one log, reconstructed exactly by id-filter and disastrously by naive chunking. Everything runs offline against a log fixture, stdlib Python 3, `$0.00`, with every reconstruction computed. The instinct to unlearn is that a complete log is a readable log. Under concurrency, completeness is not enough; without a correlation id, the log has all the steps and none of the stories.

## Concepts

Named here so you can find them again; each is built below.

- **Correlation id** — a unique id per request, stamped on every line it emits and propagated downstream.
- **Interleaving** — concurrent requests' log lines shuffled together in one time-ordered stream.
- **Reconstruction** — reassembling one request's ordered path from the log.
- **Id-filter** — selecting the lines carrying one id, in time order; the exact path.
- **Naive chunking** — slicing the id-less log into fixed groups; mis-attributes across requests.
- **Phantom request** — a reconstructed path that stitches steps from different requests together.

## Worked example

Source: the request-tracing view of a service's logs — reconstructing one request's path from a concurrent stream. The events stand in for a real interleaved log; the small step vocabulary (start, query, done) keeps the reconstruction exact.

Script and fixture: `modules/ship-and-operate/code/ship-inter-09/` — `trace.py`, and `log.json`, three interleaved requests. Every command runs from there.

### The interleaved log

Three requests run at once, so their lines shuffle together in the stream.

```
# $ python3 trace.py --log
#   t   with correlation id       without id
#   1   [r1] start             start
#   2   [r2] start             start
#   3   [r3] start             start
#   4   [r1] query             query
#   6   [r3] query             query
#   7   [r1] done              done
#   9   [r3] done              done
```

run: 2026-08-27 · deterministic; the log stream is a fixture · 9 events, 3 requests · `python3 trace.py --log`

Read the two columns. The correlation-id column tags each line with the request that produced it, `r1`, `r2`, `r3`. The without-id column is what you get if you do not stamp the id: a stream of `start`, `start`, `start`, `query`, … where every request's steps look identical. The right column has exactly the same events as the left — it is a complete log — but it has lost the one piece of information that separates the three stories.

### Reconstruction, two ways

With ids, reconstruction is a group-by; without, the naive approach is to chunk the stream.

```
# trace.py:39-51 — COMPLETE (filter by id vs chunk the id-less stream)
def by_correlation_id(events):
    """Filter the log by each request's id and read its steps in time order -- the exact path."""
    paths = {}
    for e in sorted(events, key=lambda e: e["t"]):
        paths.setdefault(e["id"], []).append(e["step"])
    return paths


def by_naive_chunking(events, steps_per_request):
    """No ids: assume the log is in request order and chunk it into fixed-size groups."""
    steps = [e["step"] for e in sorted(events, key=lambda e: e["t"])]
    return [steps[k:k + steps_per_request] for k in range(0, len(steps), steps_per_request)]
```

A reconstructed path counts as a real request only if it matches the expected step sequence exactly:

```
# trace.py:53-55 — COMPLETE (a real request follows the expected step sequence)
def is_valid_path(path, expected):
    """A real request follows the expected step sequence exactly."""
    return path == expected
```

`by_correlation_id` groups the lines by their id and reads each group's steps in time order — the request's real path. `by_naive_chunking` has no id to group on, so it falls back to the only structure it can see: it assumes the log is in request order and cuts it into groups of three. Run both:

```
# $ python3 trace.py --trace
#   by correlation id:
#     r1    ['start', 'query', 'done']   valid=True
#     r2    ['start', 'query', 'done']   valid=True
#     r3    ['start', 'query', 'done']   valid=True
#   by naive chunking (no ids):
#     chunk0 ['start', 'start', 'start'] valid=False
#     chunk1 ['query', 'query', 'query'] valid=False
#     chunk2 ['done', 'done', 'done']    valid=False
```

run: 2026-08-27 · deterministic · `python3 trace.py --trace`

The id-filter recovers all three real paths — each a clean `start, query, done`. The naive chunker recovers nothing usable: because the three requests interleaved step-by-step, its groups are `[start, start, start]`, `[query, query, query]`, `[done, done, done]` — three "requests" that each did the same step three times and nothing else, none of which is a real path any request took. The chunker did not just get the order slightly wrong; it fabricated three phantom requests out of the shuffled steps, and an engineer trying to debug from them would be chasing ghosts.

<svg viewBox="0 0 700 220" role="img" aria-label="Nine log lines interleaved: three requests each doing start, query, done. On the left, correlation-id filtering draws horizontal groupings that pull r1's, r2's, r3's lines into three clean start-query-done paths. On the right, naive chunking draws vertical cuts that group the three starts, then the three queries, then the three dones — invalid paths.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">same 9 lines: id-filter recovers real paths, chunking cuts across requests</text>
    <text x="30" y="40" fill="var(--s1)">by id (correct)</text>
    <g font-size="8">
      <rect x="30" y="50" width="60" height="16" fill="var(--acc-soft)" stroke="var(--s1)"></rect><text x="60" y="62" text-anchor="middle" fill="var(--acc-ink)">r1 start</text>
      <rect x="95" y="50" width="60" height="16" fill="var(--acc-soft)" stroke="var(--s1)"></rect><text x="125" y="62" text-anchor="middle" fill="var(--acc-ink)">r1 query</text>
      <rect x="160" y="50" width="60" height="16" fill="var(--acc-soft)" stroke="var(--s1)"></rect><text x="190" y="62" text-anchor="middle" fill="var(--acc-ink)">r1 done</text>
      <text x="230" y="62" fill="var(--s1)">✓ valid</text>
      <rect x="30" y="70" width="60" height="16" fill="var(--panel)" stroke="var(--line)"></rect><text x="60" y="82" text-anchor="middle" fill="var(--muted)">r2 start</text>
      <rect x="95" y="70" width="60" height="16" fill="var(--panel)" stroke="var(--line)"></rect><text x="125" y="82" text-anchor="middle" fill="var(--muted)">r2 query</text>
      <rect x="160" y="70" width="60" height="16" fill="var(--panel)" stroke="var(--line)"></rect><text x="190" y="82" text-anchor="middle" fill="var(--muted)">r2 done</text>
      <text x="230" y="82" fill="var(--s1)">✓</text>
    </g>
    <text x="400" y="40" fill="var(--s2)">by chunk (wrong)</text>
    <g font-size="8">
      <rect x="400" y="50" width="55" height="16" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"></rect><text x="427" y="62" text-anchor="middle" fill="var(--ink)">start</text>
      <rect x="400" y="70" width="55" height="16" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"></rect><text x="427" y="82" text-anchor="middle" fill="var(--ink)">start</text>
      <rect x="400" y="90" width="55" height="16" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"></rect><text x="427" y="102" text-anchor="middle" fill="var(--ink)">start</text>
      <text x="465" y="82" fill="var(--s2)">✗ [start,start,start]</text>
    </g>
    <text x="30" y="150" fill="var(--muted)" font-size="8">id-filter groups a request's own lines (horizontal); chunking groups by position (vertical)</text>
    <text x="30" y="170" fill="var(--muted)" font-size="8">under interleaving the vertical cut slices across all three requests → phantom paths</text>
  </g>
</svg>
^ Filtering by id pulls each request's own three lines together into a real path; chunking cuts the shuffled stream by position, grouping the three starts, then the three queries, into paths no request ever took. The id is what makes the horizontal grouping possible.

**Under concurrency a service's log lines interleave, so the same step name recurs across every request and a log without a correlation id records every step but not which request it belonged to — id-filtering recovers all three exact start-query-done paths while naive chunking of the id-less stream reconstructs zero valid requests (start,start,start …), because the fix is a unique id stamped on every line and propagated downstream, turning reconstruction into a filter.**

### The self-test

The `--check` mode plants the bug — an id-less log reconstructed by chunking — and proves it: id-filtering recovers every exact path, chunking recovers none, the requests are genuinely interleaved, and filtering by one id isolates exactly that request.

```
# $ python3 trace.py --check
#   every id-filtered path is the exact expected sequence = True (3 requests)
#   naive chunking reconstructs ZERO valid requests = True (0 of 3 chunks valid)
#   the requests are interleaved in the log (not grouped) = True (['r1','r2','r3','r1',...])
#   filtering by one id isolates exactly that request = True (r1: 3 lines)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 trace.py --check`

The `interleaved` line is the precondition that makes the whole thing bite: if the requests happened to run one-at-a-time (their lines grouped), even the id-less log would be readable by chunking, and the correlation id would seem unnecessary. It is the interleaving — which you cannot prevent and cannot predict — that makes the id essential, and `naive_none_valid` is the price of not having it: not a slightly-degraded reconstruction, but zero valid requests recovered.

<svg viewBox="0 0 700 150" role="img" aria-label="Two bars of valid request paths recovered. By correlation id: 3 of 3. By naive chunking: 0 of 3. The id-filter recovers everything, chunking recovers nothing.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">valid request paths recovered from the same 9 log lines</text>
    <line x1="60" y1="120" x2="660" y2="120" stroke="var(--line)"></line>
    <text x="30" y="52" fill="var(--s1)" font-size="8">by id</text>
    <rect x="110" y="40" width="330" height="22" fill="var(--s1)"></rect><text x="275" y="55" text-anchor="middle" fill="var(--panel)" font-size="8">3 of 3 paths ✓</text>
    <text x="30" y="92" fill="var(--s2)" font-size="8">by chunk</text>
    <rect x="110" y="80" width="6" height="22" fill="var(--s2)"></rect><text x="150" y="95" fill="var(--s2)" font-size="8">0 of 3 paths ✗</text>
    <text x="110" y="138" fill="var(--muted)" font-size="8">the same complete log, opposite outcomes — the id is the only difference</text>
  </g>
</svg>
^ From identical log content, correlation-id filtering recovers all three real paths and naive chunking recovers none. Completeness is equal; only the id makes the log reconstructable.

```
# trace.py:95-101 — COMPLETE (id-filter recovers every exact path; chunking recovers none)
    corr_all_valid = len(corr) > 0 and all(is_valid_path(p, expected) for p in corr.values())
    print("  every id-filtered path is the exact expected sequence = %s (%d requests)"
          % (corr_all_valid, len(corr)))

    naive = by_naive_chunking(events, len(expected))
    naive_valid = sum(1 for p in naive if is_valid_path(p, expected))
    naive_none_valid = naive_valid == 0
```

And isolating a single request is exactly a filter on its id — every line matching, and all of them:

```
# trace.py:111-113 — COMPLETE (filtering by one id returns exactly that request's lines)
    one = list(corr)[0]
    filtered = [e for e in events if e["id"] == one]
    filter_isolates = all(e["id"] == one for e in filtered) and len(filtered) == len(expected)
```

### The running tally

| reconstruction | r1 | r2 | r3 | valid paths |
|---|---|---|---|---|
| by correlation id | start,query,done | start,query,done | start,query,done | 3 of 3 |
| by naive chunking | start,start,start | query,query,query | done,done,done | 0 of 3 |

Read across: the id rows are three real, identical, valid request paths; the chunk rows are three malformed groups that no request produced. The two reconstructions ran on the same nine events — the only difference is whether each event carried its request's id. That single field is the difference between three clean stories and three phantoms, and it costs nothing to add: a uuid generated at the entry point and passed along. Completeness gave you every step; the correlation id gave you the ability to say whose step it was, which is the entire job of a trace.

### What we did not settle

This is the core of request tracing; distributed systems build it out. The correlation id must propagate across service boundaries — passed in a request header (often `X-Request-Id` or a W3C `traceparent`) so a request touching five services shares one id across all their logs — and that propagation is the part teams most often forget, leaving each service's trace an island. Full distributed tracing (OpenTelemetry, Zipkin, Jaeger) adds a span id per operation and parent links, so you get not just which lines belong to a request but the tree of calls and their timings. Structured logging (each line a key-value record, not a string) is what makes filtering by id cheap at scale. And ids should be generated at the true entry point (the load balancer or gateway) and never reused. The invariant: in a concurrent or distributed system, stamp a correlation id on every log line and propagate it everywhere, because a log without it records what happened but not to whom.

## Build

The build in one paragraph: generate a unique correlation id when a request enters the system, stamp it on every log line that request produces, and propagate it to every downstream service (via a request header) so the whole distributed path shares one id — then reconstructing a request is a filter on its id, ordered by time, which recovers its exact path even when many requests interleave. Generate the id at the true entry point, use structured (key-value) log lines so filtering scales, adopt a standard propagation header and full span-based tracing for multi-service call trees, and never reconstruct requests by position because concurrency shuffles the stream.

We opened on the interleaved log. The number that proves the fix is how many real paths each reconstruction recovers:

```
# modules/ship-and-operate/code/ship-inter-09/ — COMPLETE, run from that directory
$ python3 trace.py --trace
  by correlation id:      3 valid paths
  by naive chunking:      0 valid paths
```

Now build your own. Take a real concurrent workload, emit logs both with and without a correlation id, and try to reconstruct individual requests from each. Your number to beat is not log volume; it is **how many real request paths you can recover, with ids versus without** — id-filtering should recover every path while position-based reconstruction recovers few or none. Confirm the requests genuinely interleave. Bring back both recovery counts. Good luck.

## Definition of done

- [ ] A log of events, each tagged with a correlation id, from interleaved concurrent requests
- [ ] Reconstruction by id-filter (group by id, order by time)
- [ ] Naive reconstruction by chunking the id-stripped stream
- [ ] Confirmation id-filtering recovers every request's exact path
- [ ] Confirmation naive chunking recovers zero valid paths under interleaving
- [ ] Confirmation the requests are genuinely interleaved and one id isolates one request
- [ ] `python3 trace.py --check` printing SELF-TEST PASS: corr_all_valid, naive_none_valid, interleaved, filter_isolates
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does a complete log become unreadable under concurrency without correlation ids?
2. Why does naive chunking of the id-less stream produce phantom requests?
3. What makes reconstruction trivial once every line carries a correlation id?
4. Where should the correlation id be generated, and how does it reach a downstream service's logs?
5. Your own concurrent workload was logged both ways. How many real paths did each reconstruction recover, and were the requests interleaved?

## External resources

- W3C Trace Context (`traceparent`) and the OpenTelemetry tracing docs — my summary: the standard for propagating a trace id across services and the span model above a bare correlation id; read it for distributed call-tree tracing.
- Any structured-logging guide (JSON log lines with a request-id field) — my summary: why machine-parseable log records make id-filtering cheap at scale; read it for the logging format this module assumes.
- This hub, *ship-inter-08* (liveness vs readiness) and *ship-inter-05* (deadline propagation) — read them for other cross-cutting concerns a request carries through a system, propagation being the shared theme.
