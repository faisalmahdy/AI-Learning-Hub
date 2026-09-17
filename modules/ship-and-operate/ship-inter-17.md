---
id: ship-inter-17
title: Keep metric labels bounded — one user_id label turns a 4-series counter into one per user
topic: ship-and-operate
level: intermediate
status: ready
time: 19 min
summary: A metrics backend does not store "a counter" — it stores one independent time series for every distinct combination of label values that has appeared. A request counter labeled by route and status is a handful of series and stays flat no matter how much traffic you take. The obvious enhancement is fatal: add user_id to slice by user, and now there is one series per (route, status, user), growing with your user base. A backend like Prometheus holds every active series in memory, so a high-cardinality label is not a bigger number in a cell — it multiplies the whole table. On eight events spanning 2 routes, 2 statuses, and 5 users, labeling by (route, status) makes 4 series and caps at 4; adding user makes 8 already and ceilings at 2×2×5 = 20 — and the 5 is your user count, which only grows.
eli5: A dashboard keeps a separate little tally for every combination of the tags you attach to a number. If your tags are things like "which page" and "did it work" there are only a few combinations, so a few tallies. If you add "which person" as a tag, you suddenly need a separate tally for every person who ever visits — and that list never stops growing until the dashboard runs out of room.
---

## Why this module

A metric label looks free — it is just a string you attach — but every distinct value you attach spawns a permanent, independent time series the backend must hold.

The mental model that causes the outage is "a counter is one number, and labels are just ways to look at it." That is backwards. The backend stores one time series per distinct combination of label values observed. A counter labeled by route and status, with two routes and two statuses, is at most four series — flat forever, whatever your traffic. So far so good. Then someone adds `user_id` to break the metric down per user, and the series count becomes one per (route, status, user). The number of series now grows with the number of users, and a backend like Prometheus keeps every active series resident in memory.

**A high-cardinality label does not make a metric bigger — it multiplies the number of series, and series are what the backend pays for.**

The rule is that labels must be bounded and small — route, status, method, region — values known ahead of time and few. Identifiers — user, request, session, full URL — are unbounded and belong in logs or traces, which are built for high cardinality. This module counts the series each scheme produces on one event stream and shows the multiplication.

## Concepts

A **time series** is the unit of storage: a metric name plus one specific set of label values, tracked over time. `requests_total{route="/a",status="200"}` is one series; changing any label value makes a different series.

**Cardinality** is the number of distinct series a metric produces. The ceiling is the **product** of each label's distinct-value count: two routes times two statuses is four; add five users and it is twenty. Because it is a product, one large factor dominates all the small ones — a label with thousands of values multiplies every bounded label against it.

A **bounded label** has a small, fixed set of possible values you can enumerate in advance: HTTP status, route template, method, region. An **unbounded label** has a value set that grows with usage: user id, request id, session id, email, a URL with query parameters. Bounded labels keep cardinality flat; one unbounded label makes it scale with traffic diversity.

The trap is that the unbounded label is often the most tempting one — "I want to see requests per user" — and it looks like a one-line improvement. The cost is invisible until the series count crosses what the backend can hold, at which point scrapes slow, memory balloons, and the backend can fall over, taking your visibility with it exactly when you need it.

**Cardinality is a product of label value counts, so the right question about a new label is not "is it useful" but "how many distinct values will it ever take."**

Because the total is a product, the biggest factor sets the scale — a grid of route by status is small, but stacking a tall user axis behind it multiplies the whole plane.

<svg role="img" aria-label="A 2 by 2 grid of route and status, multiplied by a deep user axis into a 2 by 2 by 5 volume" viewBox="0 0 300 130" width="300" height="130">
  <rect x="20" y="40" width="30" height="30" fill="none" stroke="var(--s2)" stroke-width="1"/>
  <rect x="50" y="40" width="30" height="30" fill="none" stroke="var(--s2)" stroke-width="1"/>
  <rect x="20" y="70" width="30" height="30" fill="none" stroke="var(--s2)" stroke-width="1"/>
  <rect x="50" y="70" width="30" height="30" fill="none" stroke="var(--s2)" stroke-width="1"/>
  <text x="22" y="115" fill="var(--muted)" font-size="8">route × status = 4</text>
  <text x="95" y="70" fill="var(--muted)" font-size="14">×</text>
  <line x1="120" y1="100" x2="120" y2="30" stroke="var(--s1)" stroke-width="1"/>
  <line x1="130" y1="100" x2="130" y2="30" stroke="var(--s1)" stroke-width="1"/>
  <line x1="140" y1="100" x2="140" y2="30" stroke="var(--s1)" stroke-width="1"/>
  <line x1="150" y1="100" x2="150" y2="30" stroke="var(--s1)" stroke-width="1"/>
  <line x1="160" y1="100" x2="160" y2="30" stroke="var(--s1)" stroke-width="1"/>
  <text x="118" y="115" fill="var(--muted)" font-size="8">user = 5 (and rising)</text>
  <text x="185" y="70" fill="var(--muted)" font-size="14">= 20</text>
  <text x="230" y="70" fill="var(--muted)" font-size="8">series</text>
</svg>
^ The 4-cell route×status grid is fixed; multiplying it by the user axis turns 4 series into 20, and the user axis is the one that keeps growing.

The fix for wanting per-user detail is not a metric label — it is a log line or a trace span, both indexed for high cardinality by design.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-17/cardinality.py

The fixture is eight request events, each with a bounded route and status and an unbounded user.

```json filename=modules/ship-and-operate/code/ship-inter-17/metrics.json:1-14 COMPLETE
{
  "_meta": "A stream of request events, each with a route, a status, and the user who made it. A metric emitted with a set of labels creates one time series per distinct combination of label values that actually occurs. route and status are bounded (few values); user is unbounded (grows with your user base). The question: how many time series does each labeling scheme create?",
  "events": [
    {"route": "/a", "status": 200, "user": "u1"},
    {"route": "/a", "status": 200, "user": "u2"},
    {"route": "/a", "status": 500, "user": "u3"},
    {"route": "/b", "status": 200, "user": "u1"},
    {"route": "/b", "status": 200, "user": "u4"},
    {"route": "/b", "status": 500, "user": "u5"},
    {"route": "/a", "status": 200, "user": "u3"},
    {"route": "/b", "status": 500, "user": "u2"}
  ]
}
```

A labeling scheme is just a list of label keys. The distinct series it creates is the set of observed value-tuples over those keys; the ceiling is the product of each key's distinct-value count.

```python filename=modules/ship-and-operate/code/ship-inter-17/cardinality.py:42-56 COMPLETE
def series(events, labels):
    """The distinct time series a labeling scheme creates: one per observed combination of label values."""
    return sorted({tuple(str(e[k]) for k in labels) for e in events})


def distinct(events, field):
    return len({e[field] for e in events})


def ceiling(events, labels):
    """The cardinality ceiling: the product of each label's distinct value count."""
    prod = 1
    for k in labels:
        prod *= distinct(events, k)
    return prod
```

The two schemes differ by one label. That single word — `user` — is the whole module.

```python filename=modules/ship-and-operate/code/ship-inter-17/cardinality.py:61-67 COMPLETE
BOUNDED = ["route", "status"]
UNBOUNDED = ["route", "status", "user"]


def series_view(data):
    events = data["events"]
    b, u = series(events, BOUNDED), series(events, UNBOUNDED)
```

Run `--series` and list what each scheme actually creates.

```text filename=--series
SERIES — distinct time series per labeling scheme (8 events)
----------------------------------------------------------------
  bounded  (route, status)        -> 4 series
      ('/a', '200')
      ('/a', '500')
      ('/b', '200')
      ('/b', '500')
  unbounded (route, status, user) -> 8 series
      ('/a', '200', 'u1')
      ('/a', '200', 'u2')
      ('/a', '200', 'u3')
      ('/a', '500', 'u3')
      ('/b', '200', 'u1')
      ('/b', '200', 'u4')
      ('/b', '500', 'u2')
      ('/b', '500', 'u5')
----------------------------------------------------------------
  adding the user label multiplies 4 series into 8.
```

Four series become eight on the same eight events — and eight is only where it sits now, with five users. The `(/a, 200)` bucket alone split into three series because three different users hit it.

<svg role="img" aria-label="The bounded route-status bucket for /a 200 splits into three separate series when user is added as a label" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="20" fill="var(--muted)" font-size="9">bounded: one bucket</text>
  <rect x="10" y="28" width="120" height="20" fill="var(--s2)"/>
  <text x="20" y="42" fill="var(--panel)" font-size="9">(/a, 200)</text>
  <text x="150" y="42" fill="var(--muted)" font-size="14">→</text>
  <text x="175" y="20" fill="var(--muted)" font-size="9">+ user: three series</text>
  <rect x="175" y="28" width="110" height="16" fill="var(--s1)"/>
  <text x="182" y="40" fill="var(--panel)" font-size="8">(/a, 200, u1)</text>
  <rect x="175" y="48" width="110" height="16" fill="var(--s1)"/>
  <text x="182" y="60" fill="var(--panel)" font-size="8">(/a, 200, u2)</text>
  <rect x="175" y="68" width="110" height="16" fill="var(--s1)"/>
  <text x="182" y="80" fill="var(--panel)" font-size="8">(/a, 200, u3)</text>
  <text x="10" y="108" fill="var(--muted)" font-size="8">one bounded bucket fans out into one series per user who hit it</text>
</svg>
^ Adding the user label does not annotate the existing bucket — it shatters it into one series per user, and the shards multiply with every new user.

## Build

The `--ceiling` view shows where this goes: not the eight series observed now, but the ceiling the scheme can reach.

```text filename=--ceiling
CEILING — cardinality ceiling = product of label value counts
----------------------------------------------------------------
  routes=2  statuses=2  users=5
  bounded  (route, status)        ceiling 4
  unbounded (route, status, user) ceiling 20
----------------------------------------------------------------
  the user label multiplies the ceiling by the user count.
```

The bounded ceiling is 2 × 2 = 4 — and it never moves, because routes and statuses are fixed. The unbounded ceiling is 2 × 2 × 5 = 20, five times larger, and the 5 is the user count. Ship this and the ceiling tracks your user base: ten thousand users is forty thousand series for one counter.

<svg role="img" aria-label="Bounded ceiling stays flat at 4 as users grow; unbounded ceiling rises linearly with user count" viewBox="0 0 300 140" width="300" height="140">
  <line x1="35" y1="15" x2="35" y2="115" stroke="var(--grid)" stroke-width="1"/>
  <line x1="35" y1="115" x2="285" y2="115" stroke="var(--grid)" stroke-width="1"/>
  <text x="5" y="115" fill="var(--muted)" font-size="8">0</text>
  <line x1="35" y1="108" x2="285" y2="108" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="240" y="104" fill="var(--s2)" font-size="8">bounded (4)</text>
  <line x1="35" y1="112" x2="285" y2="25" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="200" y="35" fill="var(--s1)" font-size="8">unbounded ∝ users</text>
  <text x="120" y="132" fill="var(--muted)" font-size="8">number of users →</text>
</svg>
^ As the user base grows, the bounded scheme's series count is flat; the unbounded scheme's rises without bound — that slope is the outage waiting to happen.

## Definition of done

The self-test pins the multiplication: the bounded scheme stays at or under routes×statuses, adding user creates strictly more series, the ceiling equals the product of cardinalities, user is the high-cardinality label, and the user label scales the ceiling by the user count.

```python filename=modules/ship-and-operate/code/ship-inter-17/cardinality.py:98-113 COMPLETE
    bounded_capped = len(b) <= routes * statuses
    print("  the bounded scheme stays at or under routes*statuses = %s (%d <= %d)" % (bounded_capped, len(b), routes * statuses))

    unbounded_exceeds = len(u) > len(b)
    print("  adding user_id creates more series = %s (%d vs %d)" % (unbounded_exceeds, len(u), len(b)))

    ceiling_is_product = ceiling(events, UNBOUNDED) == routes * statuses * users
    print("  the ceiling is the product of label cardinalities = %s (%d*%d*%d = %d)"
          % (ceiling_is_product, routes, statuses, users, ceiling(events, UNBOUNDED)))

    user_is_high_cardinality = users > routes and users > statuses
    print("  user is the high-cardinality label = %s (users %d vs routes %d, statuses %d)"
          % (user_is_high_cardinality, users, routes, statuses))

    unbounded_ceiling_scales = ceiling(events, UNBOUNDED) == ceiling(events, BOUNDED) * users
    print("  the user label scales the ceiling by the user count = %s (%d = %d * %d)"
          % (unbounded_ceiling_scales, ceiling(events, UNBOUNDED), ceiling(events, BOUNDED), users))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the bounded scheme stays capped; adding user_id multiplies the series count
------------------------------------------------------------------------------------------------
  the bounded scheme stays at or under routes*statuses = True (4 <= 4)
  adding user_id creates more series = True (8 vs 4)
  the ceiling is the product of label cardinalities = True (2*2*5 = 20)
  user is the high-cardinality label = True (users 5 vs routes 2, statuses 2)
  the user label scales the ceiling by the user count = True (20 = 4 * 5)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  bounded_capped=True  unbounded_exceeds=True  ceiling_is_product=True  user_is_high_cardinality=True  unbounded_ceiling_scales=True
```

**Done means the explosion is quantified, not hand-waved: the ceiling is exactly routes×statuses×users, so the user factor is a multiplier on the whole metric, not an addition to it.**

## Boss fight

The ceiling here is 20 — small. Predict whether that means adding user_id is safe on this service. It is tempting to say yes: 20 series is nothing.

That reasoning is the trap, because the ceiling is a product and this fixture has five users. Cardinality scales with the actual cardinality of each label in production, not in the toy. Swap the 5 users for a real user base and the same code path produces `2 × 2 × N` series for one counter; a service with a million users emits four million series from a single labeled metric. Worse, unbounded labels are often correlated with other unbounded labels — add both `user` and `request_id` and the product is users times requests, which is effectively unbounded. The lesson is to read the ceiling formula, not the current count: any label whose value set grows with traffic makes the product grow with traffic.

The mirror-image mistake is over-correcting into uselessly coarse metrics — dropping `status` because "labels are dangerous." Bounded labels are cheap and essential; the discipline is not "few labels" but "no unbounded labels." Keep route and status; send user and request id to traces.

```python filename=modules/ship-and-operate/code/ship-inter-17/cardinality.py:51-56 COMPLETE
def ceiling(events, labels):
    """The cardinality ceiling: the product of each label's distinct value count."""
    prod = 1
    for k in labels:
        prod *= distinct(events, k)
    return prod
```

**Judge a label by the size of its value set, not by how useful the breakdown looks: a bounded label is free forever, an unbounded one multiplies your whole metric by your traffic.**

## External resources

The Prometheus documentation on labels and "Cardinality is key" — the explicit warning that every unique label-value combination is a new time series, and identifiers must not be labels.

Google's "Site Reliability Engineering", the monitoring chapter — why metrics are for aggregate signals and logs/traces are for high-cardinality detail, the division this module rests on.

Grafana Labs and Honeycomb write-ups on "high cardinality" — the trace/observability side, where per-user and per-request detail belongs, indexed for exactly the cardinality metrics cannot hold.
