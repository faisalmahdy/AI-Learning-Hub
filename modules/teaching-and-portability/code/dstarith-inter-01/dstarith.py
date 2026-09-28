"""Add a calendar unit, not a fixed number of seconds -- a local day is 23 or 25 hours across a daylight-saving transition, so scheduling 'the same time tomorrow' by adding 86400 seconds drifts an hour off the intended wall-clock time.

Two things are called 'a day' and they are not equal. A calendar day is a unit of local time -- midnight to midnight in some zone. A fixed 86400 seconds is a unit of elapsed physical time. They coincide only when the zone's offset does not change, and it changes twice a year: on the spring-forward date the clocks jump from 2:00 to 3:00, so that local day contains only 23 hours of real time, and on the fall-back date it contains 25.

Code that says 'fire again at the same time tomorrow' almost always implements it as 'fire again 86400 seconds later', by adding a fixed duration to the stored instant. That is 'exactly 24 hours later', which is the wrong thing on a transition day. After a spring-forward, 24 hours after 9:00 is 10:00 -- the alarm has drifted an hour late, and because each subsequent day keeps adding 86400 to the drifted instant, it stays at 10:00 forever. The user set a 9:00 alarm and it now goes off at 10:00.

The fix is to do the arithmetic in the units the user meant. 'The same time tomorrow' is a calendar operation: take tomorrow's date, attach the target wall-clock time in the zone, and convert that to an absolute instant using tomorrow's offset -- not add a fixed elapsed duration. Then the alarm is 9:00 local every day, and the underlying real-time gap between firings is 23 or 25 hours on the transition days, which is exactly correct.

On this fixture a 9:00 daily alarm is scheduled across a spring-forward between day 1 and day 2 (offset goes from -8 to -7). The naive add-86400 alarm fires at 9:00 through day 1 and then at 10:00 from day 2 on; the calendar alarm fires at 9:00 every day. This computes both.

  --naive     the add-86400-seconds alarm: its local firing hour drifts to 10:00 after the transition
  --calendar  the calendar-arithmetic alarm: 9:00 local every day, absorbing the short day in the real-time gap
  --check     the transition day is not 86400 seconds, the naive alarm drifts by exactly the offset change, and the calendar alarm holds the target

the zone offsets, the target hour, and the transition day are the fixture; the alarm instants and their local firing hours are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dstarith.json"

DAY = 86400
HOUR = 3600


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def offset(data, day):
    """The zone's UTC offset (seconds) on a given local day -- it steps at the DST transition."""
    hrs = data["offset_before_hours"] if day <= data["dst_after_day"] else data["offset_after_hours"]
    return hrs * HOUR


def calendar_alarm_utc(data, day):
    """The absolute instant of target_local_hour on this local day: local time minus that day's offset."""
    local_abs = day * DAY + data["target_local_hour"] * HOUR
    return local_abs - offset(data, day)          # utc = local - offset, using THIS day's offset


def local_hour(data, utc, day):
    """The wall-clock hour a UTC instant reads on a given local day."""
    return (utc + offset(data, day) - day * DAY) / HOUR


def naive_alarm_utc(data, day):
    """The add-86400 schedule: fix the first day's instant, then add a fixed 24 hours per day."""
    first = calendar_alarm_utc(data, 0)
    return first + day * DAY                        # 'same time tomorrow' == +86400s, every day


# ----------------------------------------------------------------- printing

def naive_view(data):
    print("NAIVE — schedule by adding 86400 seconds each day")
    print("-" * 60)
    print("  target: %02d:00 local every day; spring-forward after day %d" % (data["target_local_hour"], data["dst_after_day"]))
    for d in range(data["num_days"]):
        utc = naive_alarm_utc(data, d)
        drift = "  <- DRIFTED" if abs(local_hour(data, utc, d) - data["target_local_hour"]) > 1e-9 else ""
        print("    day %d: fires at %05.2f local%s" % (d, local_hour(data, utc, d), drift))
    print("-" * 60)
    print("  after the transition the alarm fires an hour late and stays there")


def calendar_view(data):
    print("CALENDAR — schedule by attaching the target time to each day in the zone")
    print("-" * 60)
    print("  target: %02d:00 local every day; spring-forward after day %d" % (data["target_local_hour"], data["dst_after_day"]))
    for d in range(data["num_days"]):
        utc = calendar_alarm_utc(data, d)
        gap = (utc - calendar_alarm_utc(data, d - 1)) / HOUR if d > 0 else None
        gaptxt = "" if gap is None else "  (%.0f real hours since yesterday)" % gap
        print("    day %d: fires at %05.2f local%s" % (d, local_hour(data, utc, d), gaptxt))
    print("-" * 60)
    print("  9:00 every day; the short 23-hour day is absorbed into the real-time gap, not the wall clock")


def check(data):
    print("SELF-TEST — the transition day is not 86400 seconds, the naive alarm drifts by exactly the offset change, and the calendar alarm holds the target")
    print("-" * 112)
    target = data["target_local_hour"]
    after = data["dst_after_day"] + 1               # first day fully after the transition

    transition_gap = calendar_alarm_utc(data, after) - calendar_alarm_utc(data, after - 1)
    transition_day_not_86400 = transition_gap != DAY
    print("  the local day spanning the transition is not 86400 s = %s (%d s = %.0f h)" % (transition_day_not_86400, transition_gap, transition_gap / HOUR))

    naive_before = local_hour(data, naive_alarm_utc(data, 0), 0)
    naive_matches_before_dst = abs(naive_before - target) < 1e-9
    print("  before the transition the naive alarm is on target = %s (%05.2f)" % (naive_matches_before_dst, naive_before))

    naive_after = local_hour(data, naive_alarm_utc(data, after), after)
    naive_drifts_after_dst = abs(naive_after - target) > 1e-9
    print("  after the transition the naive alarm has drifted = %s (%05.2f, not %02d:00)" % (naive_drifts_after_dst, naive_after, target))

    offset_change_hours = (offset(data, after) - offset(data, 0)) / HOUR
    drift_equals_offset_change = abs((naive_after - target) - offset_change_hours) < 1e-9
    print("  the drift equals the offset change = %s (%.2f h == %.2f h)" % (drift_equals_offset_change, naive_after - target, offset_change_hours))

    calendar_holds = all(abs(local_hour(data, calendar_alarm_utc(data, d), d) - target) < 1e-9 for d in range(data["num_days"]))
    print("  the calendar alarm fires on target every day = %s" % calendar_holds)

    ok = (transition_day_not_86400 and naive_matches_before_dst and naive_drifts_after_dst
          and drift_equals_offset_change and calendar_holds)
    print("-" * 112)
    print("SELF-TEST %s  transition_day_not_86400=%s  naive_matches_before_dst=%s  naive_drifts_after_dst=%s  drift_equals_offset_change=%s  calendar_holds=%s"
          % ("PASS" if ok else "FAIL", transition_day_not_86400, naive_matches_before_dst, naive_drifts_after_dst,
             drift_equals_offset_change, calendar_holds))
    return ok


def main():
    p = argparse.ArgumentParser(description="DST calendar arithmetic: to repeat a local time daily, add a calendar day in the zone and recompute the instant, never add a fixed 86400 seconds, because a local day is 23 or 25 hours across a daylight-saving transition and fixed-second arithmetic drifts off the intended wall-clock time.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--calendar", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("target_local_hour=%d  num_days=%d  dst_after_day=%d  offsets=%d->%d  file=%s  (these are a fixture)"
          % (data["target_local_hour"], data["num_days"], data["dst_after_day"],
             data["offset_before_hours"], data["offset_after_hours"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.calendar:
        calendar_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
