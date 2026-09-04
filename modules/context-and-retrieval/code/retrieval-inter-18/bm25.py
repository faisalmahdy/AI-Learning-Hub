"""Saturate the term frequency, or a keyword-stuffed document buries the relevant one.

A lexical scorer weights a document by how often the query term appears in it -- its term frequency. The
naive rule is to use that count directly: twice the occurrences, twice the score. That rule is unbounded, and
it rewards repetition without limit. A page that repeats "mortgage" fifty times scores fifty times a page that
uses it once, even if the second page is the one that actually answers the question. Keyword stuffing is not a
hypothetical; it is the oldest trick in search spam, and linear term frequency is exactly the weakness it
exploits.

BM25 saturates the term frequency instead: score = tf * (k1 + 1) / (tf + k1). The first occurrence is worth
the most; each additional one adds less; and the score approaches a ceiling of k1 + 1 no matter how high tf
climbs. Going from one occurrence to three is a real jump, but going from ten to fifty barely moves the score,
because past a point the term's presence is established and more repetition tells you nothing. The parameter
k1 sets how fast the curve flattens. The effect is that stuffing stops working: the stuffed document's huge tf
advantage collapses to almost nothing, and other signals -- other query terms, document length, relevance --
get to decide.

On this fixture k1 is 1.2, so the ceiling is 2.2. Linear scoring gives tf 3 and tf 50 the scores 3 and 50 --
a 16.7x gap that lets the stuffed doc dominate. BM25 gives them 1.57 and 2.15 -- a 1.37x gap, stuffing
neutralized. This computes both.

  --scores    linear vs BM25 score for a range of term frequencies, and the marginal gain of each step
  --stuffing  a relevant doc (tf 3) vs a stuffed doc (tf 50): the linear gap vs the BM25 gap
  --check     linear tf is unbounded; BM25 saturates toward a ceiling and diminishes each extra occurrence

The k1 and term frequencies are the fixture; every score is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "bm25.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def linear(tf):
    """The naive scorer: term frequency used directly, unbounded."""
    return float(tf)


def bm25(tf, k1):
    """BM25's saturating term frequency: approaches the ceiling k1+1 as tf grows."""
    return tf * (k1 + 1) / (tf + k1)


def ceiling(k1):
    return k1 + 1.0


# ----------------------------------------------------------------- printing

def scores_view(data):
    k1 = data["k1"]
    print("SCORES — linear vs BM25 term-frequency weight (k1 %.1f, ceiling %.1f)" % (k1, ceiling(k1)))
    print("-" * 64)
    print("  tf     linear    BM25    marginal BM25 gain")
    prev = None
    for tf in data["tf_values"]:
        b = bm25(tf, k1)
        marg = "" if prev is None else "+%.3f" % (b - prev)
        print("  %-5d  %6.1f   %5.3f   %s" % (tf, linear(tf), b, marg))
        prev = b
    print("-" * 64)
    print("  linear keeps climbing; BM25 flattens toward %.1f as tf grows." % ceiling(k1))


def stuffing_view(data):
    k1, rel, stf = data["k1"], data["relevant_tf"], data["stuffed_tf"]
    print("STUFFING — a relevant doc (tf %d) vs a keyword-stuffed doc (tf %d)" % (rel, stf))
    print("-" * 64)
    print("  linear:  relevant %.1f   stuffed %.1f   stuffed/relevant %.1fx" % (linear(rel), linear(stf), linear(stf) / linear(rel)))
    print("  BM25:    relevant %.3f  stuffed %.3f  stuffed/relevant %.2fx" % (bm25(rel, k1), bm25(stf, k1), bm25(stf, k1) / bm25(rel, k1)))
    print("-" * 64)
    print("  linear lets the stuffed doc dominate; BM25 shrinks its edge to almost nothing.")


def check(data):
    print("SELF-TEST — linear tf is unbounded; BM25 saturates toward a ceiling and diminishes each extra occurrence")
    print("-" * 104)
    k1 = data["k1"]
    cap = ceiling(k1)

    linear_unbounded = linear(50) == 50.0 and linear(50) > linear(10) * 4
    print("  linear scoring grows without limit = %s (tf 50 -> %.1f)" % (linear_unbounded, linear(50)))

    bm25_below_ceiling = all(bm25(tf, k1) < cap for tf in [1, 3, 10, 50])
    print("  every BM25 score stays under the ceiling %.1f = %s (tf 50 -> %.3f)" % (cap, bm25_below_ceiling, bm25(50, k1)))

    marginal_diminishes = (bm25(3, k1) - bm25(1, k1)) > (bm25(50, k1) - bm25(10, k1))
    print("  each extra occurrence adds less = %s (1->3 gains %.3f, 10->50 gains %.3f)"
          % (marginal_diminishes, bm25(3, k1) - bm25(1, k1), bm25(50, k1) - bm25(10, k1)))

    first_occurrence_worth_most = (bm25(1, k1) - bm25(0, k1)) > (bm25(2, k1) - bm25(1, k1))
    print("  the first occurrence is the biggest jump = %s (0->1 gains %.3f)" % (first_occurrence_worth_most, bm25(1, k1) - bm25(0, k1)))

    stuffing_neutralized = (linear(50) / linear(3)) > 10 and (bm25(50, k1) / bm25(3, k1)) < 2
    print("  BM25 shrinks the stuffing advantage = %s (linear %.1fx -> BM25 %.2fx)"
          % (stuffing_neutralized, linear(50) / linear(3), bm25(50, k1) / bm25(3, k1)))

    ok = linear_unbounded and bm25_below_ceiling and marginal_diminishes and first_occurrence_worth_most and stuffing_neutralized
    print("-" * 104)
    print("SELF-TEST %s  linear_unbounded=%s  bm25_below_ceiling=%s  marginal_diminishes=%s  first_occurrence_worth_most=%s  stuffing_neutralized=%s"
          % ("PASS" if ok else "FAIL", linear_unbounded, bm25_below_ceiling, marginal_diminishes, first_occurrence_worth_most, stuffing_neutralized))
    return ok


def main():
    p = argparse.ArgumentParser(description="Saturate term frequency (BM25) so keyword stuffing cannot dominate a lexical score.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--stuffing", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("k1=%.1f  ceiling=%.1f  file=%s  (the k1 and term frequencies are a fixture)"
          % (data["k1"], ceiling(data["k1"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.stuffing:
        stuffing_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
