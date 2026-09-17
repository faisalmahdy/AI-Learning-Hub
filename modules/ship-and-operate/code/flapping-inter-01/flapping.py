"""Use hysteresis (fire at a high threshold, clear at a lower one) for an alert on a noisy metric, not a single threshold -- a metric that hovers near one threshold crosses it up and down repeatedly, so a single-threshold alert fires and clears on every oscillation and pages on-call many times for one situation, while a two-threshold alert fires once and holds through the noise.

An alert compares a metric to a threshold and fires when the metric crosses it. That is fine for a metric that moves decisively. It fails for a noisy metric that sits near the level that matters, because such a metric crosses the threshold many times in quick succession -- up a little, down a little, up again.

A single-threshold alert reads each up-crossing as a fresh incident. It fires, the value dips below and it clears, the value rises and it fires again, so a single sustained-ish condition generates a page per wobble. That is flapping, and its real cost is not the pages themselves but the fatigue: an alert that cries several times an hour is an alert people mute, and a muted alert misses the outage it was for.

Hysteresis splits the one threshold into two: fire only when the metric exceeds a HIGH threshold, and clear only when it drops below a LOWER one. Between the two thresholds is a dead band, and oscillations that stay inside it do not toggle the alert. The alert fires once when the metric genuinely climbs past the high mark and stays fired until it truly recovers past the low mark -- one page for one condition. A 'for duration' rule (require the breach to hold for several samples before firing) is the other common fix; both stop a single crossing from meaning anything.

On this fixture the samples oscillate around a threshold of 80. A single threshold fires 4 times as the metric bobs across it. Hysteresis with a high of 84 and a low of 76 fires once: the samples between 76 and 84 fall in the dead band and are ignored. This computes both and lists the in-band samples that cause the flapping.

  --single      single-threshold alert: fires on every up-crossing, so it flaps
  --hysteresis  two-threshold alert: fires once and holds through the oscillation
  --check       the single-threshold alert flaps (multiple fires) while hysteresis fires once for the same data, and the in-band samples are what toggle the naive alert

the samples and the thresholds are the fixture; each alert's fire count and the in-band samples are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "flapping.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def single_threshold_fires(samples, threshold):
    """Count fire events for a single-threshold alert: each clear-to-fire crossing is one page."""
    firing, fires = False, 0
    for s in samples:
        if not firing and s > threshold:
            firing, fires = True, fires + 1
        elif firing and s <= threshold:
            firing = False
    return fires


def hysteresis_fires(samples, high, low):
    """Count fire events for a hysteresis alert: fire above high, clear below low, ignore the band between."""
    firing, fires = False, 0
    for s in samples:
        if not firing and s > high:
            firing, fires = True, fires + 1
        elif firing and s < low:
            firing = False
    return fires


def in_band(samples, high, low):
    """The samples that sit in the dead band -- they toggle a single threshold but not hysteresis."""
    return [s for s in samples if low <= s <= high]


# ----------------------------------------------------------------- printing

def _trace(samples, threshold):
    firing = False
    out = []
    for s in samples:
        if not firing and s > threshold:
            firing = True
            out.append("%d FIRE" % s)
        elif firing and s <= threshold:
            firing = False
            out.append("%d clear" % s)
        else:
            out.append("%d" % s)
    return out


def single_view(d):
    s, t = d["samples"], d["threshold"]
    print("SINGLE — one threshold at %d" % t)
    print("-" * 64)
    print("  trace: %s" % _trace(s, t))
    print("  fire events: %d" % single_threshold_fires(s, t))
    print("-" * 64)
    print("  the metric bobs across the threshold, so the alert pages again and again")


def hysteresis_view(d):
    s, hi, lo = d["samples"], d["high"], d["low"]
    print("HYSTERESIS — fire above %d, clear below %d (dead band %d..%d)" % (hi, lo, lo, hi))
    print("-" * 64)
    print("  fire events: %d" % hysteresis_fires(s, hi, lo))
    print("  in-band samples (ignored): %s" % in_band(s, hi, lo))
    print("-" * 64)
    print("  oscillations inside the band do not toggle the alert, so it fires once and holds")


def check(d):
    print("SELF-TEST — the single-threshold alert flaps while hysteresis fires once for the same data, and the in-band samples are what toggle the naive alert")
    print("-" * 112)
    s, t, hi, lo = d["samples"], d["threshold"], d["high"], d["low"]

    single = single_threshold_fires(s, t)
    single_flaps = single >= 3
    print("  single-threshold alert flaps (fires many times) = %s (%d fires)" % (single_flaps, single))

    hyst = hysteresis_fires(s, hi, lo)
    hysteresis_stable = hyst == 1
    print("  hysteresis alert fires once for the same data = %s (%d fire)" % (hysteresis_stable, hyst))

    hysteresis_fewer = hyst < single
    print("  hysteresis fires fewer times than the single threshold = %s (%d < %d)" % (hysteresis_fewer, hyst, single))

    band = in_band(s, hi, lo)
    band_causes_flap = len(band) >= 2
    print("  several samples fall in the dead band that toggles the naive alert = %s (%s)" % (band_causes_flap, band))

    ok = (single_flaps and hysteresis_stable and hysteresis_fewer and band_causes_flap)
    print("-" * 112)
    print("SELF-TEST %s  single_flaps=%s  hysteresis_stable=%s  hysteresis_fewer=%s  band_causes_flap=%s"
          % ("PASS" if ok else "FAIL", single_flaps, hysteresis_stable, hysteresis_fewer, band_causes_flap))
    return ok


def main():
    p = argparse.ArgumentParser(description="Alert hysteresis: alert on a noisy metric with two thresholds -- fire above a high mark, clear below a lower one -- rather than a single threshold, because a metric hovering near one threshold crosses it repeatedly and makes a single-threshold alert flap, paging on-call once per oscillation until they mute it; hysteresis (or a 'for duration' rule) fires once when the condition genuinely begins and holds through the noise.")
    p.add_argument("--single", action="store_true")
    p.add_argument("--hysteresis", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("samples=%d  threshold=%d  high=%d  low=%d  file=%s"
          % (len(d["samples"]), d["threshold"], d["high"], d["low"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.single:
        single_view(d)
    elif args.hysteresis:
        hysteresis_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
