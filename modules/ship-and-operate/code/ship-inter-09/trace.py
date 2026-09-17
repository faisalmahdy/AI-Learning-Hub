"""Stamp every log line with a correlation id -- or concurrent requests interleave into a jumble.

A service handles many requests at once, and each one emits log lines as it moves through its
steps -- start, query, done. Those lines all land in one log stream, interleaved, because the
requests run concurrently. Without a correlation id on each line you cannot tell which 'query'
belongs to which request; the log is a pile of steps with no way to reassemble any single
request's path. The naive attempt -- assume the lines are in request order and chunk them --
mis-attributes steps across requests, reconstructing paths that never happened (two starts, no
done) because it stitched one request's start to another's query.

A correlation id fixes it for free: generate an id per request and stamp it on every line that
request emits, then propagate it to downstream services so the whole distributed path shares
one id. Now reconstructing a request is a filter: keep the lines with its id, in time order,
and you have its exact path. On this fixture three requests interleave in the log; filtering by
id recovers all three exact paths, while chunking the id-stripped log reconstructs zero valid
requests. This builds both and shows the jumble become traceable.

  --log        the interleaved log, with and without correlation ids
  --trace      reconstruct each request by id-filter vs by naive consecutive chunking
  --check      correlation ids recover every request's exact path; chunking recovers none

The log events are the fixture; every reconstruction is computed. Deterministic; stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "log.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- reconstruction

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


def is_valid_path(path, expected):
    """A real request follows the expected step sequence exactly."""
    return path == expected


# ----------------------------------------------------------------- printing

def log_view(data):
    events = sorted(data["events"], key=lambda e: e["t"])
    print("LOG — the interleaved stream (requests run concurrently)")
    print("-" * 54)
    print("  t   with correlation id       without id")
    for e in events:
        print("  %-3d [%s] %-10s        %s" % (e["t"], e["id"], e["step"], e["step"]))
    print("-" * 54)
    print("  the same step name appears for every request -- only the id tells them apart.")


def trace_view(data):
    events = data["events"]
    expected = data["expected_path"]
    corr = by_correlation_id(events)
    naive = by_naive_chunking(events, len(expected))
    print("TRACE — reconstruct each request's path")
    print("-" * 60)
    print("  by correlation id:")
    for rid, path in corr.items():
        print("    %-5s %-28s valid=%s" % (rid, path, is_valid_path(path, expected)))
    print("  by naive chunking (no ids):")
    for i, path in enumerate(naive):
        print("    chunk%d %-27s valid=%s" % (i, path, is_valid_path(path, expected)))
    print("-" * 60)
    print("  id-filtering recovers real paths; chunking stitches steps across requests.")


def check(data):
    print("SELF-TEST — correlation ids recover every request's exact path; chunking recovers none")
    print("-" * 66)
    events = data["events"]
    expected = data["expected_path"]

    corr = by_correlation_id(events)
    corr_all_valid = len(corr) > 0 and all(is_valid_path(p, expected) for p in corr.values())
    print("  every id-filtered path is the exact expected sequence = %s (%d requests)"
          % (corr_all_valid, len(corr)))

    naive = by_naive_chunking(events, len(expected))
    naive_valid = sum(1 for p in naive if is_valid_path(p, expected))
    naive_none_valid = naive_valid == 0
    print("  naive chunking reconstructs ZERO valid requests = %s (%d of %d chunks valid)"
          % (naive_none_valid, naive_valid, len(naive)))

    # requests are genuinely interleaved: at least one request's lines are non-consecutive
    order = [e["id"] for e in sorted(events, key=lambda e: e["t"])]
    interleaved = any(order[i] != order[i + 1] for i in range(len(order) - 1) if order[i] in order[i + 1:])
    print("  the requests are interleaved in the log (not grouped) = %s (%s)" % (interleaved, order))

    # filtering by one id isolates exactly that request's lines
    one = list(corr)[0]
    filtered = [e for e in events if e["id"] == one]
    filter_isolates = all(e["id"] == one for e in filtered) and len(filtered) == len(expected)
    print("  filtering by one id isolates exactly that request = %s (%s: %d lines)"
          % (filter_isolates, one, len(filtered)))

    ok = corr_all_valid and naive_none_valid and interleaved and filter_isolates
    print("-" * 66)
    print("SELF-TEST %s  corr_all_valid=%s  naive_none_valid=%s  interleaved=%s  filter_isolates=%s"
          % ("PASS" if ok else "FAIL", corr_all_valid, naive_none_valid, interleaved, filter_isolates))
    return ok


def main():
    p = argparse.ArgumentParser(description="Stamp a correlation id on every log line.")
    p.add_argument("--log", action="store_true")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    ids = {e["id"] for e in data["events"]}
    print("events=%d  requests=%d  file=%s  (the log stream is a fixture)"
          % (len(data["events"]), len(ids), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.log:
        log_view(data)
    elif args.trace:
        trace_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
