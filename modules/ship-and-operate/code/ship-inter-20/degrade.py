"""Fall back to the stale cache when a dependency is down, or every request during the outage just fails.

A service that reads from a downstream dependency has to decide what to do when that dependency is unavailable.
The default is to fail: the read errors, so the request errors, and for the whole outage the service returns
nothing. But the service often does not NEED a live read -- it needs a good-enough answer, and the last value
it successfully fetched is usually still good enough. Failing every request throws away that fallback and
couples your availability to the dependency's: if the dependency is down 40% of the window, you are down 40%
of the window, even though you were holding a perfectly usable recent value the whole time.

Graceful degradation serves that value. Cache the last successful read; when the dependency is down, return
the cached value instead of an error, labeled with how stale it is. Availability now depends on YOUR cache,
not the dependency's uptime, so a dependency outage becomes a bounded staleness rather than an outage of your
own. The staleness is capped by the outage length -- the value can only be as old as the time since the last
successful fetch -- and you decide whether that is acceptable per read (a price quote, no; a config value,
almost always). Serving slightly stale beats serving nothing for the vast majority of reads.

On this fixture the dependency is up for 3 ticks, down for 4, then up for 3. Without a fallback, the 4 down-tick
requests fail: 6 of 10 served, 60% availability. With a stale-cache fallback, all 10 are served -- 100%
availability -- and the value served during the outage is at most 4 ticks stale. This computes both.

  --serve      each tick's outcome under no-fallback vs stale-cache fallback, with the staleness served
  --summary    availability and worst-case staleness for each policy
  --check      no fallback loses availability during the outage; the fallback serves all with bounded staleness

The uptime pattern is the fixture; every outcome is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "uptime.json"


def serve(status):
    """Walk the ticks; track the last up-tick as the cache. Return per-tick (up, served_no_fb, served_fb, staleness)."""
    last_good = None
    out = []
    for t, up in enumerate(status):
        if up:
            last_good = t
        served_no_fb = bool(up)
        served_fb = up or (last_good is not None)      # fallback serves if the cache is warm
        staleness = 0 if up else (t - last_good if last_good is not None else None)
        out.append((up, served_no_fb, served_fb, staleness))
    return out


def availability(rows, index):
    served = sum(1 for r in rows if r[index])
    return served / len(rows)


def max_staleness(rows):
    ages = [r[3] for r in rows if not r[0] and r[3] is not None]
    return max(ages) if ages else 0


# ----------------------------------------------------------------- printing

def serve_view(data):
    rows = serve(data["status"])
    print("SERVE — per tick: dependency status, and what each policy returns")
    print("-" * 66)
    print("  tick  dep    no-fallback     stale-cache fallback")
    for t, (up, snf, sfb, stale) in enumerate(rows):
        nf = "fresh" if up else "FAIL"
        fb = "fresh" if up else ("stale (%d old)" % stale if sfb else "cold, fail")
        print("  %2d    %-4s   %-13s   %s" % (t, "up" if up else "DOWN", nf, fb))
    print("-" * 66)
    print("  during the outage no-fallback returns nothing; the fallback returns the cached value.")


def summary_view(data):
    rows = serve(data["status"])
    print("SUMMARY — availability and worst-case staleness per policy")
    print("-" * 66)
    print("  no fallback:    availability %3.0f%%   (fails every down-tick)" % (100 * availability(rows, 1)))
    print("  stale fallback: availability %3.0f%%   worst staleness %d ticks" % (100 * availability(rows, 2), max_staleness(rows)))
    print("-" * 66)
    print("  the fallback trades a bounded staleness for the availability the outage would have cost.")


def check(data):
    print("SELF-TEST — no fallback loses availability during the outage; the fallback serves all with bounded staleness")
    print("-" * 108)
    status = data["status"]
    rows = serve(status)
    outage = status.count(0)

    no_fallback_loses = availability(rows, 1) < 1.0
    print("  no-fallback availability is below 100%% = %s (%.0f%%)" % (no_fallback_loses, 100 * availability(rows, 1)))

    fallback_full = availability(rows, 2) == 1.0
    print("  the stale-cache fallback serves every request = %s (%.0f%%)" % (fallback_full, 100 * availability(rows, 2)))

    fallback_serves_stale = any(not r[0] and r[3] and r[3] > 0 for r in rows)
    print("  the fallback serves some stale values during the outage = %s" % fallback_serves_stale)

    staleness_bounded = max_staleness(rows) <= outage
    print("  worst staleness is bounded by the outage length = %s (%d <= %d)" % (staleness_bounded, max_staleness(rows), outage))

    fresh_when_up = all(r[3] == 0 for r in rows if r[0])
    print("  when the dependency is up, served values are fresh (0 stale) = %s" % fresh_when_up)

    ok = no_fallback_loses and fallback_full and fallback_serves_stale and staleness_bounded and fresh_when_up
    print("-" * 108)
    print("SELF-TEST %s  no_fallback_loses=%s  fallback_full=%s  fallback_serves_stale=%s  staleness_bounded=%s  fresh_when_up=%s"
          % ("PASS" if ok else "FAIL", no_fallback_loses, fallback_full, fallback_serves_stale, staleness_bounded, fresh_when_up))
    return ok


def main():
    p = argparse.ArgumentParser(description="Serve the last-known-good cached value when a dependency is down (graceful degradation).")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("ticks=%d  down_ticks=%d  file=%s  (the uptime pattern is a fixture)"
          % (len(data["status"]), data["status"].count(0), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.serve:
        serve_view(data)
    elif args.summary:
        summary_view(data)
    else:
        p.print_help()
        return 2
    return 0


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
