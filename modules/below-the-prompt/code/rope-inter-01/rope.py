#!/usr/bin/env python3
"""RoPE rotates q and k by their position -- so attention sees only RELATIVE position.

A transformer's attention score is a dot product between a query and a key. On its own
it carries no notion of where each token sits in the sequence. Rotary position embedding
(RoPE) adds that notion in the cleanest possible way: rotate the query vector by an angle
proportional to its position m, and the key vector by an angle proportional to its
position n. Because a dot product of two rotated vectors depends only on the DIFFERENCE
of their rotation angles, the score between query-at-m and key-at-n comes out depending
only on the relative offset n - m -- not on where either token sits absolutely. That is
exactly what you want: "three tokens back" should mean the same thing at the start of a
document and in the middle of it.

The instructive wrong way is to encode position by ADDING a position vector to q and k
(the pre-RoPE, absolute style). Then the dot product picks up cross terms that depend on
the absolute m and n, so the same relative offset scores differently at different
absolute positions -- the invariance is gone. This measures both: RoPE's relative-only
score, and the additive scheme breaking it.

  --scores      RoPE attention score for each (m, n) pair, grouped by offset
  --additive    the same pairs under additive position encoding -- offset no longer enough
  --check       RoPE depends only on n-m; additive does not; rotation preserves norm

Stdlib only. Deterministic.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "vectors.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- rotation + scoring

def rotate(v, angle):
    """Rotate a 2D vector by `angle` radians."""
    c, s = math.cos(angle), math.sin(angle)
    return [v[0] * c - v[1] * s, v[0] * s + v[1] * c]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def norm(v):
    return math.sqrt(dot(v, v))


def rope_score(q, k, m, n, theta):
    """RoPE: rotate q by m*theta, k by n*theta, then dot. Depends only on (n-m)."""
    return dot(rotate(q, m * theta), rotate(k, n * theta))


def additive_score(q, k, m, n, theta):
    """The wrong way: ADD a position vector (m or n scaled) to q, k, then dot."""
    pos = [math.cos(theta), math.sin(theta)]  # a fixed position direction, scaled by index
    qm = [q[0] + m * pos[0], q[1] + m * pos[1]]
    kn = [k[0] + n * pos[0], k[1] + n * pos[1]]
    return dot(qm, kn)


# ----------------------------------------------------------------- printing

def scores_view(data):
    q, k, theta = data["q"], data["k"], data["theta"]
    print("SCORES — RoPE attention score per (m,n) pair, with the offset n-m")
    print("-" * 66)
    print("  m    n    offset   rope score")
    for m, n in data["pairs"]:
        print("  %-4d %-4d %-8d %.4f" % (m, n, n - m, rope_score(q, k, m, n, theta)))
    print("-" * 66)
    print("  pairs (0,2) and (3,5) share offset 2 -> identical score. that is the point.")


def additive_view(data):
    q, k, theta = data["q"], data["k"], data["theta"]
    print("ADDITIVE — same pairs, position ADDED instead of rotated")
    print("-" * 66)
    print("  m    n    offset   additive score")
    for m, n in data["pairs"]:
        print("  %-4d %-4d %-8d %.4f" % (m, n, n - m, additive_score(q, k, m, n, theta)))
    print("-" * 66)
    print("  (0,2) and (3,5) share offset 2 but score DIFFERENTLY -> absolute leaked in.")


def check(data):
    print("SELF-TEST — RoPE score depends only on n-m; additive does not; rotation keeps norm")
    print("-" * 66)
    q, k, theta = data["q"], data["k"], data["theta"]

    # Two pairs with the SAME offset (2): (0,2) and (3,5).
    s1 = rope_score(q, k, 0, 2, theta)
    s2 = rope_score(q, k, 3, 5, theta)
    rope_relative = abs(s1 - s2) < 1e-9
    print("  RoPE: same offset -> same score = %s (%.4f == %.4f)" % (rope_relative, s1, s2))

    # A different offset (3) must give a different score, or "relative" is trivial.
    s3 = rope_score(q, k, 1, 4, theta)
    rope_discriminates = abs(s3 - s1) > 1e-6
    print("  RoPE: different offset -> different score = %s (%.4f vs %.4f)" % (rope_discriminates, s3, s1))

    # Additive: same offset, different absolute -> DIFFERENT score (the bug).
    a1 = additive_score(q, k, 0, 2, theta)
    a2 = additive_score(q, k, 3, 5, theta)
    additive_leaks = abs(a1 - a2) > 1e-6
    print("  additive: same offset -> DIFFERENT score = %s (%.4f vs %.4f)" % (additive_leaks, a1, a2))

    # Rotation preserves length -- it only turns the vector, never scales it.
    preserves = abs(norm(rotate(q, 1.234)) - norm(q)) < 1e-9
    print("  rotation preserves the vector norm = %s (|q|=%.4f)" % (preserves, norm(q)))

    ok = rope_relative and rope_discriminates and additive_leaks and preserves
    print("-" * 66)
    print("SELF-TEST %s  rope_relative=%s  rope_discriminates=%s  additive_leaks=%s  norm_preserved=%s"
          % ("PASS" if ok else "FAIL", rope_relative, rope_discriminates, additive_leaks, preserves))
    return ok


def main():
    p = argparse.ArgumentParser(description="Rotary position embedding and relative-position invariance.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--additive", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("q=%s  k=%s  theta=%.2f rad  file=%s  (vectors are a fixture)"
          % (data["q"], data["k"], data["theta"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.additive:
        additive_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
