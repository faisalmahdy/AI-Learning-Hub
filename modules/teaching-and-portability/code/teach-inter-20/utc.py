"""Store timestamps in UTC, or a naive wall-clock time gets the order and duration wrong across timezones.

A timestamp that records only the wall-clock time -- "14:00" -- and forgets which timezone it was 14:00 IN is
ambiguous: it names a different instant on a machine in Berlin than on one in New York. As long as everything
runs in one timezone the ambiguity is invisible. The moment two machines in different zones log events into the
same store, comparing the stored numbers compares clocks that were never the same. "14:00" on a UTC+2 machine
is actually 12:00 UTC; "13:00" on a UTC-1 machine is 14:00 UTC -- so the event that reads LATER on the wall
clock actually happened EARLIER. Order events by the naive number and you reverse them; subtract them and you
get the wrong duration. The data looks fine; the timezone it was in is just missing.

Storing UTC fixes it. Convert every timestamp to UTC (subtract the offset) before storing, so each is an
absolute instant that means the same thing on every machine. Now ordering, subtracting, and comparing all work,
because every timestamp is on one universal clock. The rule is: record instants in UTC (or with an explicit
offset), and convert to a local timezone only for display. A naive local timestamp is not a smaller version of
a UTC one; it is a broken one, missing the piece that makes it comparable.

On this fixture event A is logged 14:00 at UTC+2 and event B 13:00 at UTC-1. By the stored wall-clock hour A
(14) is after B (13). In real time A is 12:00 UTC and B is 14:00 UTC, so A is actually two hours BEFORE B --
the naive order is reversed and the naive duration (1h) is wrong (it is 2h). This computes both.

  --instants   each event's naive wall-clock hour and its true UTC hour
  --order      the event order by naive time vs by UTC, and the duration each gives
  --check      the naive order and duration are wrong; the UTC ones are right

The events are the fixture; every UTC time is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "events.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def utc_hour(e):
    """The absolute instant: local wall-clock hour minus the machine's UTC offset."""
    return e["local_hour"] - e["utc_offset"]


def order_by(events, key):
    return [e["name"] for e in sorted(events, key=key)]


def duration(events, key):
    vals = [key(e) for e in events]
    return abs(vals[0] - vals[1])


# ----------------------------------------------------------------- printing

def instants_view(data):
    print("INSTANTS — naive wall-clock hour vs true UTC hour")
    print("-" * 58)
    print("  event   local   offset   UTC hour")
    for e in data["events"]:
        print("  %-5s   %2d:00   %+d       %2d:00" % (e["name"], e["local_hour"], e["utc_offset"], utc_hour(e)))
    print("-" * 58)
    print("  the wall-clock hour hides the offset; the UTC hour is absolute.")


def order_view(data):
    events = data["events"]
    naive_order = order_by(events, lambda e: e["local_hour"])
    utc_order = order_by(events, utc_hour)
    print("ORDER — event order and duration by naive time vs UTC")
    print("-" * 58)
    print("  by naive wall clock: %s   duration %d h" % (" then ".join(naive_order), duration(events, lambda e: e["local_hour"])))
    print("  by UTC (true):       %s   duration %d h" % (" then ".join(utc_order), duration(events, utc_hour)))
    print("-" * 58)
    print("  the naive order is reversed and its duration is wrong.")


def check(data):
    print("SELF-TEST — the naive order and duration are wrong; the UTC ones are right")
    print("-" * 96)
    events = data["events"]
    naive_order = order_by(events, lambda e: e["local_hour"])
    utc_order = order_by(events, utc_hour)
    naive_dur = duration(events, lambda e: e["local_hour"])
    utc_dur = duration(events, utc_hour)

    utc_is_local_minus_offset = all(utc_hour(e) == e["local_hour"] - e["utc_offset"] for e in events)
    print("  the UTC hour is local_hour - utc_offset = %s" % utc_is_local_minus_offset)

    offsets_differ = events[0]["utc_offset"] != events[1]["utc_offset"]
    print("  the two events were logged in different timezones = %s (%+d vs %+d)" % (offsets_differ, events[0]["utc_offset"], events[1]["utc_offset"]))

    naive_order_reversed = naive_order != utc_order
    print("  the naive wall-clock order differs from the true UTC order = %s (%s vs %s)" % (naive_order_reversed, naive_order, utc_order))

    naive_duration_wrong = naive_dur != utc_dur
    print("  the naive duration differs from the true duration = %s (%d h vs %d h)" % (naive_duration_wrong, naive_dur, utc_dur))

    naive_looks_later_is_earlier = events[0]["local_hour"] > events[1]["local_hour"] and utc_hour(events[0]) < utc_hour(events[1])
    print("  the event that reads later actually happened earlier = %s" % naive_looks_later_is_earlier)

    ok = utc_is_local_minus_offset and offsets_differ and naive_order_reversed and naive_duration_wrong and naive_looks_later_is_earlier
    print("-" * 96)
    print("SELF-TEST %s  utc_is_local_minus_offset=%s  offsets_differ=%s  naive_order_reversed=%s  naive_duration_wrong=%s  naive_looks_later_is_earlier=%s"
          % ("PASS" if ok else "FAIL", utc_is_local_minus_offset, offsets_differ, naive_order_reversed, naive_duration_wrong, naive_looks_later_is_earlier))
    return ok


def main():
    p = argparse.ArgumentParser(description="Store timestamps in UTC so ordering and durations are correct across timezones.")
    p.add_argument("--instants", action="store_true")
    p.add_argument("--order", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("events=%d  file=%s  (the events are a fixture)" % (len(data["events"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.instants:
        instants_view(data)
    elif args.order:
        order_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
