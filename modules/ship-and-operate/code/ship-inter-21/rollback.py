"""Keep the old version warm for an instant flip, or rolling back means redeploying while the bad version serves.

A canary limits the BLAST RADIUS of a bad release -- how many users see it -- by rolling out to a slice first.
This is a different lever: the SPEED of rollback once a bad version is live to everyone. The two costs are not the
same. However you deploy, you pay a detection window: the bad version serves every request from the moment it ships
until monitoring notices, and you cannot roll back what you have not yet detected. That window is unavoidable and
shared. What is NOT shared is how long the rollback itself takes, and that is set entirely by whether the previous
version is still runnable.

In-place deployment overwrites the old version -- same servers, new binary -- so once it is bad, the old version
is gone. Rolling back means deploying AGAIN from scratch: rebuild, ship, restart, warm up, all of which takes
minutes, and the bad version keeps serving the whole time. Blue-green keeps the old version running untouched in a
second environment and merely points traffic at the new one; rolling back is flipping the pointer back, which takes
seconds. Same detection, wildly different recovery: the bad version's total airtime is detect + redeploy for
in-place, detect + flip for blue-green, and the difference is the rollback time times the request rate.

On this fixture 100 requests per second hit a bad version detected after 30 seconds. In-place rollback needs a
300-second redeploy, so the bad version serves for 330 seconds -- 33,000 bad requests. Blue-green flips in 2
seconds, so it serves for 32 seconds -- 3,200 bad requests. The 30-second detection window (3,000 requests) is
shared; the rollback window is where blue-green saves 29,800 requests. This computes both.

  --airtime    how long the bad version serves and how many bad requests each strategy allows
  --split      the shared detection cost vs the rollback cost, so the win is attributed correctly
  --check      detection is shared; in-place redeploys slowly; blue-green flips fast; the win is rate*(redeploy-flip)

The rate and timings are the fixture; every count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "rollback.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def airtime(detect_s, rollback_s):
    """Seconds the bad version serves: the detection window plus the rollback time."""
    return detect_s + rollback_s


def bad_requests(rate, detect_s, rollback_s):
    """Requests served by the bad version = rate * its airtime."""
    return rate * airtime(detect_s, rollback_s)


# ----------------------------------------------------------------- printing

def airtime_view(data):
    rate, d, redeploy, flip = data["rate"], data["detect_s"], data["redeploy_s"], data["flip_s"]
    print("AIRTIME — how long the bad version serves and how many requests it poisons")
    print("-" * 66)
    print("  strategy     rollback   airtime      bad requests")
    print("  in-place     %4ds      %4ds        %d" % (redeploy, airtime(d, redeploy), bad_requests(rate, d, redeploy)))
    print("  blue-green   %4ds      %4ds        %d" % (flip, airtime(d, flip), bad_requests(rate, d, flip)))
    print("-" * 66)
    print("  same detection, but in-place keeps serving bad for the whole redeploy; blue-green flips out.")


def split_view(data):
    rate, d, redeploy, flip = data["rate"], data["detect_s"], data["redeploy_s"], data["flip_s"]
    detection_cost = rate * d
    print("SPLIT — shared detection cost vs the rollback cost that blue-green cuts")
    print("-" * 66)
    print("  detection window (shared):   %ds  ->  %d bad requests either way" % (d, detection_cost))
    print("  in-place rollback:           %ds  ->  %d bad requests" % (redeploy, rate * redeploy))
    print("  blue-green rollback:         %ds  ->  %d bad requests" % (flip, rate * flip))
    print("-" * 66)
    print("  blue-green saves %d bad requests: the rollback window shrinks from %ds to %ds." % (rate * (redeploy - flip), redeploy, flip))


def check(data):
    print("SELF-TEST — detection is shared; in-place redeploys slowly; blue-green flips fast; win is rate*(redeploy-flip)")
    print("-" * 108)
    rate, d, redeploy, flip = data["rate"], data["detect_s"], data["redeploy_s"], data["flip_s"]

    detection_shared = bad_requests(rate, d, 0) == rate * d
    print("  the detection window costs the same either way = %s (%d requests)" % (detection_shared, rate * d))

    inplace_rollback_slow = redeploy > 10 * flip
    print("  in-place rollback is far slower than a flip = %s (%ds > %ds)" % (inplace_rollback_slow, redeploy, flip))

    bluegreen_serves_fewer = bad_requests(rate, d, flip) < bad_requests(rate, d, redeploy)
    print("  blue-green serves fewer bad requests = %s (%d < %d)" % (bluegreen_serves_fewer, bad_requests(rate, d, flip), bad_requests(rate, d, redeploy)))

    win_is_rollback_gap = (bad_requests(rate, d, redeploy) - bad_requests(rate, d, flip)) == rate * (redeploy - flip)
    print("  the saving is exactly rate*(redeploy - flip) = %s (%d = %d*%d)" % (win_is_rollback_gap, bad_requests(rate, d, redeploy) - bad_requests(rate, d, flip), rate, redeploy - flip))

    detection_still_paid = bad_requests(rate, d, flip) > 0
    print("  blue-green still pays the detection window (rollback speed is not detection) = %s (%d > 0)" % (detection_still_paid, bad_requests(rate, d, flip)))

    ok = detection_shared and inplace_rollback_slow and bluegreen_serves_fewer and win_is_rollback_gap and detection_still_paid
    print("-" * 108)
    print("SELF-TEST %s  detection_shared=%s  inplace_rollback_slow=%s  bluegreen_serves_fewer=%s  win_is_rollback_gap=%s  detection_still_paid=%s"
          % ("PASS" if ok else "FAIL", detection_shared, inplace_rollback_slow, bluegreen_serves_fewer, win_is_rollback_gap, detection_still_paid))
    return ok


def main():
    p = argparse.ArgumentParser(description="Blue-green keeps the old version warm so rollback is an instant traffic flip, not a slow redeploy while the bad version serves.")
    p.add_argument("--airtime", action="store_true")
    p.add_argument("--split", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("rate=%d req/s  detect=%ds  redeploy=%ds  flip=%ds  file=%s  (the timings are a fixture)"
          % (data["rate"], data["detect_s"], data["redeploy_s"], data["flip_s"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.airtime:
        airtime_view(data)
    elif args.split:
        split_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
