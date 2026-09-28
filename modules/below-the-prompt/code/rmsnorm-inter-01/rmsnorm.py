#!/usr/bin/env python3
"""RMSNorm normalizes each token across its features -- normalize across tokens and you leak.

Every layer of a transformer reads the residual stream, and before it does it normalizes,
because after a few layers one token's activation vector can grow ten times another's and
whatever reads them next would be dominated by magnitude instead of content. RMSNorm is the
fix: divide each token's feature vector by its own root-mean-square, times a learned gain, so
every token arrives at unit scale and the next layer compares content, not loudness.

The whole correctness of it is the axis. RMSNorm is per-token: token i's normalized output is
a function of token i's features alone. Normalize across tokens instead -- divide each feature
by the RMS of that feature over all positions -- and the numbers still look normalized, but
token i's output now depends on every other token's value in that feature, including tokens
that come after it. In a causal language model that is a leak from the future into the past:
the representation of position 0 changes when you edit position 1. This builds both, shows the
correct one gives every token unit RMS and depends on nothing but itself, and shows the buggy
one couples the positions -- the planted bug is the transposed axis.

  --stream     the residual stream, each token's RMS, and both normalizations
  --leak       perturb one token and watch which normalization changes another token's output
  --check      per-token norm gives unit-RMS, self-only rows; the across-token bug leaks

The residual stream is the fixture; the RMS math is computed. Deterministic; stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "stream.json"
EPS = 1e-6


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rms(vec):
    return math.sqrt(sum(x * x for x in vec) / len(vec) + EPS)


# ------------------------------------------------------------- the correct norm: per token (row)

def rmsnorm_per_token(stream, gain):
    """Correct: each token divided by its OWN rms, times the learned per-feature gain."""
    out = []
    for row in stream:
        r = rms(row)
        out.append([(x / r) * g for x, g in zip(row, gain)])
    return out


# ------------------------------------------------------------- the bug: per feature (column)

def rmsnorm_across_tokens(stream, gain):
    """The bug: each feature divided by the rms of that feature ACROSS all tokens -- couples them."""
    n_tok = len(stream)
    n_feat = len(stream[0])
    col_rms = [rms([stream[t][j] for t in range(n_tok)]) for j in range(n_feat)]
    out = []
    for row in stream:
        out.append([(x / col_rms[j]) * gain[j] for j, x in enumerate(row)])
    return out


# ------------------------------------------------------------- the leak test

def perturb(stream, token, delta):
    """Return a copy of the stream with `delta` added to every feature of one token."""
    return [[x + (delta if t == token else 0.0) for x in row] for t, row in enumerate(stream)]


def row_changed(a, b, i):
    """Did token i's output row change between two normalizations?"""
    return any(abs(a[i][j] - b[i][j]) > 1e-9 for j in range(len(a[i])))


# ----------------------------------------------------------------- printing

def stream_view(data):
    stream, gain = data["stream"], data["gain"]
    per = rmsnorm_per_token(stream, gain)
    across = rmsnorm_across_tokens(stream, gain)
    print("STREAM — %d tokens x %d features; gain %s" % (len(stream), len(stream[0]), gain))
    print("-" * 70)
    print("  token  raw                         rms    per-token-rms(out)  across-rms(out)")
    for t, row in enumerate(stream):
        print("  t%d     %-26s %.3f  %.3f              %.3f"
              % (t, str(row), rms(row), rms(per[t]), rms(across[t])))
    print("-" * 70)
    print("  correct per-token norm puts every token at rms 1; the across-token bug does not.")


def leak_view(data):
    stream, gain = data["stream"], data["gain"]
    tok, delta = data["perturb_token"], data["perturb_delta"]
    base_per = rmsnorm_per_token(stream, gain)
    base_across = rmsnorm_across_tokens(stream, gain)
    pert = perturb(stream, tok, delta)
    new_per = rmsnorm_per_token(pert, gain)
    new_across = rmsnorm_across_tokens(pert, gain)
    other = [i for i in range(len(stream)) if i != tok][0]
    print("LEAK — add %.1f to token t%d, then check whether OTHER tokens' outputs move" % (delta, tok))
    print("-" * 70)
    print("  per-token norm: did t%d's output change? %s" % (other, row_changed(base_per, new_per, other)))
    print("  across-token bug: did t%d's output change? %s" % (other, row_changed(base_across, new_across, other)))
    print("-" * 70)
    print("  editing one token must not move another's normalization -- only the bug does.")


def check(data):
    print("SELF-TEST — per-token norm is unit-rms and self-only; the across-token bug leaks")
    print("-" * 70)
    stream, gain = data["stream"], data["gain"]

    # gain of 1.0 isolates the normalization; unit-rms should hold before the gain is applied
    ones = [1.0] * len(gain)
    per_unit = rmsnorm_per_token(stream, ones)
    unit_rms = all(abs(rms(row) - 1.0) < 1e-6 for row in per_unit)
    print("  every token has unit rms after per-token norm = %s (%s)"
          % (unit_rms, [round(rms(r), 3) for r in per_unit]))

    across_unit = rmsnorm_across_tokens(stream, ones)
    across_not_unit = any(abs(rms(row) - 1.0) > 1e-3 for row in across_unit)
    print("  the across-token bug does NOT give unit-rms tokens = %s (%s)"
          % (across_not_unit, [round(rms(r), 3) for r in across_unit]))

    tok, delta = data["perturb_token"], data["perturb_delta"]
    other = [i for i in range(len(stream)) if i != tok][0]
    base_per, base_across = rmsnorm_per_token(stream, gain), rmsnorm_across_tokens(stream, gain)
    pert = perturb(stream, tok, delta)
    new_per, new_across = rmsnorm_per_token(pert, gain), rmsnorm_across_tokens(pert, gain)

    per_no_leak = not row_changed(base_per, new_per, other)
    print("  per-token norm: editing t%d leaves t%d unchanged (no leak) = %s" % (tok, other, per_no_leak))

    across_leaks = row_changed(base_across, new_across, other)
    print("  across-token bug: editing t%d CHANGES t%d (a leak) = %s" % (tok, other, across_leaks))

    ok = unit_rms and across_not_unit and per_no_leak and across_leaks
    print("-" * 70)
    print("SELF-TEST %s  unit_rms=%s  across_not_unit=%s  per_no_leak=%s  across_leaks=%s"
          % ("PASS" if ok else "FAIL", unit_rms, across_not_unit, per_no_leak, across_leaks))
    return ok


def main():
    p = argparse.ArgumentParser(description="RMSNorm per token vs the across-token axis bug.")
    p.add_argument("--stream", action="store_true")
    p.add_argument("--leak", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tokens=%d  features=%d  file=%s  (the residual stream is a fixture; rms is computed)"
          % (len(data["stream"]), len(data["stream"][0]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stream:
        stream_view(data)
    elif args.leak:
        leak_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
