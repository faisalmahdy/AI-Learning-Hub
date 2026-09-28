---
id: teach-inter-20
title: Store timestamps in UTC — or a naive wall-clock time gets the order and duration wrong across timezones
topic: teaching-and-portability
level: intermediate
status: ready
time: 19 min
summary: A timestamp that records only the wall-clock time — "14:00" — and forgets which timezone it was 14:00 in is ambiguous: it names a different instant on a machine in Berlin than in New York. As long as everything runs in one timezone the ambiguity is invisible. The moment two machines in different zones log into the same store, comparing the stored numbers compares clocks that were never the same. "14:00" on a UTC+2 machine is 12:00 UTC; "13:00" on a UTC−1 machine is 14:00 UTC — so the event that reads later on the wall clock actually happened earlier. Order by the naive number and you reverse them; subtract them and you get the wrong duration. Storing UTC fixes it: convert to an absolute instant before storing. On events A (14:00 at UTC+2) and B (13:00 at UTC−1), naive order is B then A with a 1-hour gap; the true UTC order is A then B with a 2-hour gap.
eli5: If one friend says "let's meet at 3" and another says "let's meet at 2" but they're in different time zones, the later-sounding time might actually come first. Clock numbers alone don't tell you when something really happened unless you also know the zone. Converting every time to one shared world clock before writing it down means "earlier" and "later" always mean what they say.
---

## Why this module

A timestamp without its timezone is not a slightly-incomplete timestamp — it is a broken one, because the number alone does not name a moment in time.

Wall-clock time is relative to a zone. "14:00" is a real instant only once you know it is 14:00 in some particular place; the same "14:00" is two different moments in Berlin and New York. A log that stores the bare hour and drops the offset has thrown away the piece that makes the number mean something. Inside a single timezone this is harmless — every timestamp shares the same hidden offset, so comparisons happen to work. Across timezones it breaks silently: two machines in different zones write their local wall-clock times into one store, and now comparing those numbers compares clocks that were never synchronized. An event stamped 14:00 can have happened before one stamped 13:00, and the stored numbers say the opposite.

**A naive wall-clock timestamp is missing its timezone, so comparing or subtracting such timestamps across machines compares numbers that refer to different clocks.**

Storing UTC removes the ambiguity. Convert every timestamp to Coordinated Universal Time — one clock the whole world shares — before storing it, so each stored value is an absolute instant that means the same thing everywhere. Ordering, subtracting, and comparing then all work, because everything is on one timeline. This module logs two events in different zones and shows the naive order and duration come out wrong while the UTC ones are right.

## Concepts

The **local hour** is the wall-clock time on the machine that logged the event. The **UTC offset** is how many hours that machine's zone is ahead of UTC. The **UTC hour** is local_hour − offset — the same instant expressed on the universal clock.

The **naive timestamp** stores only the local hour and forgets the offset. Two naive timestamps can be compared as plain numbers, and that comparison is meaningful *only* if both were logged at the same offset — which you cannot guarantee once more than one machine is involved.

The **absolute instant** is what UTC gives you: a number on a single clock, so "earlier" and "later" are unambiguous and durations are real elapsed time.

The failure has two faces. **Order**: sort by the naive hour and events can come out in the wrong sequence, because a larger wall-clock number in a more-ahead zone can be an earlier instant. **Duration**: subtract two naive hours and you get the gap between wall-clock readings, not the elapsed time — off by the difference in offsets.

**Converting to UTC before storing turns every timestamp into a point on one shared timeline, which is the only condition under which comparing timestamps is valid.**

Each machine reads its own wall clock, but those clocks are shifted from one another; only after subtracting each offset do the readings land on the same shared axis.

<svg role="img" aria-label="Two local clocks offset from each other; subtracting each offset projects both onto one shared UTC timeline" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="16" fill="var(--muted)" font-size="8">two shifted local clocks</text>
  <line x1="20" y1="30" x2="200" y2="30" stroke="var(--s1)" stroke-width="1.5"/><text x="205" y="33" fill="var(--s1)" font-size="7">UTC+2</text>
  <line x1="60" y1="48" x2="240" y2="48" stroke="var(--s2)" stroke-width="1.5"/><text x="245" y="51" fill="var(--s2)" font-size="7">UTC-1</text>
  <text x="20" y="72" fill="var(--muted)" font-size="8">− each offset →</text>
  <line x1="20" y1="90" x2="285" y2="90" stroke="var(--ink)" stroke-width="2"/><text x="120" y="84" fill="var(--ink)" font-size="7">one shared UTC axis</text>
  <circle cx="120" cy="90" r="3" fill="var(--s1)"/><circle cx="200" cy="90" r="3" fill="var(--s2)"/>
  <text x="20" y="110" fill="var(--muted)" font-size="7">comparison only means something once both are on this axis</text>
</svg>
^ The local clocks are offset lines that do not share an origin; subtracting each machine's offset projects its readings onto the single UTC axis where "earlier" and "later" are finally comparable.

The rule that follows is: store instants in UTC (or with an explicit offset attached), and convert to a local zone only at the moment of display. Local time is a presentation format, not a storage format.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/teach-inter-20/utc.py

The fixture is two events logged in different zones.

```json filename=modules/teaching-and-portability/code/teach-inter-20/events.json:1-8 COMPLETE
{
  "_meta": "Two events, each logged with a local wall-clock hour and the UTC offset of the machine that logged it (hours ahead of UTC). A naive log stores only the wall-clock hour and forgets the offset, so comparing or subtracting the stored numbers treats different-timezone times as if they were the same clock. The UTC hour is local_hour - utc_offset, an absolute instant. The question: does ordering the events by their stored wall-clock time match ordering them by the real instant?",
  "events": [
    {"name": "A", "local_hour": 14, "utc_offset": 2},
    {"name": "B", "local_hour": 13, "utc_offset": -1}
  ]
}
```

The UTC hour is one subtraction; ordering and duration take a key function so we can run each on the naive hour or the UTC hour.

```python filename=modules/teaching-and-portability/code/teach-inter-20/utc.py:40-51 COMPLETE
def utc_hour(e):
    """The absolute instant: local wall-clock hour minus the machine's UTC offset."""
    return e["local_hour"] - e["utc_offset"]


def order_by(events, key):
    return [e["name"] for e in sorted(events, key=key)]


def duration(events, key):
    vals = [key(e) for e in events]
    return abs(vals[0] - vals[1])
```

Run `--instants` to convert each event.

```text filename=--instants
INSTANTS — naive wall-clock hour vs true UTC hour
----------------------------------------------------------
  event   local   offset   UTC hour
  A       14:00   +2       12:00
  B       13:00   -1       14:00
----------------------------------------------------------
  the wall-clock hour hides the offset; the UTC hour is absolute.
```

A reads 14:00 but is at UTC+2, so it is really 12:00 UTC. B reads 13:00 but is at UTC−1, so it is really 14:00 UTC. On the wall clock A's number is bigger; on the universal clock A's instant is earlier. The offset is the whole difference, and the naive timestamp is exactly the part that hid it.

<svg role="img" aria-label="Event A wall clock 14 maps to UTC 12; event B wall clock 13 maps to UTC 14, so A is earlier in UTC despite a larger wall-clock number" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="16" fill="var(--muted)" font-size="8">wall clock (naive)</text>
  <line x1="20" y1="30" x2="285" y2="30" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="200" cy="30" r="4" fill="var(--s1)"/><text x="190" y="24" fill="var(--s1)" font-size="8">A 14</text>
  <circle cx="150" cy="30" r="4" fill="var(--s2)"/><text x="140" y="24" fill="var(--s2)" font-size="8">B 13</text>
  <text x="10" y="76" fill="var(--muted)" font-size="8">UTC (true instant)</text>
  <line x1="20" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="120" cy="90" r="4" fill="var(--s1)"/><text x="110" y="84" fill="var(--s1)" font-size="8">A 12</text>
  <circle cx="200" cy="90" r="4" fill="var(--s2)"/><text x="190" y="84" fill="var(--s2)" font-size="8">B 14</text>
  <line x1="200" y1="34" x2="120" y2="86" stroke="var(--s1)" stroke-width="1" stroke-dasharray="2 2"/>
  <line x1="150" y1="34" x2="200" y2="86" stroke="var(--s2)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="60" y="112" fill="var(--muted)" font-size="7">A and B swap places between the two clocks</text>
</svg>
^ On the wall clock A sits to the right of B; converting to UTC by the offsets swaps them, so A is actually the earlier instant — the crossing lines are the bug.

## Build

The order view sorts the events by each clock and reports the duration each yields.

```python filename=modules/teaching-and-portability/code/teach-inter-20/utc.py:66-75 COMPLETE
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
```

Now order and time them with `--order`.

```text filename=--order
ORDER — event order and duration by naive time vs UTC
----------------------------------------------------------
  by naive wall clock: B then A   duration 1 h
  by UTC (true):       A then B   duration 2 h
----------------------------------------------------------
  the naive order is reversed and its duration is wrong.
```

By the naive wall clock the order is B then A with a 1-hour gap. By UTC the order is A then B with a 2-hour gap. Both outputs are wrong under the naive scheme: the sequence is reversed *and* the elapsed time is halved. A dashboard sorting events by the stored hour would show them backwards; a report computing "time between A and B" would say one hour when it was two. Neither error announces itself — the numbers look perfectly reasonable.

<svg role="img" aria-label="Naive order B then A with gap 1; UTC order A then B with gap 2 — both order and duration differ" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="16" fill="var(--s1)" font-size="8">naive: B then A, 1 h</text>
  <line x1="20" y1="35" x2="280" y2="35" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="150" cy="35" r="4" fill="var(--s2)"/><text x="145" y="28" fill="var(--s2)" font-size="8">B</text>
  <circle cx="200" cy="35" r="4" fill="var(--s1)"/><text x="196" y="28" fill="var(--s1)" font-size="8">A</text>
  <text x="10" y="72" fill="var(--s2)" font-size="8">UTC: A then B, 2 h</text>
  <line x1="20" y1="90" x2="280" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="120" cy="90" r="4" fill="var(--s1)"/><text x="116" y="83" fill="var(--s1)" font-size="8">A</text>
  <circle cx="200" cy="90" r="4" fill="var(--s2)"/><text x="196" y="83" fill="var(--s2)" font-size="8">B</text>
  <text x="30" y="106" fill="var(--muted)" font-size="7">order reversed and the gap doubles under UTC — the naive read was wrong on both</text>
</svg>
^ Naive and UTC disagree on both the order (B–A vs A–B) and the gap (1 h vs 2 h), so a naive timestamp corrupts sequencing and elapsed-time alike.

## Definition of done

The self-test pins both failures: the UTC hour is local minus offset, the offsets differ, the naive order is reversed, the naive duration is wrong, and the event that reads later actually happened earlier.

```python filename=modules/teaching-and-portability/code/teach-inter-20/utc.py:87-99 COMPLETE
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
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive order and duration are wrong; the UTC ones are right
------------------------------------------------------------------------------------------------
  the UTC hour is local_hour - utc_offset = True
  the two events were logged in different timezones = True (+2 vs -1)
  the naive wall-clock order differs from the true UTC order = True (['B', 'A'] vs ['A', 'B'])
  the naive duration differs from the true duration = True (1 h vs 2 h)
  the event that reads later actually happened earlier = True
------------------------------------------------------------------------------------------------
SELF-TEST PASS  utc_is_local_minus_offset=True  offsets_differ=True  naive_order_reversed=True  naive_duration_wrong=True  naive_looks_later_is_earlier=True
```

**Done means the corruption is exhibited, not warned about: the naive order (B, A) reverses the true UTC order (A, B), and the naive 1-hour gap is half the real 2-hour elapsed time.**

## Boss fight

Storing UTC fixed ordering and duration. Predict whether that means you should also display timestamps in UTC to users. It is tempting to keep everything in UTC end to end.

You should store UTC and display local — the two roles are different. A user in Tokyo wants to see "3:00 PM" in their own zone, not a UTC number they have to convert in their head; showing raw UTC to humans is its own usability bug. The discipline is a clean split: instants live in UTC in storage and computation, and are converted to the viewer's timezone only at the render boundary. Storing local to save a conversion, or displaying UTC to save a conversion, both break — one corrupts the data, the other confuses the user. Convert at the edges, compute in the middle.

The mirror-image mistake is thinking a fixed offset makes a timestamp safe. Offsets are not constant: daylight saving time shifts a zone's offset twice a year, so the same location is UTC+1 in winter and UTC+2 in summer, and a naive local time during the autumn "fall back" hour is genuinely ambiguous — it happens twice. This is why robust systems store UTC (which never shifts) rather than a local time plus a remembered offset, and why "the offset I saw at write time" is not enough to reconstruct the instant later. UTC is the only clock with no DST and no ambiguity.

```python filename=modules/teaching-and-portability/code/teach-inter-20/utc.py:40-42 COMPLETE
def utc_hour(e):
    """The absolute instant: local wall-clock hour minus the machine's UTC offset."""
    return e["local_hour"] - e["utc_offset"]
```

**Store timestamps as absolute UTC instants and convert to a local zone only for display — a naive wall-clock time drops the offset that makes it comparable, corrupting order and duration, and even a stored offset is defeated by daylight saving.**

## External resources

The Python `datetime` documentation on aware vs naive datetimes and `datetime.now(timezone.utc)` — the language-level version of this rule, and why naive datetimes are a footgun.

"UTC is enough for everyone... right?" and Jon Skeet's writing on date/time handling — the many ways timezones, DST, and offsets defeat naive timestamps, and why UTC storage is the standard fix.

The IANA time zone database (tz) and the ISO 8601 format — how zones and their DST rules are actually represented, and the timestamp format that carries an explicit offset when you must keep local information.
