"""Give the lock a fencing token and let storage reject stale ones -- a lock alone cannot stop a paused client's late write.

A distributed lock is supposed to guarantee that only one client at a time may write to a shared resource. It does not,
by itself, deliver that guarantee, because a lock is held under a LEASE -- a time-limited grant -- and a client can lose
the lease without knowing it. The classic way: client A holds the lock, then suffers a long stall (a stop-the-world
garbage-collection pause, a scheduling delay, a network partition) that outlasts the lease. The lock service, seeing the
lease expire, grants the lock to client B, who does its work. Then A resumes -- from A's own point of view no time has
passed and it still holds the lock -- and performs the write it was about to do. Now two clients have written to the
resource believing they had exclusive access, and A's write, based on a lease it no longer holds, can corrupt or
overwrite B's. The lock did its job at every instant; the stall is what broke the mutual exclusion, and no amount of
lock-checking by A can help, because A cannot know it was paused.

A fencing token fixes this at the RESOURCE, not the client. Every time the lock is granted, the lock service issues a
token that strictly increases -- A gets 33, B gets 34 -- and the client must include its token with every write. The
storage service remembers the highest token it has accepted and REFUSES any write whose token is not greater. So once B's
token-34 write lands, the storage's high-water mark is 34, and A's later write carrying the stale token 33 is rejected --
the resource itself enforces the ordering the lease intended. The client cannot be trusted to notice its own stall, but
the resource can be trusted to reject an out-of-date token, and that is the guarantee that actually holds.

The rule: a lock provides mutual exclusion only if a stalled holder can be fenced out, so the lock must issue
monotonically increasing tokens and the protected resource must check them, rejecting any write that does not carry a
token newer than the last one it honored. A lock without fencing is an optimization (it reduces contention) but not a
safety mechanism against delayed writers.

On this fixture three writes reach storage in order: A(token 33) writes 'x', B(token 34) writes 'y', then the stalled A
writes 'z' with its stale token 33. Without fencing, storage accepts every write and the final value is 'z' -- A's stale
write corrupted B's. With fencing, storage accepts 33 then 34, then rejects the second 33 (not greater than 34), so the
final value is 'y'. This computes both.

  --writes   each write attempt under no fencing (all accepted) vs fencing (stale token rejected), and the final value
  --tokens   why the token must be monotonic: the storage's high-water mark rises and never accepts an older token again
  --check    without fencing the stale write wins ('z'); with fencing the stale token is rejected and the correct value ('y') stands

The write attempts are the fixture; the fenced and unfenced outcomes are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "fencing.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run_unfenced(attempts):
    """No token check: storage accepts every write in order; the last write wins."""
    value = None
    log = []
    for a in attempts:
        value = a["value"]
        log.append((a["client"], a["token"], "accept", value))
    return value, log


def run_fenced(attempts):
    """Storage tracks the highest accepted token and rejects any write not strictly greater."""
    high_water = 0
    value = None
    log = []
    for a in attempts:
        if a["token"] > high_water:
            high_water = a["token"]
            value = a["value"]
            log.append((a["client"], a["token"], "accept", value))
        else:
            log.append((a["client"], a["token"], "REJECT (stale)", value))
    return value, log


# ----------------------------------------------------------------- printing

def writes_view(data):
    attempts = data["attempts"]
    uv, ulog = run_unfenced(attempts)
    fv, flog = run_fenced(attempts)
    print("WRITES — the stalled client A's late token-33 write, with and without fencing")
    print("-" * 66)
    print("  order of writes reaching storage: %s" % [(a["client"], a["token"], a["value"]) for a in attempts])
    print("-" * 66)
    print("  UNFENCED:")
    for c, t, res, v in ulog:
        print("    %s token %d -> %-14s (value now %r)" % (c, t, res, v))
    print("  final value = %r  <- A's stale write corrupted B's" % uv)
    print("  FENCED:")
    for c, t, res, v in flog:
        print("    %s token %d -> %-14s (value now %r)" % (c, t, res, v))
    print("  final value = %r  <- the stale token 33 was rejected" % fv)


def tokens_view(data):
    attempts = data["attempts"]
    print("TOKENS — the storage high-water mark only moves forward")
    print("-" * 58)
    high_water = 0
    print("  attempt      token   high-water before   decision")
    for a in attempts:
        decision = "accept (raises HW)" if a["token"] > high_water else "reject (<= HW)"
        before = high_water
        if a["token"] > high_water:
            high_water = a["token"]
        print("  %s writes %-3r  %-6d  %-18d  %s" % (a["client"], a["value"], a["token"], before, decision))
    print("-" * 58)
    print("  once the high-water mark reaches 34, no token <= 34 is ever accepted again.")


def check(data):
    print("SELF-TEST — without fencing the stale write wins; with fencing the stale token is rejected and the correct value stands")
    print("-" * 122)
    attempts = data["attempts"]
    uv, _ = run_unfenced(attempts)
    fv, flog = run_fenced(attempts)

    unfenced_accepts_stale = uv == attempts[-1]["value"]
    print("  unfenced: A's stale last write wins = %s (final %r)" % (unfenced_accepts_stale, uv))

    stale = attempts[-1]
    stale_rejected = any(res.startswith("REJECT") and c == stale["client"] and t == stale["token"] for c, t, res, v in flog)
    print("  fenced: the stale token-%d write is rejected = %s" % (stale["token"], stale_rejected))

    fenced_correct = fv == attempts[1]["value"]
    print("  fenced: the final value is B's write = %s (%r)" % (fenced_correct, fv))

    tokens_monotonic = attempts[1]["token"] > attempts[0]["token"]
    print("  the fencing tokens increase on each grant = %s (%d < %d)" % (tokens_monotonic, attempts[0]["token"], attempts[1]["token"]))

    outcomes_differ = uv != fv
    print("  fencing changes the outcome (lock alone was unsafe) = %s (%r vs %r)" % (outcomes_differ, uv, fv))

    ok = unfenced_accepts_stale and stale_rejected and fenced_correct and tokens_monotonic and outcomes_differ
    print("-" * 122)
    print("SELF-TEST %s  unfenced_accepts_stale=%s  stale_rejected=%s  fenced_correct=%s  tokens_monotonic=%s  outcomes_differ=%s"
          % ("PASS" if ok else "FAIL", unfenced_accepts_stale, stale_rejected, fenced_correct, tokens_monotonic, outcomes_differ))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fencing tokens: a leased distributed lock cannot stop a stalled holder from writing after its lease expired, so the lock must issue monotonically increasing tokens and the protected resource must reject any write whose token is not greater than the last it accepted, fencing out the stale writer.")
    p.add_argument("--writes", action="store_true")
    p.add_argument("--tokens", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("attempts=%s  file=%s  (the write order and tokens are a fixture)"
          % ([(a["client"], a["token"], a["value"]) for a in data["attempts"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.writes:
        writes_view(data)
    elif args.tokens:
        tokens_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
