---
id: leaseskew-inter-01
title: A lease holder must expire early — network delay and clock skew push a full-duration lease past the grantor's expiry
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A lease grants exclusive use of a resource for a duration D, and two clocks are involved: the grantor starts counting when it sends the grant and will reassign the lease at its own time D, while the holder starts counting when it receives the grant — later by the network delay — and the holder's clock may run slow relative to the grantor's, so its D-length timer takes extra real time to finish. Put those together in the grantor's timeline and the holder receives the grant at delay, runs a timer that elapses after D plus the skew, and stops at delay + D + skew — past the grantor's expiry at D — so there is a window from D to delay + D + skew where the grantor may already have handed the lease to a new holder while the old one still believes it holds it, the two-holders failure the lease existed to prevent. The holder cannot see the grantor's clock, so it cannot measure this; what it can do is assume the worst and use an effective lease of D minus a safety margin, with the margin at least the maximum network delay plus the maximum clock skew, so it stops at delay + (D − margin) + skew, which is at most D. On the fixture D is 100, the network delay 10, the clock skew 15, and the margin 30: the naive holder stops at 125, overrunning the expiry of 100 by 25 (exactly delay + skew), while the holder using D − 30 stops at 95, safely before 100; a margin of only 20 is smaller than delay + skew and still overruns to 105. The rule: a lease's granted duration is an upper bound the grantor enforces, and the holder must treat its own usable lease as shorter by at least the delay plus the skew, or the two windows overlap.
eli5: Imagine you rent a practice room until 3:00 by the front-desk clock, but you only find out you got it a few minutes after 3:00's countdown already started, and your own watch runs a little slow. If you pack up exactly when your watch says the hour is done, it's already past 3:00 on the desk clock — and the next person, who the desk sent in at 3:00, is now in the room with you. The safe move is to leave a bit early by your own watch: stop with enough cushion to cover both the late start and your slow watch, so you're always out before the desk gives the room to someone else. You can't see the desk's clock, so you give yourself a margin and quit early.
---

## Why this module

Leases are how distributed systems grant time-bounded exclusive access — a leader lease, a lock with a timeout, a cache entry's ownership. The appeal is that the grant expires on its own, so a holder that crashes or gets partitioned does not hold the resource forever. But "expires on its own" hides a clock question: expires by whose clock?

The grant is measured by the grantor, and enforced by the grantor when it decides to reassign. The holder runs on a different clock, learns of the grant after a delay, and cannot see the grantor's clock at all. If the holder assumes its lease lasts exactly as long as granted, from its own perspective, it will still be acting after the grantor has moved on — and the whole point of a lease, one holder at a time, is broken.

**A lease's duration is enforced on the grantor's clock, so a holder that uses the full duration on its own clock can outlast the grant and overlap the next holder.**

## Concepts

Set up the two clocks in one shared timeline. The grantor sends the grant at time 0 and will consider the lease expired — and free to reassign — at time D. That is the hard deadline the holder must beat.

The holder does not receive the grant at time 0. It arrives after the network delay, so the holder only starts its own timer at time = delay. And the holder's clock may not tick at the grantor's rate; if it runs slow, a D-length interval on the holder's clock takes more than D of real time — the extra being the clock skew. So the holder's timer, started at delay and lasting D-plus-skew of real time, elapses at delay + D + skew in the shared timeline.

Compare that to the grantor's expiry at D. The holder stops at delay + D + skew, which is later than D by exactly delay + skew. In that gap the grantor has already expired the lease and may have granted it to another node, while the old holder — whose timer has not fired yet — is still acting. Two holders, the exact hazard a lease is supposed to make impossible.

The holder cannot fix this by measuring, because it has no access to the grantor's clock and cannot know the true delay or skew for this grant. What it can do is bound them and subtract. Choose a safety margin at least as large as the maximum network delay plus the maximum clock skew, and treat the usable lease as D minus that margin. Then the holder stops at delay + (D − margin) + skew ≤ D, at or before the grantor's expiry, whatever the actual delay and skew were within their bounds.

This is why real lease implementations always have the holder renew or stop well before the nominal expiry: the granted duration is an upper bound the grantor enforces, and the holder's safe working window is strictly shorter. The margin is the price of not being able to see the other clock.

**The holder must use an effective lease of D minus a margin covering the delay plus the skew, because its stop time in the grantor's frame is delay + effective + skew and that must not exceed D.**

<svg role="img" aria-label="The holder's stop time built up from three parts: the network delay shifts the start right, the granted duration is the middle, and the clock skew stretches the end, pushing the stop past the grantor's expiry." viewBox="0 0 320 130">
<rect x="0" y="0" width="320" height="130" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="12">holder stop = delay + duration + skew</text>
<line x1="200" y1="28" x2="200" y2="100" stroke="var(--ink)" stroke-dasharray="3 3"></line>
<text x="182" y="114" fill="var(--muted)" font-size="9">grantor expiry</text>
<rect x="30" y="50" width="24" height="16" fill="var(--muted)"></rect>
<text x="30" y="80" fill="var(--muted)" font-size="8">delay</text>
<rect x="54" y="50" width="146" height="16" fill="var(--s2)"></rect>
<text x="90" y="62" fill="var(--panel)" font-size="8">granted duration</text>
<rect x="200" y="50" width="40" height="16" fill="var(--s1)"></rect>
<text x="204" y="62" fill="var(--panel)" font-size="8">skew</text>
<text x="242" y="62" fill="var(--s1)" font-size="8">&#8594; overruns</text>
</svg>
^ The delay shifts the holder's window right and the skew stretches its end, so a full-duration lease reaches past the grantor's expiry by exactly delay + skew.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/orchestration-and-governance/code/leaseskew-inter-01/leaseskew.py

The fixture grants a 100-unit lease with a 10-unit delay and 15-unit skew.

```json filename=modules/orchestration-and-governance/code/leaseskew-inter-01/leaseskew.json:3-7 COMPLETE
  "lease_duration": 100,
  "network_delay": 10,
  "clock_skew": 15,
  "margin": 30,
  "small_margin": 20
```

The grantor expires at D; the holder stops at delay + its effective duration + skew.

```python filename=modules/orchestration-and-governance/code/leaseskew-inter-01/leaseskew.py:30-32 COMPLETE
def grantor_expiry(d):
    """When the grantor considers the lease expired and may reassign it: its own duration."""
    return d["lease_duration"]
```

```python filename=modules/orchestration-and-governance/code/leaseskew-inter-01/leaseskew.py:35-37 COMPLETE
def holder_stop(d, effective_duration):
    """When the holder actually stops, in the grantor's timeline: receipt delay + its timer + skew."""
    return d["network_delay"] + effective_duration + d["clock_skew"]
```

Using the full duration overruns the expiry.

```text filename=leaseskew.py --naive
NAIVE — holder uses the full granted duration 100 on its own clock
----------------------------------------------------------------
  grantor expiry (grantor clock) = 100
  holder stop = delay 10 + duration 100 + skew 15 = 125
  overlap past expiry = 25
----------------------------------------------------------------
  the holder is still acting after the grantor reassigned the lease -- two holders
```

The grantor frees the lease at 100, but the holder does not stop until 125 — a 25-unit window (10 delay + 15 skew) in which the grantor may have granted the lease to someone else while the old holder is still writing. The holder did exactly D of work; the delay and skew pushed that D past the grantor's D.

<svg role="img" aria-label="Two timelines. The grantor's lease runs from 0 to 100, then a new grant begins. The holder's lease starts at 10 (after the delay) and runs to 125, overlapping the grantor's next grant from 100 to 125." viewBox="0 0 320 140">
<rect x="0" y="0" width="320" height="140" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="12">holder's window overruns the grantor's expiry</text>
<text x="20" y="44" fill="var(--muted)" font-size="9">grantor</text>
<rect x="60" y="34" width="180" height="16" fill="var(--s2)"></rect>
<text x="64" y="46" fill="var(--panel)" font-size="8">lease to holder (0-100)</text>
<rect x="240" y="34" width="60" height="16" fill="var(--muted)"></rect>
<text x="244" y="46" fill="var(--panel)" font-size="8">next</text>
<text x="20" y="84" fill="var(--muted)" font-size="9">holder</text>
<rect x="78" y="74" width="207" height="16" fill="var(--s1)"></rect>
<text x="82" y="86" fill="var(--panel)" font-size="8">believes it holds (10-125)</text>
<rect x="240" y="74" width="45" height="16" fill="var(--s1)" opacity="0.5"></rect>
<line x1="240" y1="28" x2="240" y2="100" stroke="var(--ink)" stroke-dasharray="3 3"></line>
<text x="200" y="112" fill="var(--s1)" font-size="9">overlap 100-125: two holders</text>
</svg>
^ The holder's window, shifted right by the delay and stretched by the skew, runs to 125 and overlaps the grantor's next grant that began at 100.

## Build

Shortening the effective lease by a sufficient margin makes the holder stop in time.

```python filename=modules/orchestration-and-governance/code/leaseskew-inter-01/leaseskew.py:40-47 COMPLETE
def overlap(d, effective_duration):
    """How long the holder keeps acting past the grantor's expiry (0 if it stops in time)."""
    return max(0, holder_stop(d, effective_duration) - grantor_expiry(d))


def needed_margin(d):
    """The smallest safety margin that avoids overlap: the network delay plus the clock skew."""
    return d["network_delay"] + d["clock_skew"]
```

```text filename=leaseskew.py --safe
SAFE — holder uses an effective lease of duration 100 minus margin 30 = 70
----------------------------------------------------------------
  grantor expiry = 100
  holder stop = delay 10 + effective 70 + skew 15 = 95
  overlap past expiry = 0   (margin 30 >= needed 25)
----------------------------------------------------------------
  shortening the lease by at least delay + skew makes the holder stop before expiry
```

With an effective lease of 70 (100 minus the 30 margin), the holder stops at 95 — before the grantor's expiry at 100, with 5 to spare. The margin of 30 covers the needed 25 (delay 10 + skew 15), so no overlap. The holder gave up 30 units of usable lease to buy the guarantee that it never outlasts the grant.

<svg role="img" aria-label="Three stop times against the grantor's expiry at 100: naive stops at 125 (overruns), a margin of 30 stops at 95 (safe), and a too-small margin of 20 stops at 105 (still overruns)." viewBox="0 0 320 140">
<rect x="0" y="0" width="320" height="140" fill="var(--panel)"></rect>
<text x="12" y="16" fill="var(--ink)" font-size="12">holder stop vs grantor expiry (100)</text>
<line x1="200" y1="28" x2="200" y2="120" stroke="var(--ink)" stroke-dasharray="3 3"></line>
<text x="182" y="134" fill="var(--muted)" font-size="9">expiry 100</text>
<rect x="40" y="36" width="210" height="14" fill="var(--s1)"></rect>
<text x="252" y="47" fill="var(--s1)" font-size="9">naive 125</text>
<rect x="40" y="62" width="150" height="14" fill="var(--s2)"></rect>
<text x="192" y="73" fill="var(--s2)" font-size="9">margin 30 &#8594; 95</text>
<rect x="40" y="88" width="170" height="14" fill="var(--s1)" opacity="0.6"></rect>
<text x="212" y="99" fill="var(--s1)" font-size="9">margin 20 &#8594; 105</text>
</svg>
^ Only the bar that ends left of the expiry line (margin 30, stop 95) is safe; the naive stop and the too-small margin both cross the line.

The self-test ties the overrun to delay + skew and shows the margin must cover it.

```python filename=modules/orchestration-and-governance/code/leaseskew-inter-01/leaseskew.py:80-84 COMPLETE
    naive_overlaps = overlap(d, dur) > 0
    print("  naive holder overruns the grantor's expiry = %s (stop %d > expiry %d)" % (naive_overlaps, holder_stop(d, dur), grantor_expiry(d)))

    overlap_is_delay_plus_skew = overlap(d, dur) == needed_margin(d)
    print("  the overrun equals delay + skew = %s (%d == %d)" % (overlap_is_delay_plus_skew, overlap(d, dur), needed_margin(d)))
```

```text filename=leaseskew.py --check
SELF-TEST — the naive stop overruns the grantor's expiry by delay + skew, a margin of at least delay + skew stops in time, and a smaller margin still overruns
----------------------------------------------------------------------------------------------------------------
  naive holder overruns the grantor's expiry = True (stop 125 > expiry 100)
  the overrun equals delay + skew = True (25 == 25)
  margin 30 (>= delay+skew) stops the holder in time = True (stop 95 <= expiry 100)
  the chosen margin covers delay + skew = True (30 >= 25)
  a margin of only 20 (< delay+skew) still overruns = True (stop 105)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_overlaps=True  overlap_is_delay_plus_skew=True  safe_no_overlap=True  margin_covers=True  small_margin_fails=True
```

**small_margin_fails is the sizing rule made concrete: any margin below delay + skew still overruns, so the margin must bound the worst-case delay and skew, not a typical one.**

## Definition of done

You can explain why a lease's duration is enforced on the grantor's clock and why the holder's usable window is shorter — it starts late (delay) and may run slow (skew).

You can compute the holder's stop time in the grantor's frame (delay + effective duration + skew) and show why the full duration overruns by delay + skew.

You can size the safety margin — at least the maximum delay plus the maximum skew — and explain why it must bound the worst case, not the typical case.

You can state why the holder cannot solve this by measurement (no access to the grantor's clock) and must instead give up usable lease time as the margin.

## Boss fight

Your leader-election uses a 10-second lease, and rarely — under network load — two nodes briefly both act as leader and issue conflicting writes, even though the lease "clearly" expired. Logs show the old leader wrote a few hundred milliseconds after the new leader was elected.

First: explain how a 10-second lease produces a sub-second double-leader window. Which two quantities, added, define the overlap, and why does it show up under network load specifically?

Then: fix it with a safety margin. Given a lease of 10 seconds, a worst-case network delay of 300 ms, and a worst-case clock skew of 200 ms, what effective lease should the leader use, and what does that cost you (how much sooner must it renew)? Why is renewing at the effective expiry, not the nominal one, the whole discipline?

Finally: a safety margin makes double-leader windows rare but relies on the delay and skew staying within their assumed bounds — and a garbage-collection pause or a VM freeze can blow past any margin. Explain why a margin alone cannot make leases fully safe against unbounded pauses, and how a fencing token on the resource closes the gap the margin cannot (connect to the idea that the resource, not the holder, has the final say).

## External resources

Google's Chubby lock-service paper describes lease timeouts held shorter on the client than on the master precisely to tolerate clock and message delays — the safety margin this module builds.

Martin Kleppmann's writing on distributed locks ("How to do distributed locking") shows why clock-based leases can still fail under unbounded pauses and why a monotonic fencing token on the resource is the backstop, which is the boss fight's final step.
