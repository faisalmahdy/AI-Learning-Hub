---
id: credit-inter-01
title: Pace the sender with credit-based flow control — the receiver advertises its free capacity so the buffer never overflows, instead of dropping a dumped burst
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A bounded queue with backpressure is reactive — it lets the sender push until the queue is full, then blocks or drops — which protects the receiver from an unbounded buffer but still handles overload by discarding work that has already arrived. Credit-based flow control moves the decision upstream, before the item is sent at all: the receiver advertises its free capacity as "credit", the sender may send only up to the credit it currently holds (decrementing as it sends), and the receiver replenishes credit as it drains items it has processed. The sender is thus never permitted to put more into the buffer than there is room for, so the buffer never overflows and nothing is dropped — what would have been a burst that overruns the receiver becomes a stream paced exactly to the receiver's rate. Without flow control, a sender that dumps its whole burst at once meets a buffer that holds only its capacity, and the excess is dropped: work lost not because the receiver could not eventually handle it, but because it all arrived before the receiver could make room. That is the distinction credit-based flow control captures — throughput versus burst: the receiver can process all the work over time, it just cannot hold all of it at once, and flow control matches the sender's sending to the receiver's draining. On a fixture where a sender has 6 items for a receiver that buffers 3 and processes 1 per step, dumping all at once drops 3, while credit-based flow control keeps the buffer within 3 and delivers all 6.
eli5: Imagine pouring water from a big jug into a small cup that has a tiny hole draining it slowly. If you just upend the jug, the cup overflows instantly and most of the water spills on the floor — gone. The cup could have handled all the water eventually, drip by drip, but it can't hold it all at once. The smart way is for the cup to tell you "I've got room for three more sips right now," so you pour only that much, wait for it to drain a bit, and then it says "room for one more," and you pour one more. Nothing spills, and all the water gets through — just paced to how fast the cup drains. Credit-based flow control is the cup telling the jug how much room it has before each pour, so the sender never overfills the receiver.
---

## Why this module

Any time a fast producer feeds a slower consumer, something has to give, and the question is what and when. The naive design lets the producer send at its own pace and hopes the consumer keeps up; when it does not, the work piles up somewhere, and that somewhere either grows without bound (a memory blowup) or is capped and starts dropping. Both are failures, and both happen after the excess work has already been produced and sent.

Backpressure with a bounded queue is the standard first fix: cap the buffer so it cannot grow unbounded, and block or drop when it fills. This is a real improvement — it converts an unbounded crash into a bounded, predictable loss — but it is still reactive. The sender learns it sent too much only after the fact, when its writes block or its items are refused, and any work already in flight past the cap is discarded.

Credit-based flow control is the proactive alternative: never send the excess in the first place. The receiver publishes how much room it has, and the sender treats that as a hard budget, sending only up to it. The overflow that backpressure would have to drop simply never leaves the sender; it waits until the receiver grants more credit. This module runs a burst through both designs and counts what is lost.

**Backpressure is reactive — it drops or blocks once the buffer is full — while credit-based flow control is proactive: the receiver advertises its free capacity and the sender never exceeds it, so the excess is never sent and the buffer never overflows.**

## Concepts

The distinction that makes flow control possible is throughput versus burst. A receiver has two different limits: how much work it can process over time (throughput) and how much it can hold at one instant (buffer capacity). A burst can exceed the instantaneous capacity while staying well within the throughput — the receiver could handle all of it if it arrived spread out, but not all at once. Dropping on overflow throws away work the receiver was perfectly capable of doing; it fails on the burst limit for work that fit under the throughput limit.

Credit is the mechanism that converts a burst into a paced stream. The credit the receiver advertises is exactly its free buffer space, so the sender filling up to the credit fills the buffer up to capacity and no further. As the receiver processes items and frees space, it advertises new credit, and the sender sends more. The sender's rate is thereby clamped to the receiver's draining rate, and the burst is spread across as many steps as the receiver needs — which is precisely what keeps the total work under the throughput limit from ever exceeding the buffer limit.

This is why credit-based flow control loses nothing while a bounded queue must drop. The bounded queue is a passive vessel: it can refuse, but it cannot reach back to the sender and slow it down before the item is created. Credit closes that loop — the receiver's state (its free space) directly gates the sender's action (how much it may send) — so the control happens before the item is sent, not after it arrives. It is the same loop that TCP's receive window and HTTP/2's flow-control window implement, and its guarantee is structural: if the sender obeys the credit, the buffer cannot overflow.

<svg role="img" aria-label="A control loop: the receiver's free space is advertised as credit back to the sender, which gates how much the sender sends into the buffer, closing the loop" viewBox="0 0 440 130">
<rect x="20" y="50" width="90" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="65" y="69" fill="var(--ink)" font-size="9" text-anchor="middle">sender</text>
<line x1="110" y1="58" x2="180" y2="58" stroke="var(--muted)"/>
<text x="145" y="50" fill="var(--muted)" font-size="8" text-anchor="middle">send &le; credit</text>
<rect x="180" y="50" width="90" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="225" y="69" fill="var(--ink)" font-size="9" text-anchor="middle">buffer</text>
<line x1="270" y1="65" x2="330" y2="65" stroke="var(--muted)"/>
<rect x="330" y="50" width="90" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="375" y="69" fill="var(--ink)" font-size="9" text-anchor="middle">receiver</text>
<path d="M375 80 Q 375 110, 220 110 T 65 80" fill="none" stroke="var(--s1)"/>
<text x="220" y="124" fill="var(--s1)" font-size="8" text-anchor="middle">advertises credit = free space</text>
</svg>
^ The receiver's free space flows back to the sender as credit and gates its sending, closing the loop so the buffer cannot be overrun.

**Throughput and burst are different limits, and overflow drops work that fit the throughput but not the instant; credit is the sender's free-space budget, which paces a burst into a stream and closes the loop so the buffer structurally cannot overflow.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/credit-inter-01. The fixture is a receiver's buffer capacity and processing rate, and the size of the sender's burst.

```json filename=modules/orchestration-and-governance/code/credit-inter-01/credit.json:3-5 COMPLETE
  "capacity": 3,
  "process_per_step": 1,
  "to_send": 6
```

With no flow control the sender dumps the whole burst; the buffer holds capacity and the rest is dropped.

```python filename=modules/orchestration-and-governance/code/credit-inter-01/credit.py:34-38 COMPLETE
def no_control(capacity, to_send):
    """Sender dumps the whole burst at once; the buffer holds capacity, the rest is dropped."""
    accepted = min(to_send, capacity)
    dropped = to_send - accepted
    return {"accepted": accepted, "dropped": dropped, "peak_buffer": accepted}
```

Under credit-based flow control the sender sends only up to the advertised credit, which refills as the receiver drains.

```python filename=modules/orchestration-and-governance/code/credit-inter-01/credit.py:41-60 COMPLETE
def credit_flow(capacity, process_per_step, to_send):
    """Sender sends only up to the receiver's advertised credit (free capacity), which refills as it drains."""
    buffer = 0
    remaining = to_send
    delivered = 0
    peak = 0
    trace = []
    step = 0
    while remaining > 0 or buffer > 0:
        credit = capacity - buffer          # receiver advertises its free slots
        sent = min(remaining, credit)       # sender never exceeds the credit
        buffer += sent
        remaining -= sent
        peak = max(peak, buffer)
        processed = min(process_per_step, buffer)
        buffer -= processed
        delivered += processed
        trace.append((step, credit, sent, buffer, delivered))
        step += 1
    return {"dropped": 0, "delivered": delivered, "peak_buffer": peak, "trace": trace}
```

Before running it, predict: dumping 6 into a buffer of 3 drops 3. Run `--nocontrol`:

```text filename=credit.py --nocontrol
NOCONTROL — sender dumps all 6 items into a buffer of 3
----------------------------------------------------
  buffer accepts: 3
  overflow dropped: 3
----------------------------------------------------
  the burst exceeds the buffer, so the excess is lost on arrival
```

The prediction holds. The buffer accepts 3 and drops 3 — half the burst is lost on arrival, even though the receiver could have processed all 6 over six steps. The loss is a burst-limit failure, not a throughput failure.

<svg role="img" aria-label="A burst of 6 items poured into a buffer of 3: three fill the buffer and three overflow and are dropped" viewBox="0 0 440 140">
<text x="70" y="30" fill="var(--ink)" font-size="10" text-anchor="middle">burst of 6</text>
<rect x="50" y="40" width="40" height="80" fill="var(--s2)"/>
<text x="70" y="86" fill="var(--ink)" font-size="9" text-anchor="middle">6</text>
<line x1="95" y1="80" x2="180" y2="80" stroke="var(--muted)"/>
<rect x="190" y="70" width="70" height="50" fill="var(--panel)" stroke="var(--s1)"/>
<text x="225" y="60" fill="var(--muted)" font-size="9" text-anchor="middle">buffer (3)</text>
<text x="225" y="100" fill="var(--s1)" font-size="9" text-anchor="middle">holds 3</text>
<text x="330" y="100" fill="var(--s2)" font-size="10" text-anchor="middle">3 overflow, dropped</text>
<path d="M260 80 L 300 80" stroke="var(--s2)"/>
</svg>
^ Dumping the burst overruns a buffer that holds only 3, so 3 items overflow and are lost though the receiver could have processed all 6 over time.

Now the paced version. Run `--credit`:

```text filename=credit.py --credit
CREDIT — sender paced by advertised credit (capacity 3, process 1/step)
----------------------------------------------------------
  step   credit   sent   buffer   delivered
  0      3        3      2        1
  1      1        1      2        2
  2      1        1      2        3
  3      1        1      2        4
  4      1        0      1        5
  5      2        0      0        6
----------------------------------------------------------
  buffer peaks at 3 (<= capacity); 6 delivered, 0 dropped
```

The prediction of pacing holds. Step 0 the sender uses its full credit of 3; thereafter the receiver frees one slot per step, so it advertises credit of 1 and the sender sends 1, matching the drain rate. The buffer peaks at 3 and never exceeds it, and all 6 items are delivered over six steps — none dropped. The burst became a stream clamped to the receiver's rate.

<svg role="img" aria-label="Buffer occupancy over six steps under credit flow control, staying at or below the capacity line of 3 the whole time while all six items are delivered" viewBox="0 0 440 150">
<line x1="40" y1="120" x2="410" y2="120" stroke="var(--line)"/>
<line x1="40" y1="120" x2="40" y2="30" stroke="var(--line)"/>
<line x1="40" y1="50" x2="410" y2="50" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="405" y="46" fill="var(--s2)" font-size="8" text-anchor="end">capacity 3</text>
<rect x="60" y="50" width="24" height="70" fill="var(--s1)"/>
<rect x="110" y="50" width="24" height="70" fill="var(--s1)"/>
<rect x="160" y="50" width="24" height="70" fill="var(--s1)"/>
<rect x="210" y="50" width="24" height="70" fill="var(--s1)"/>
<rect x="260" y="73" width="24" height="47" fill="var(--s1)"/>
<rect x="310" y="97" width="24" height="23" fill="var(--s1)"/>
<text x="225" y="138" fill="var(--muted)" font-size="9" text-anchor="middle">step 0 ... 5 — buffer stays at or under capacity, all 6 delivered</text>
</svg>
^ Under credit pacing the buffer rides at or below the capacity line every step; nothing overflows and all six items get through.

## Build

The self-test plants the failure and names each claim as a boolean flag. It first runs both designs on the same fixture.

```python filename=modules/orchestration-and-governance/code/credit-inter-01/credit.py:91-93 COMPLETE
    cap, pps, ts = data["capacity"], data["process_per_step"], data["to_send"]
    nc = no_control(cap, ts)
    cr = credit_flow(cap, pps, ts)
```

Then it checks that the burst exceeds capacity, that no-control drops items, and that credit flow control drops nothing, keeps the buffer within capacity, and delivers everything.

```python filename=modules/orchestration-and-governance/code/credit-inter-01/credit.py:98-107 COMPLETE
    nocontrol_drops = nc["dropped"] > 0
    print("  no flow control: the buffer overflows and drops items = %s (%d)" % (nocontrol_drops, nc["dropped"]))

    credit_drops_none = cr["dropped"] == 0
    print("  credit flow control: nothing is dropped = %s" % credit_drops_none)

    credit_within_capacity = cr["peak_buffer"] <= cap
    print("  credit flow control: buffer never exceeds capacity = %s (peak %d)" % (credit_within_capacity, cr["peak_buffer"]))

    credit_delivers_all = cr["delivered"] == ts
    print("  credit flow control: all items delivered (paced) = %s (%d of %d)" % (credit_delivers_all, cr["delivered"], ts))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if credit pacing ever drops an item or overruns the buffer:

```text filename=credit.py --check
SELF-TEST — an uncontrolled burst overflows the buffer and drops the excess; credit pacing drops nothing
----------------------------------------------------------------------------------------------------------------
  the burst is larger than the buffer capacity = True (6 > 3)
  no flow control: the buffer overflows and drops items = True (3)
  credit flow control: nothing is dropped = True
  credit flow control: buffer never exceeds capacity = True (peak 3)
  credit flow control: all items delivered (paced) = True (6 of 6)
```

**The self-test checks both that credit drops nothing and that the buffer never exceeds capacity — proving the no-loss guarantee comes from the sender respecting the credit, not from a larger buffer or luck.**

## Definition of done

You can distinguish reactive backpressure (drop/block when the buffer fills) from proactive credit-based flow control (never send beyond advertised capacity).
You can define credit as the receiver's free buffer space and explain how advertising and replenishing it paces the sender to the receiver's drain rate.
You can separate throughput from burst and explain why overflow drops work that fit the throughput but not the instant.
You can explain why credit-based flow control structurally cannot overflow the buffer, while a bounded queue must drop.
You can name real instances of the mechanism (TCP receive window, HTTP/2 flow-control window) and state their shared guarantee.

## Boss fight

Consider what credit-based flow control does when the receiver never drains — a permanently stuck consumer. Credit never replenishes, so the sender's credit stays at zero and it simply cannot send; the work backs up on the sender's side instead of the receiver's. That is better than dropping (nothing is lost) but it relocates the problem: the sender must now decide what to do when it is blocked indefinitely — buffer locally (its own unbounded-growth risk), apply its own upstream backpressure, or time out. The lesson sharpens: flow control does not make an overloaded system able to do more work; it moves the pressure to a place where you can handle it deliberately, and a truly stuck receiver still forces a policy decision, just a cleaner one than silent drops.

Now consider a multi-sender receiver, where flow control interacts with fairness. If the receiver advertises a single pool of credit and several senders compete for it, a greedy sender can grab all the credit each round and starve the others — the exact head-of-line-style unfairness a shared resource invites. Real protocols address this by allocating credit per sender (per-stream flow-control windows in HTTP/2) rather than one global pool, so each sender's pacing is independent and one cannot monopolize the receiver. The principle generalizes: credit controls how much is sent, but who gets to send needs its own allocation, or flow control on a shared receiver reintroduces starvation.

**Credit-based flow control moves back-pressure to the sender rather than eliminating it, so a stuck receiver still forces a deliberate policy at the sender; and on a shared receiver, credit must be allocated per sender, or a greedy sender grabs the whole pool and starves the rest.**

## External resources

The TCP specification's receive window is the canonical credit-based flow-control mechanism: the receiver advertises the window, and the sender may have only that many unacknowledged bytes in flight.
HTTP/2 and gRPC define per-stream and per-connection flow-control windows, the credit mechanism applied to multiplexed streams with the per-sender fairness the boss fight raises.
The topic's own module on bounded queues and backpressure covers the reactive alternative this proactive mechanism is contrasted against.
