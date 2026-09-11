#!/usr/bin/env python3
"""The KV cache: reuse the past instead of recomputing it -- and match it exactly.

Generating a token means running attention over the whole sequence so far. Do it
naively and every new token recomputes the keys and values for the entire prefix,
so producing n tokens costs on the order of n-squared key/value computations. The
KV cache saves each position's key and value the first time and reuses them, so
each step computes just one new pair -- linear, not quadratic. The one rule: the
cached generation must produce byte-identical outputs to the from-scratch version,
and the classic bug (attend before appending the current token's key/value) breaks
exactly that, silently, because it still runs and still returns a vector.

  --recompute     the from-scratch cost: keys/values computed at each step
  --cached        the cache path: outputs, and the cost saved
  --bug           the off-by-one cache that attends before appending the new token
  --check         cached matches from-scratch exactly; the bug does not; cost is linear vs quadratic

Reuses the attention idea from attention-inter-01, generating left to right.
Stdlib only (math). No model -- token vectors are a fixture. Deterministic.
"""
import argparse
import json
import sys
from math import exp, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEQ = HERE / "seq.json"


def load():
    return json.loads(SEQ.read_text(encoding="utf-8"))["emb"]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def softmax(xs):
    m = max(xs)
    e = [exp(x - m) for x in xs]
    s = sum(e)
    return [x / s for x in e]


def attend(query, keys, values):
    """One position's attention over a set of key/value vectors: scaled dot-product
    scores, softmax, weighted blend of values."""
    d = len(query)
    sc = [dot(query, k) / sqrt(d) for k in keys]
    w = softmax(sc)
    return [sum(w[j] * values[j][c] for j in range(len(values))) for c in range(d)]


# ------------------------------------------------------- from-scratch generation

def recompute(emb):
    """No cache: at each step t, (re)build keys/values for the whole prefix 0..t and
    attend. Returns the per-step outputs and the number of key/value builds."""
    outputs, kv_builds = [], 0
    for t in range(len(emb)):
        keys = values = emb[: t + 1]           # rebuilt from scratch every step
        kv_builds += t + 1                      # ...at a cost of t+1 KV each step
        outputs.append(attend(emb[t], keys, values))
    return outputs, kv_builds


# ------------------------------------------------------------- cached generation

def cached(emb):
    """With a KV cache: append the new token's key/value, then attend over the cache.
    One KV build per step. Must match recompute() exactly."""
    ck, cv, outputs, kv_builds = [], [], [], 0
    for t in range(len(emb)):
        ck.append(emb[t])                       # append current token FIRST
        cv.append(emb[t])
        kv_builds += 1                          # one new KV per step
        outputs.append(attend(emb[t], ck, cv))
    return outputs, kv_builds


def cached_buggy(emb):
    """THE BUG: attend over the cache BEFORE appending the current token, so position
    t never attends to itself. Still runs, still returns a vector -- just wrong."""
    ck, cv, outputs = [], [], []
    for t in range(len(emb)):
        if not ck:                              # t=0: nothing cached yet
            outputs.append(list(emb[t]))        # degenerate: emit the token as-is
        else:
            outputs.append(attend(emb[t], ck, cv))   # attends 0..t-1, misses self
        ck.append(emb[t])                       # append AFTER (the off-by-one)
        cv.append(emb[t])
    return outputs, 0


# ---------------------------------------------------------------- comparison

def close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for u, v in zip(a, b) for x, y in zip(u, v))


# ------------------------------------------------------------------- printing

def recompute_view(emb):
    _, builds = recompute(emb)
    print("FROM SCRATCH — rebuild keys/values for the whole prefix every step")
    print("-" * 60)
    running = 0
    for t in range(len(emb)):
        running += t + 1
        print("  step %d: attend over %d position(s), rebuilt %d KV  (cumulative %d)"
              % (t, t + 1, t + 1, running))
    print("-" * 60)
    print("  total KV builds = %d for %d tokens -- grows with the square of length." % (builds, len(emb)))


def cached_view(emb):
    outs, builds = cached(emb)
    ref, rbuilds = recompute(emb)
    print("CACHED — append one KV per step, reuse the rest")
    print("-" * 60)
    for t in range(len(emb)):
        print("  step %d: 1 new KV, attend over %d cached  -> output matches scratch: %s"
              % (t, t + 1, close([outs[t]], [ref[t]])))
    print("-" * 60)
    print("  total KV builds = %d vs %d from scratch -- linear, not quadratic." % (builds, rbuilds))


def bug_view(emb):
    ref, _ = recompute(emb)
    bug, _ = cached_buggy(emb)
    print("THE BUG — attend before appending the current token (off-by-one)")
    print("-" * 60)
    for t in range(len(emb)):
        print("  step %d: matches from-scratch = %s" % (t, close([bug[t]], [ref[t]])))
    print("-" * 60)
    print("  every step is wrong: position t never attends to itself, so its output")
    print("  is missing its own token -- and nothing errored to tell you.")


def check(emb):
    print("SELF-TEST — cached matches scratch exactly; the bug does not; cost is linear")
    print("-" * 60)
    ref, rbuilds = recompute(emb)
    good, gbuilds = cached(emb)
    bug, _ = cached_buggy(emb)
    n = len(emb)

    matches = all(close([good[t]], [ref[t]]) for t in range(n))
    print("  cached output == from-scratch output at every step = %s" % matches)

    bug_wrong = any(not close([bug[t]], [ref[t]]) for t in range(n))
    print("  the off-by-one cache differs from from-scratch = %s" % bug_wrong)

    linear = gbuilds == n
    quadratic = rbuilds == n * (n + 1) // 2
    print("  cached KV builds = %d (== n) ; scratch = %d (== n(n+1)/2) = %s"
          % (gbuilds, rbuilds, linear and quadratic))

    saved = rbuilds > gbuilds
    print("  the cache does strictly less work = %s (%d < %d)" % (saved, gbuilds, rbuilds))

    det = cached(emb)[0] == cached(emb)[0]
    ok = matches and bug_wrong and linear and quadratic and saved and det
    print("-" * 60)
    print("SELF-TEST %s  matches=%s  bug_wrong=%s  linear=%s  quadratic=%s  saved=%s"
          % ("PASS" if ok else "FAIL", matches, bug_wrong, linear, quadratic, saved))
    return ok


def main():
    p = argparse.ArgumentParser(description="A KV cache, and the off-by-one that breaks it.")
    p.add_argument("--recompute", action="store_true")
    p.add_argument("--cached", action="store_true")
    p.add_argument("--bug", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    emb = load()
    print("seq_len=%d  dim=%d  file=%s  (token vectors are a fixture)"
          % (len(emb), len(emb[0]), SEQ.name))
    print("")

    if args.check:
        return 0 if check(emb) else 1
    if args.recompute:
        recompute_view(emb)
    elif args.cached:
        cached_view(emb)
    elif args.bug:
        bug_view(emb)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
