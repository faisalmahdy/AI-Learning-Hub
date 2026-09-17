"""Keep metric labels bounded, or one user_id label turns a 4-series counter into one series per user.

A metrics backend does not store "a counter." It stores one independent time series for every distinct
combination of label values that has ever appeared. A request counter labeled by route and status is a
handful of series -- routes times statuses -- and its memory footprint is flat no matter how much traffic
you take. The obvious enhancement is fatal: "let me add user_id so I can slice by user." Now the counter
has one series per (route, status, user), and the series count grows with your user base. A backend like
Prometheus holds every active series in memory; a high-cardinality label is not a bigger number in a cell,
it is a multiplication of the whole table. Dashboards slow, the scrape balloons, and eventually the backend
falls over -- from a metric that looked like a one-line improvement.

The rule is that a label's value set must be bounded and small: route, status, method, region -- things with
a handful of values known ahead of time. Identifiers -- user, request, session, email, full URL with query
-- are unbounded and belong in logs or traces, which are indexed for high cardinality, not in metric labels.
Total cardinality is the PRODUCT of each label's distinct values, so one unbounded label dominates every
bounded one it is multiplied against.

On this fixture eight events span 2 routes, 2 statuses, and 5 users. Labeling by (route, status) creates 4
series and stays capped at routes*statuses no matter how many users arrive. Adding user makes it
(route, status, user): 8 series already, and its ceiling is 2*2*5 = 20 -- five times larger, and the 5 is
your user count, which only grows. This computes both.

  --series     the distinct time series each labeling scheme creates, listed
  --ceiling    the cardinality ceiling (product of label value counts) for each scheme
  --check      the bounded scheme stays capped; adding user_id multiplies the series count

The event stream is the fixture; every series count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "metrics.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


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


# ----------------------------------------------------------------- printing

BOUNDED = ["route", "status"]
UNBOUNDED = ["route", "status", "user"]


def series_view(data):
    events = data["events"]
    b, u = series(events, BOUNDED), series(events, UNBOUNDED)
    print("SERIES — distinct time series per labeling scheme (%d events)" % len(events))
    print("-" * 64)
    print("  bounded  (route, status)        -> %d series" % len(b))
    for s in b:
        print("      %s" % (s,))
    print("  unbounded (route, status, user) -> %d series" % len(u))
    for s in u:
        print("      %s" % (s,))
    print("-" * 64)
    print("  adding the user label multiplies %d series into %d." % (len(b), len(u)))


def ceiling_view(data):
    events = data["events"]
    print("CEILING — cardinality ceiling = product of label value counts")
    print("-" * 64)
    print("  routes=%d  statuses=%d  users=%d" % (distinct(events, "route"), distinct(events, "status"), distinct(events, "user")))
    print("  bounded  (route, status)        ceiling %d" % ceiling(events, BOUNDED))
    print("  unbounded (route, status, user) ceiling %d" % ceiling(events, UNBOUNDED))
    print("-" * 64)
    print("  the user label multiplies the ceiling by the user count.")


def check(data):
    print("SELF-TEST — the bounded scheme stays capped; adding user_id multiplies the series count")
    print("-" * 96)
    events = data["events"]
    b, u = series(events, BOUNDED), series(events, UNBOUNDED)
    routes, statuses, users = distinct(events, "route"), distinct(events, "status"), distinct(events, "user")

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

    ok = bounded_capped and unbounded_exceeds and ceiling_is_product and user_is_high_cardinality and unbounded_ceiling_scales
    print("-" * 96)
    print("SELF-TEST %s  bounded_capped=%s  unbounded_exceeds=%s  ceiling_is_product=%s  user_is_high_cardinality=%s  unbounded_ceiling_scales=%s"
          % ("PASS" if ok else "FAIL", bounded_capped, unbounded_exceeds, ceiling_is_product, user_is_high_cardinality, unbounded_ceiling_scales))
    return ok


def main():
    p = argparse.ArgumentParser(description="Keep metric labels bounded so the time-series count does not explode.")
    p.add_argument("--series", action="store_true")
    p.add_argument("--ceiling", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("events=%d  routes=%d  statuses=%d  users=%d  file=%s  (the event stream is a fixture)"
          % (len(data["events"]), distinct(data["events"], "route"), distinct(data["events"], "status"),
             distinct(data["events"], "user"), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.series:
        series_view(data)
    elif args.ceiling:
        ceiling_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
