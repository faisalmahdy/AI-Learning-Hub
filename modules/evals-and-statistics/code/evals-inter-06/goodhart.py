#!/usr/bin/env python3
"""Optimize a proxy metric and it stops measuring the target -- select on a held-out score.

An eval metric you can compute cheaply -- keyword overlap, answer length, a rubric of surface
checks -- is a proxy for the thing you actually want, which is quality a human would endorse.
The proxy is useful right up until you select or tune a system to maximize it: then the system
finds the cheap way to move the proxy without moving the target, and the proxy, now a target,
stops being a good proxy. This is Goodhart's law, and it is the difference between an eval that
ranks systems and an eval that gets gamed into shipping the worse one.

Three system variants are scored on the same cases by two metrics: a proxy (an automatic
surface score) and a target (a held-out true-quality score the systems were not tuned against).
The baseline is honest. One variant games the proxy -- it drives the proxy up while the target
falls below baseline. One variant genuinely improves -- both go up. Selecting the system with
the best proxy ships the gamed one, a regression against baseline on the metric that matters;
selecting on the held-out target ships the genuinely better one. The tell is per-variant
divergence: a variant whose proxy rose while its target fell has been gamed, and the proxy can
no longer be trusted to rank it.

  --scores     each variant's mean proxy and mean target, and the delta vs baseline
  --select     the naive proxy-argmax pick vs the target-argmax pick, and each one's true quality
  --check      the proxy pick is a target regression; the held-out pick is the true best

The per-case scores are the fixture; the means, deltas, and picks are computed here.
Deterministic; stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "runs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


# ------------------------------------------------------------- the two metrics per variant

def proxy_mean(variant):
    return mean([c["proxy"] for c in variant["cases"]])


def target_mean(variant):
    return mean([c["target"] for c in variant["cases"]])


def deltas_vs_baseline(data):
    """For each variant, its proxy and target change relative to the baseline variant."""
    variants = data["variants"]
    base = next(v for v in variants if v["id"] == data["baseline"])
    bp, bt = proxy_mean(base), target_mean(base)
    out = {}
    for v in variants:
        out[v["id"]] = {"proxy": proxy_mean(v), "target": target_mean(v),
                        "dproxy": proxy_mean(v) - bp, "dtarget": target_mean(v) - bt}
    return out, bp, bt


def is_gamed(d):
    """Gamed: the proxy rose but the target did not -- the metric moved without the quality."""
    return d["dproxy"] > 0 and d["dtarget"] <= 0


# ------------------------------------------------------------- the two selection rules

def select_by_proxy(data):
    """The naive rule: ship the variant with the highest proxy score."""
    return max(data["variants"], key=lambda v: (proxy_mean(v), v["id"]))["id"]


def select_by_target(data):
    """The held-out rule: ship the variant with the highest target score."""
    return max(data["variants"], key=lambda v: (target_mean(v), v["id"]))["id"]


# ----------------------------------------------------------------- printing

def scores_view(data):
    d, bp, bt = deltas_vs_baseline(data)
    print("SCORES — each variant's proxy and target, and the change vs baseline (%s)" % data["baseline"])
    print("-" * 66)
    print("  variant      proxy   target   dproxy   dtarget   gamed?")
    for v in data["variants"]:
        row = d[v["id"]]
        print("  %-11s %.3f   %.3f   %+.3f   %+.3f   %s"
              % (v["id"], row["proxy"], row["target"], row["dproxy"], row["dtarget"], is_gamed(row)))
    print("-" * 66)
    print("  a variant with dproxy up and dtarget down has gamed the proxy -- do not rank it by proxy.")


def select_view(data):
    d, _, _ = deltas_vs_baseline(data)
    by_p, by_t = select_by_proxy(data), select_by_target(data)
    print("SELECT — proxy-argmax vs target-argmax, and the true quality each ships")
    print("-" * 66)
    print("  select by proxy  -> %-11s  (true target %.3f, dtarget %+.3f)"
          % (by_p, d[by_p]["target"], d[by_p]["dtarget"]))
    print("  select by target -> %-11s  (true target %.3f, dtarget %+.3f)"
          % (by_t, d[by_t]["target"], d[by_t]["dtarget"]))
    print("-" * 66)
    print("  the proxy pick ships the gamed variant; the held-out pick ships the real improvement.")


def check(data):
    print("SELF-TEST — the proxy pick is a target regression; the held-out pick is the true best")
    print("-" * 66)
    d, bp, bt = deltas_vs_baseline(data)

    by_p = select_by_proxy(data)
    by_t = select_by_target(data)

    proxy_picks_gamed = is_gamed(d[by_p])
    print("  the proxy-argmax pick is a gamed variant = %s (%s: dproxy %+.3f, dtarget %+.3f)"
          % (proxy_picks_gamed, by_p, d[by_p]["dproxy"], d[by_p]["dtarget"]))

    proxy_regresses = d[by_p]["dtarget"] < 0
    print("  shipping the proxy pick REGRESSES true quality vs baseline = %s (dtarget %+.3f)"
          % (proxy_regresses, d[by_p]["dtarget"]))

    target_best = target_mean(next(v for v in data["variants"] if v["id"] == by_t)) == max(
        target_mean(v) for v in data["variants"])
    print("  the target-argmax pick has the highest true quality = %s (%s, target %.3f)"
          % (target_best, by_t, d[by_t]["target"]))

    picks_differ = by_p != by_t
    print("  the two rules disagree (the proxy would mislead you) = %s (%s vs %s)"
          % (picks_differ, by_p, by_t))

    target_improves = d[by_t]["dtarget"] > 0
    print("  the held-out pick actually improves on baseline = %s (dtarget %+.3f)"
          % (target_improves, d[by_t]["dtarget"]))

    ok = proxy_picks_gamed and proxy_regresses and target_best and picks_differ and target_improves
    print("-" * 66)
    print("SELF-TEST %s  proxy_gamed=%s  proxy_regresses=%s  target_best=%s  differ=%s  target_improves=%s"
          % ("PASS" if ok else "FAIL", proxy_picks_gamed, proxy_regresses, target_best, picks_differ, target_improves))
    return ok


def main():
    p = argparse.ArgumentParser(description="Goodhart: optimize a proxy and select on a held-out target.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--select", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    n = len(data["variants"][0]["cases"])
    print("variants=%d  cases=%d  baseline=%s  file=%s  (per-case scores are a fixture)"
          % (len(data["variants"]), n, data["baseline"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.select:
        select_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
