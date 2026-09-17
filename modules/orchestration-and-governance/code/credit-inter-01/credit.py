"""Pace the sender with credit-based flow control -- the receiver advertises how many items it can accept and the sender never exceeds that -- so the buffer never overflows, instead of a sender that dumps its burst and forces the receiver to drop the excess.

A bounded queue with backpressure is reactive: it lets the sender push until the queue is full, then blocks or drops. That protects the receiver from an unbounded buffer, but it still means overload is handled by discarding work once it has already arrived. Credit-based flow control moves the decision upstream, to before the item is sent at all.

The mechanism is a running budget the receiver grants. The receiver advertises its free capacity as 'credit'; the sender may send only up to the credit it currently holds, decrementing as it sends; and the receiver replenishes credit as it drains items it has processed. The sender is thus never permitted to put more into the buffer than there is room for, so the buffer never overflows and nothing is dropped. What would have been a burst that overruns the receiver becomes a stream paced exactly to the receiver's rate.

Without flow control, a sender that dumps its whole burst at once meets a buffer that can hold only its capacity. The items beyond capacity have nowhere to go and are dropped -- work lost not because the receiver could not eventually handle it, but because it all arrived before the receiver could make room. The same total work, delivered at the sender's pace, exceeds the receiver's instantaneous capacity even though it does not exceed its throughput.

That is the distinction credit-based flow control captures: throughput versus burst. The receiver can process all the work over time; it just cannot hold all of it at once. Flow control matches the sender's sending to the receiver's draining, so the work is spread over the steps the receiver needs, and the buffer stays within capacity the whole way.

The rule: use credit-based flow control -- the receiver advertises its free capacity and the sender sends only up to that credit, replenished as the receiver drains -- so the sender is paced to the receiver and the buffer never overflows, rather than letting a sender dump a burst that overruns a bounded buffer and forces drops.

On this fixture a sender has 6 items for a receiver that buffers 3 and processes 1 per step. Dumped all at once, 3 items overflow the buffer and are dropped; under credit-based flow control the sender is paced, the buffer never exceeds 3, and all 6 are delivered. This computes both.

  --nocontrol   the sender dumps its burst: what the buffer holds and what overflows
  --credit      the step-by-step credit pacing: sends, buffer occupancy, and deliveries
  --check       an uncontrolled burst overflows the buffer and drops the excess; credit pacing drops nothing

capacity, process_per_step, and to_send are the fixture; the drops, peak buffer, and pacing are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "credit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def no_control(capacity, to_send):
    """Sender dumps the whole burst at once; the buffer holds capacity, the rest is dropped."""
    accepted = min(to_send, capacity)
    dropped = to_send - accepted
    return {"accepted": accepted, "dropped": dropped, "peak_buffer": accepted}


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


# ----------------------------------------------------------------- printing

def nocontrol_view(data):
    cap, ts = data["capacity"], data["to_send"]
    r = no_control(cap, ts)
    print("NOCONTROL — sender dumps all %d items into a buffer of %d" % (ts, cap))
    print("-" * 52)
    print("  buffer accepts: %d" % r["accepted"])
    print("  overflow dropped: %d" % r["dropped"])
    print("-" * 52)
    print("  the burst exceeds the buffer, so the excess is lost on arrival")


def credit_view(data):
    cap, pps, ts = data["capacity"], data["process_per_step"], data["to_send"]
    r = credit_flow(cap, pps, ts)
    print("CREDIT — sender paced by advertised credit (capacity %d, process %d/step)" % (cap, pps))
    print("-" * 58)
    print("  step   credit   sent   buffer   delivered")
    for step, credit, sent, buffer, delivered in r["trace"]:
        print("  %-5d  %-6d   %-4d   %-6d   %d" % (step, credit, sent, buffer, delivered))
    print("-" * 58)
    print("  buffer peaks at %d (<= capacity); %d delivered, 0 dropped" % (r["peak_buffer"], r["delivered"]))


def check(data):
    print("SELF-TEST — an uncontrolled burst overflows the buffer and drops the excess; credit pacing drops nothing")
    print("-" * 112)
    cap, pps, ts = data["capacity"], data["process_per_step"], data["to_send"]
    nc = no_control(cap, ts)
    cr = credit_flow(cap, pps, ts)

    burst_exceeds_capacity = ts > cap
    print("  the burst is larger than the buffer capacity = %s (%d > %d)" % (burst_exceeds_capacity, ts, cap))

    nocontrol_drops = nc["dropped"] > 0
    print("  no flow control: the buffer overflows and drops items = %s (%d)" % (nocontrol_drops, nc["dropped"]))

    credit_drops_none = cr["dropped"] == 0
    print("  credit flow control: nothing is dropped = %s" % credit_drops_none)

    credit_within_capacity = cr["peak_buffer"] <= cap
    print("  credit flow control: buffer never exceeds capacity = %s (peak %d)" % (credit_within_capacity, cr["peak_buffer"]))

    credit_delivers_all = cr["delivered"] == ts
    print("  credit flow control: all items delivered (paced) = %s (%d of %d)" % (credit_delivers_all, cr["delivered"], ts))

    ok = (burst_exceeds_capacity and nocontrol_drops and credit_drops_none
          and credit_within_capacity and credit_delivers_all)
    print("-" * 112)
    print("SELF-TEST %s  burst_exceeds_capacity=%s  nocontrol_drops=%s  credit_drops_none=%s  credit_within_capacity=%s  credit_delivers_all=%s"
          % ("PASS" if ok else "FAIL", burst_exceeds_capacity, nocontrol_drops, credit_drops_none,
             credit_within_capacity, credit_delivers_all))
    return ok


def main():
    p = argparse.ArgumentParser(description="Credit-based flow control: use credit-based flow control -- the receiver advertises its free capacity and the sender sends only up to that credit, replenished as the receiver drains -- so the sender is paced to the receiver and the buffer never overflows, rather than letting a sender dump a burst that overruns a bounded buffer and forces drops.")
    p.add_argument("--nocontrol", action="store_true")
    p.add_argument("--credit", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("capacity=%d  process_per_step=%d  to_send=%d  file=%s  (these are a fixture)"
          % (data["capacity"], data["process_per_step"], data["to_send"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.nocontrol:
        nocontrol_view(data)
    elif args.credit:
        credit_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
