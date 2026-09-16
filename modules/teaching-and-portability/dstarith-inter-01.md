---
id: dstarith-inter-01
title: Add a calendar day, not 86400 seconds — across a daylight-saving transition a local day is 23 or 25 hours, so fixed-second arithmetic drifts the wall-clock time
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: Two different things are called "a day." A calendar day is a unit of local time — midnight to midnight in some zone. A fixed 86400 seconds is a unit of elapsed physical time. They are equal only while the zone's offset holds still, and it moves twice a year: on the spring-forward date the clocks jump from 2:00 straight to 3:00, so that local day contains only 23 hours of real time, and on the fall-back date it contains 25. Code that schedules "the same time tomorrow" almost always implements it as "86400 seconds later" by adding a fixed duration to a stored instant — which is "exactly 24 hours later," the wrong thing on a transition day. On the fixture a 9:00 daily alarm is scheduled across a spring-forward between day 1 and day 2 (offset −8 to −7): the naive add-86400 alarm fires at 9:00 through day 1, then drifts to 10:00 on day 2 and stays there, because 24 hours after 9:00 on the short day is 10:00 and each later day keeps adding to the drifted instant. The fix is to do the arithmetic in the unit the user meant — attach the target wall-clock time to each day in the zone and convert to an instant using that day's offset — which fires at 9:00 every day and quietly absorbs the missing hour into the real-time gap between firings (23 real hours across the transition). The rule: a recurring local time is calendar arithmetic, not a fixed number of seconds, because a local day is not always 86400 seconds long.
eli5: Say you want your alarm to go off at 9 o'clock every morning, and you set it by telling a stopwatch "ring 24 hours after the last ring." That works until the night the clocks spring forward and everyone loses an hour of sleep. On that night, 24 hours after 9:00 is not 9:00 anymore — it's 10:00, because an hour got skipped — so your alarm now rings at 10 and keeps ringing at 10 every day after. The clock on the wall moved but your stopwatch didn't know. The right way is to say "ring at 9 o'clock tomorrow" and let the calendar figure out how many hours that actually is — sometimes 23, sometimes 25 — so the alarm always matches the wall clock.
---

## Why this module

"Do this again tomorrow at the same time" sounds like the simplest scheduling request there is, and the simplest implementation is to remember when it last ran and add a day's worth of seconds. It passes every test you are likely to write, because on almost every day of the year a day really is 86400 seconds, and the alarm fires exactly when it should.

Twice a year it is wrong, and it is wrong in a way that then sticks. On the day a zone changes its clocks, the local day is not 86400 seconds long — it is 23 hours on the spring-forward date, 25 on the fall-back date. Add a fixed 86400 seconds across that boundary and you land an hour off the wall-clock time the user asked for, and because tomorrow's alarm is built by adding another 86400 to today's drifted one, the error does not correct itself. The 9:00 alarm becomes a 10:00 alarm, permanently.

This module schedules a daily 9:00 alarm across a spring-forward and measures where it actually fires, both ways. The fixed-seconds schedule drifts to 10:00 and stays; the calendar schedule holds 9:00 every day and absorbs the short day into the physical gap between firings. Then it shows the split between the two meanings of "a day" that causes it.

**"The same time tomorrow" is a statement about the wall clock, and adding a fixed number of seconds answers a different question — how much physical time elapses — which only matches the wall clock on days the offset does not move.**

## Concepts

Separate the two clocks cleanly. Physical time is the steady count of seconds that never skips; a duration like 86400 seconds is measured on it. Local wall-clock time is what a clock on the wall in some zone reads, and it is physical time plus the zone's current offset from UTC. The offset is not a constant — daylight saving shifts it, forward in spring and back in autumn.

A calendar day means "the same wall-clock time, one date later." Its length in physical seconds depends on whether the offset changed in between. On an ordinary day the offset is unchanged, so a calendar day is 86400 seconds. On the spring-forward day the offset jumps ahead an hour — the clocks skip from 2:00 to 3:00 — so getting from 9:00 one day to 9:00 the next takes only 23 hours of real time. On the fall-back day the offset drops an hour and the same step takes 25.

Now the bug is one line of algebra. Adding 86400 seconds moves you exactly 24 hours of physical time. On the spring-forward day, 24 hours of physical time after 9:00 local is 10:00 local, because an hour of wall-clock time was skipped and your fixed duration does not know it. You asked for the next 9:00 and the arithmetic gave you the instant 24 physical hours later, which is a different wall-clock time.

The figure shows the transition day compressed: the local calendar runs midnight to midnight as always, but the physical time it spans is an hour short.

<svg role="img" aria-label="A timeline of local wall-clock hours across the spring-forward day; the hours run normally but between 2 and 3 the clock jumps, so the physical span of the day is 23 hours instead of 24, marked by a gap where the skipped hour would be" viewBox="0 0 640 200">
<line x1="40" y1="90" x2="600" y2="90" stroke="var(--line)" stroke-width="1"/>
<text x="40" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">0:00</text>
<text x="150" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">2:00</text>
<line x1="150" y1="78" x2="150" y2="102" stroke="var(--s2)" stroke-width="1.5"/>
<text x="230" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">3:00</text>
<line x1="230" y1="78" x2="230" y2="102" stroke="var(--s2)" stroke-width="1.5"/>
<path d="M 150 90 q 40 -34 80 0" fill="none" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="4 3"/>
<text x="190" y="48" fill="var(--s2)" font-size="10" text-anchor="middle">2→3 skipped</text>
<text x="600" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">24:00</text>
<text x="320" y="160" fill="var(--ink)" font-size="12" text-anchor="middle">the wall clock covers 0:00→24:00, but only 23 physical hours pass</text>
</svg>
^ The spring-forward day still runs midnight to midnight on the wall clock, but the skipped hour means it is 23 hours of real time — so "+86400s" overshoots the next day's wall-clock time.

**A calendar day and 86400 seconds are the same length only when the offset holds still; the transition day is where they differ, and it is exactly the day a fixed-seconds schedule gets wrong.**

## Worked example

The fixture is a 9:00 daily alarm scheduled across a spring-forward, with the zone modeled explicitly so nothing depends on a system timezone database.

```json filename=modules/teaching-and-portability/code/dstarith-inter-01/dstarith.json:3-7 COMPLETE
  "target_local_hour": 9,
  "num_days": 4,
  "dst_after_day": 1,
  "offset_before_hours": -8,
  "offset_after_hours": -7
```

The zone is one function: its offset is `offset_before_hours` up to the transition day and `offset_after_hours` after it — the step that makes the transition day short.

```python filename=modules/teaching-and-portability/code/dstarith-inter-01/dstarith.py:33-36 COMPLETE
def offset(data, day):
    """The zone's UTC offset (seconds) on a given local day -- it steps at the DST transition."""
    hrs = data["offset_before_hours"] if day <= data["dst_after_day"] else data["offset_after_hours"]
    return hrs * HOUR
```

The correct instant for the target time on a given day attaches the wall-clock hour to that day and converts using that day's offset.

```python filename=modules/teaching-and-portability/code/dstarith-inter-01/dstarith.py:39-42 COMPLETE
def calendar_alarm_utc(data, day):
    """The absolute instant of target_local_hour on this local day: local time minus that day's offset."""
    local_abs = day * DAY + data["target_local_hour"] * HOUR
    return local_abs - offset(data, day)          # utc = local - offset, using THIS day's offset
```

The buggy schedule computes the first day's instant once and then adds a fixed 86400 seconds per day.

```python filename=modules/teaching-and-portability/code/dstarith-inter-01/dstarith.py:50-53 COMPLETE
def naive_alarm_utc(data, day):
    """The add-86400 schedule: fix the first day's instant, then add a fixed 24 hours per day."""
    first = calendar_alarm_utc(data, 0)
    return first + day * DAY                        # 'same time tomorrow' == +86400s, every day
```

Running it prints where the alarm actually fires on the wall clock each day.

```text filename=dstarith.py --naive
NAIVE — schedule by adding 86400 seconds each day
------------------------------------------------------------
  target: 09:00 local every day; spring-forward after day 1
    day 0: fires at 09.00 local
    day 1: fires at 09.00 local
    day 2: fires at 10.00 local  <- DRIFTED
    day 3: fires at 10.00 local  <- DRIFTED
------------------------------------------------------------
  after the transition the alarm fires an hour late and stays there
```

Days 0 and 1 fire at 9:00; from day 2 on it fires at 10:00 and never recovers. The calendar schedule recomputes 9:00 for each day in the zone instead.

```text filename=dstarith.py --calendar
CALENDAR — schedule by attaching the target time to each day in the zone
------------------------------------------------------------
  target: 09:00 local every day; spring-forward after day 1
    day 0: fires at 09.00 local
    day 1: fires at 09.00 local  (24 real hours since yesterday)
    day 2: fires at 09.00 local  (23 real hours since yesterday)
    day 3: fires at 09.00 local  (24 real hours since yesterday)
------------------------------------------------------------
  9:00 every day; the short 23-hour day is absorbed into the real-time gap, not the wall clock
```

Every day fires at 9:00, and the transition shows up where it belongs — in the physical gap, which is 23 hours across the spring-forward, not in the wall-clock time. The figure traces both schedules' firing hour across the four days.

<svg role="img" aria-label="A chart of the alarm's local firing hour over four days; the calendar schedule stays flat at 9 every day, while the naive schedule sits at 9 for days 0 and 1 then steps up to 10 for days 2 and 3 after the transition" viewBox="0 0 640 240">
<line x1="60" y1="200" x2="600" y2="200" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="40" x2="60" y2="200" stroke="var(--line)" stroke-width="1"/>
<text x="44" y="84" fill="var(--muted)" font-size="10" text-anchor="end">10:00</text>
<text x="44" y="144" fill="var(--muted)" font-size="10" text-anchor="end">9:00</text>
<line x1="60" y1="140" x2="600" y2="140" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<line x1="255" y1="40" x2="255" y2="200" stroke="var(--s2)" stroke-width="1" stroke-dasharray="4 3"/>
<text x="255" y="30" fill="var(--s2)" font-size="10" text-anchor="middle">spring forward</text>
<polyline points="130,140 250,140 380,80 500,80" fill="none" stroke="var(--s2)" stroke-width="2"/>
<circle cx="130" cy="140" r="4" fill="var(--s2)"/>
<circle cx="250" cy="140" r="4" fill="var(--s2)"/>
<circle cx="380" cy="80" r="4" fill="var(--s2)"/>
<circle cx="500" cy="80" r="4" fill="var(--s2)"/>
<text x="440" y="72" fill="var(--s2)" font-size="10">naive: drifts to 10:00</text>
<polyline points="130,140 250,140 380,140 500,140" fill="none" stroke="var(--s1)" stroke-width="2" stroke-dasharray="6 3"/>
<text x="300" y="158" fill="var(--s1)" font-size="10">calendar: holds 9:00</text>
<text x="130" y="218" fill="var(--muted)" font-size="10" text-anchor="middle">day 0</text>
<text x="250" y="218" fill="var(--muted)" font-size="10" text-anchor="middle">day 1</text>
<text x="380" y="218" fill="var(--muted)" font-size="10" text-anchor="middle">day 2</text>
<text x="500" y="218" fill="var(--muted)" font-size="10" text-anchor="middle">day 3</text>
</svg>
^ The two schedules agree until the transition, then the fixed-seconds one steps permanently to 10:00 while the calendar one stays at 9:00.

**The drift is not a one-day glitch that heals — because each day is built by adding 86400 to the previous drifted instant, the hour lost at the transition is carried forward forever.**

## Build

The self-test ties the drift to its cause. It confirms the naive alarm is correct before the transition and off by exactly the offset change after it — one hour, the size of the DST step.

```python filename=modules/teaching-and-portability/code/dstarith-inter-01/dstarith.py:93-99 COMPLETE
    naive_before = local_hour(data, naive_alarm_utc(data, 0), 0)
    naive_matches_before_dst = abs(naive_before - target) < 1e-9
    print("  before the transition the naive alarm is on target = %s (%05.2f)" % (naive_matches_before_dst, naive_before))

    naive_after = local_hour(data, naive_alarm_utc(data, after), after)
    naive_drifts_after_dst = abs(naive_after - target) > 1e-9
    print("  after the transition the naive alarm has drifted = %s (%05.2f, not %02d:00)" % (naive_drifts_after_dst, naive_after, target))
```

The other flags confirm the transition day really is 82800 seconds and that the calendar schedule holds the target every day. All five pass.

```text filename=dstarith.py --check
SELF-TEST — the transition day is not 86400 seconds, the naive alarm drifts by exactly the offset change, and the calendar alarm holds the target
----------------------------------------------------------------------------------------------------------------
  the local day spanning the transition is not 86400 s = True (82800 s = 23 h)
  before the transition the naive alarm is on target = True (09.00)
  after the transition the naive alarm has drifted = True (10.00, not 09:00)
  the drift equals the offset change = True (1.00 h == 1.00 h)
  the calendar alarm fires on target every day = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  transition_day_not_86400=True  naive_matches_before_dst=True  naive_drifts_after_dst=True  drift_equals_offset_change=True  calendar_holds=True
```

**The drift being exactly the offset change is the proof: the alarm did not wander for some incidental reason, it moved by precisely the hour the zone's clocks moved, because a fixed duration cannot follow a wall clock that jumped.**

## Definition of done

You are done when any "repeat at this local time" or "N days later at the same time" logic is computed as calendar arithmetic in a real timezone, and a fixed number of seconds is used only when you genuinely mean a fixed elapsed duration.

The test that separates the two is the question you are actually answering. "The same wall-clock time on a later date" — a recurring alarm, a daily report, a billing date — is calendar arithmetic: build the target local date-time in the zone and let the library resolve it to an instant, so it absorbs the 23- or 25-hour days. "Exactly this much time from now" — a token that expires in 3600 seconds, a 30-second timeout — is an elapsed duration, and adding seconds is right. The bug is using the second to implement the first. In practice you reach for a real timezone (an IANA zone via your language's date-time library), add a `timedelta(days=1)` in that zone rather than `timedelta(seconds=86400)`, and handle the two DST edge cases the library surfaces: a local time that does not exist (the skipped hour) and one that exists twice (the repeated hour).

<svg role="img" aria-label="A decision split: the question same wall-clock time on a later date routes to calendar arithmetic in the zone, and the question a fixed elapsed duration routes to adding seconds" viewBox="0 0 640 210">
<text x="320" y="28" fill="var(--muted)" font-size="12" text-anchor="middle">what are you adding?</text>
<text x="175" y="66" fill="var(--ink)" font-size="11" text-anchor="middle">"same time, later date"</text>
<line x1="175" y1="76" x2="175" y2="116" stroke="var(--line)" stroke-width="1"/>
<polygon points="175,116 170,106 180,106" fill="var(--line)"/>
<rect x="70" y="118" width="210" height="58" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="175" y="143" fill="var(--ink)" font-size="11" text-anchor="middle">calendar arithmetic in zone</text>
<text x="175" y="160" fill="var(--muted)" font-size="10" text-anchor="middle">timedelta(days=1), resolve to instant</text>
<text x="470" y="66" fill="var(--ink)" font-size="11" text-anchor="middle">"a fixed elapsed span"</text>
<line x1="470" y1="76" x2="470" y2="116" stroke="var(--line)" stroke-width="1"/>
<polygon points="470,116 465,106 475,106" fill="var(--line)"/>
<rect x="365" y="118" width="210" height="58" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="470" y="143" fill="var(--ink)" font-size="11" text-anchor="middle">add seconds</text>
<text x="470" y="160" fill="var(--muted)" font-size="10" text-anchor="middle">timeouts, TTLs, elapsed</text>
</svg>
^ Route by intent: a wall-clock time on a later date is calendar arithmetic; a fixed span is seconds — and the bug is using seconds for the first.

**Storing timestamps in UTC keeps instants comparable, but it does not save you here — the moment you need "9:00 local tomorrow," you must do the arithmetic in the zone, because that question lives on the wall clock the UTC instant deliberately forgot.**

## Boss fight

Your turn: flip the transition to a fall-back and predict the sign of the drift. Set `offset_after_hours` to `-9` (the offset drops an hour instead of rising) and rerun `--naive`. Now the transition day is 25 hours long, so 24 fixed hours falls an hour short of the next 9:00, and the naive alarm drifts to 8:00 — early, not late. The self-test still passes because `drift_equals_offset_change` tracks the signed offset step, now −1 hour. Fixed-second arithmetic drifts in whichever direction the clocks moved, and by exactly that much.

Then find the case the calendar approach itself has to make a decision about. Set the target hour to 2 and keep the spring-forward — you are asking for 2:00 local on a day when 2:00 does not exist, because the clocks jump from 2:00 to 3:00. There is no instant that reads 2:00 local that day. A real date-time library will either raise, or apply a documented rule (shift forward to 3:00, or pick the pre-transition offset), and you must choose which is right for your use — an alarm probably wants to fire at 3:00, a billing job might want to skip. This is the genuine hard part that fixed-second arithmetic hides entirely: it never notices the hour does not exist, it just silently lands somewhere. Calendar arithmetic forces the ambiguity into the open, which is exactly where you want it.

**The fixed-seconds schedule never asks whether the target time exists or is unique, so it fails silently; calendar arithmetic makes the skipped and repeated hours into explicit decisions, which is the whole reason to prefer it even though it is more work.**

## External resources

Your language's date-time library documentation on DST handling — Python's `zoneinfo` and `datetime` arithmetic, Java's `java.time` with `ZonedDateTime`, or JavaScript's `Temporal` — each states how adding a calendar unit differs from adding a duration and how it resolves skipped and repeated local times.

The IANA time zone database (tz) is where the actual transition dates and offsets come from; understanding that offsets are data that changes, not constants, is the foundation of why fixed-second arithmetic cannot be right in general.

Jon Skeet's writing on date and time handling catalogs this class of bug — "a day is not 86400 seconds," skipped and ambiguous local times — and is the standard practitioner reference for why calendar arithmetic must run in a real zone.
