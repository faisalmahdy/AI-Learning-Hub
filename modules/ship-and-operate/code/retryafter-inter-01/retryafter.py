"""Wait the server's Retry-After, not your own backoff -- a server that says 'come back in 5s' means it, and guessing is worse.

When a server rate-limits or is overloaded, it does not just reject your request -- it usually tells you WHEN to come back.
An HTTP 429 (Too Many Requests) or 503 (Service Unavailable) response carries a Retry-After header: 'do not retry for N
seconds.' That header is the server speaking authoritatively about its own state -- it knows when the rate-limit window
resets, when the overloaded queue will have drained, when maintenance ends -- information the client cannot possibly have.
The correct client behavior is to honor it: wait exactly that long, then retry once.

The common mistake is to ignore the Retry-After header and fall back to the client's own generic retry policy -- fixed or
exponential backoff -- as if the 429 were an ordinary transient error. This is wrong in both directions. The client's
backoff is a blind guess at a delay the server already told it exactly, so it retries at the wrong times: too soon (before
the window resets, so every early retry is another 429 that the client's own retry storm is making worse -- it is
hammering a server that explicitly asked it to stop), and then, because backoff doubles, too late (overshooting well past
the moment the limit actually lifted, adding latency for no reason). A client that honored the header would have made ONE
retry, at the exact instant it could succeed. Ignoring the header thus costs both extra load on an already-struggling
server AND extra latency for the client -- the rare case where doing the disciplined thing is strictly better on every
axis.

There are caveats -- a Retry-After can be absurdly large or absent, so a sane client caps the honored wait and falls back
to bounded backoff when the header is missing, and adds a little jitter so many clients released at the same reset time do
not stampede together -- but the default must be to trust the server's own timing over a generic guess, because the server
knows its schedule and the client does not.

The rule: when a response carries a Retry-After header (on a 429 or 503), wait that duration before retrying instead of
applying the client's own backoff, because the server knows exactly when it will accept traffic again and the client's
generic backoff both retries too early -- adding load during the very window the server asked you to avoid -- and too late,
overshooting the moment the limit lifts.

On this fixture the server is limited until t=5 and returns Retry-After telling the client to wait. The honoring client
retries once at t=5 and succeeds -- 2 requests total. The ignoring client uses backoff 1,2,4: it retries at t=1 and t=3
(both still limited -> more 429s) and finally succeeds at t=7 -- 4 requests total, and later. This computes both.

  --timeline   each client's request times and responses: honor (retry at 5, done) vs ignore (retries at 1,3 fail, 7 ok)
  --cost       total requests, wasted 429 retries, and success time for each client -- honoring is fewer AND faster
  --check      ignoring the header makes extra requests during the limit and finishes later; honoring retries once at the reset

limit_until and backoff_schedule are the fixture; every request time, response, and count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "retryafter.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run(limit_until, honor, backoff):
    """Simulate a client retrying against a server limited until limit_until. Returns the list of (time, response)."""
    t = 0
    attempt = 0
    log = []
    while True:
        if t >= limit_until:
            log.append((t, "200 OK"))
            return log
        retry_after = limit_until - t          # the server tells the client exactly how long to wait
        log.append((t, "429 (Retry-After %d)" % retry_after))
        if honor:
            wait = retry_after                 # trust the server's own timing
        else:
            wait = backoff[min(attempt, len(backoff) - 1)]   # blind generic backoff
        t += wait
        attempt += 1
        if attempt > 20:
            return log


def requests_count(log):
    return len(log)


def success_time(log):
    return log[-1][0] if log[-1][1].startswith("200") else None


def wasted_429s(log):
    return sum(1 for _, resp in log if resp.startswith("429"))


# ----------------------------------------------------------------- printing

def timeline_view(data):
    lu, bo = data["limit_until"], data["backoff_schedule"]
    honor = run(lu, True, bo)
    ignore = run(lu, False, bo)
    print("TIMELINE — server limited until t=%d; honor Retry-After vs ignore it (backoff %s)" % (lu, bo))
    print("-" * 66)
    print("  HONOR the Retry-After header:")
    for t, resp in honor:
        print("    t=%-3d %s" % (t, resp))
    print("  IGNORE it, use own backoff:")
    for t, resp in ignore:
        print("    t=%-3d %s" % (t, resp))
    print("-" * 66)
    print("  honor succeeds at t=%d in %d requests; ignore at t=%d in %d requests."
          % (success_time(honor), requests_count(honor), success_time(ignore), requests_count(ignore)))


def cost_view(data):
    lu, bo = data["limit_until"], data["backoff_schedule"]
    honor = run(lu, True, bo)
    ignore = run(lu, False, bo)
    print("COST — requests, wasted 429 retries, and success time")
    print("-" * 58)
    print("  client   requests   wasted-429s   succeeds-at")
    print("  %-8s %-10d %-13d %d" % ("honor", requests_count(honor), wasted_429s(honor), success_time(honor)))
    print("  %-8s %-10d %-13d %d" % ("ignore", requests_count(ignore), wasted_429s(ignore), success_time(ignore)))
    print("-" * 58)
    print("  ignoring the header adds load during the limit and finishes later -- worse on both axes.")


def check(data):
    print("SELF-TEST — ignoring Retry-After makes extra requests during the limit and finishes later; honoring retries once at the reset")
    print("-" * 122)
    lu, bo = data["limit_until"], data["backoff_schedule"]
    honor = run(lu, True, bo)
    ignore = run(lu, False, bo)

    honor_two_requests = requests_count(honor) == 2
    print("  honor makes exactly 2 requests (one 429, one success) = %s" % honor_two_requests)

    honor_retries_at_reset = honor[-1][0] == lu
    print("  honor's retry lands exactly at the reset t=%d = %s" % (lu, honor_retries_at_reset))

    ignore_more_requests = requests_count(ignore) > requests_count(honor)
    print("  ignore makes more requests than honor = %s (%d vs %d)" % (ignore_more_requests, requests_count(ignore), requests_count(honor)))

    ignore_retries_while_limited = sum(1 for t, r in ignore[1:] if r.startswith("429")) > 0
    early = [t for t, r in ignore if r.startswith("429") and t > 0]
    print("  ignore retries WHILE still limited (extra 429s) = %s (at t=%s, all < %d)" % (ignore_retries_while_limited, early, lu))

    honor_finishes_no_later = success_time(honor) <= success_time(ignore)
    print("  honor finishes no later than ignore = %s (t=%d vs t=%d)" % (honor_finishes_no_later, success_time(honor), success_time(ignore)))

    ok = honor_two_requests and honor_retries_at_reset and ignore_more_requests and ignore_retries_while_limited and honor_finishes_no_later
    print("-" * 122)
    print("SELF-TEST %s  honor_two_requests=%s  honor_retries_at_reset=%s  ignore_more_requests=%s  ignore_retries_while_limited=%s  honor_finishes_no_later=%s"
          % ("PASS" if ok else "FAIL", honor_two_requests, honor_retries_at_reset, ignore_more_requests, ignore_retries_while_limited, honor_finishes_no_later))
    return ok


def main():
    p = argparse.ArgumentParser(description="Honor Retry-After: when a response carries a Retry-After header (on a 429 or 503), wait that duration before retrying instead of applying the client's own backoff, because the server knows exactly when it will accept traffic again and generic backoff both retries too early (adding load during the window the server asked you to avoid) and too late (overshooting the moment the limit lifts).")
    p.add_argument("--timeline", action="store_true")
    p.add_argument("--cost", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("limit_until=%d  backoff_schedule=%s  file=%s  (the limit window and backoff are a fixture)"
          % (data["limit_until"], data["backoff_schedule"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.timeline:
        timeline_view(data)
    elif args.cost:
        cost_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
