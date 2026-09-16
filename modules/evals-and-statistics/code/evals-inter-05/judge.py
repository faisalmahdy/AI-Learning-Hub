#!/usr/bin/env python3
"""LLM-as-judge position bias: judge both orders, or you score presentation, not merit.

Pairwise LLM judging asks a model which of two answers is better. Real judges have a
position bias -- they systematically favor whichever answer is shown first (or last). So
a verdict from a single fixed order confounds two things: which answer is better, and
which one got the favored slot. Judge in one order and you cannot tell them apart, and on
any pair where the quality gap is smaller than the position bias, the slot wins -- the
judge crowns the first answer regardless of merit, and reports it with full confidence.

The fix is to judge BOTH orders (A-then-B and B-then-A) and only trust a verdict when it
survives the swap. A pair whose winner flips when you swap the order is one the judge
cannot actually call -- either a genuine tie or a gap the bias overwhelms -- and the honest
move is to abstain, not to report the single-order winner. This models a biased judge and
measures single-order verdicts against two-order ones.

  --single      the single-order (A first) verdict for each pair, and whether it matches truth
  --swap        each pair judged both orders; which flip (bias-decided) and which hold
  --check       single-order crowns the first slot on close pairs; two-order abstains and is honest

Stdlib only. Deterministic (the judge is a scoring rule, not a real model call).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pairs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the biased judge

def judge_once(first_q, second_q, bias):
    """The judge favors the FIRST-presented answer by `bias`. Returns 'first' or 'second'."""
    return "first" if first_q + bias >= second_q else "second"


def verdict_order(pair, bias, a_first):
    """Judge the pair in one order; return the winner as 'A' or 'B'."""
    if a_first:
        w = judge_once(pair["a_quality"], pair["b_quality"], bias)
        return "A" if w == "first" else "B"
    else:
        w = judge_once(pair["b_quality"], pair["a_quality"], bias)
        return "B" if w == "first" else "A"


# ------------------------------------------------------------- single vs two-order

def single_order(pair, bias):
    """Judge once, A presented first (the naive protocol)."""
    return verdict_order(pair, bias, a_first=True)


def two_order(pair, bias):
    """Judge both orders; a winner only counts if it survives the swap, else abstain."""
    ab = verdict_order(pair, bias, a_first=True)
    ba = verdict_order(pair, bias, a_first=False)
    return ab if ab == ba else "abstain"


# ----------------------------------------------------------------- printing

def single_view(data):
    bias = data["position_bias"]
    print("SINGLE — one order (A first); verdict vs truth (position bias = %.1f)" % bias)
    print("-" * 66)
    for p in data["pairs"]:
        v = single_order(p, bias)
        note = "ok" if v == p["truly_better"] else "<-- WRONG (truth %s)" % p["truly_better"]
        print("  %-3s A_q=%.0f B_q=%.0f  verdict=%s  %s" % (p["id"], p["a_quality"], p["b_quality"], v, note))
    print("-" * 66)
    print("  the single-order judge always names a winner -- even when position, not merit, decided.")


def swap_view(data):
    bias = data["position_bias"]
    print("SWAP — judge both orders; a flip means the bias, not quality, decided")
    print("-" * 66)
    for p in data["pairs"]:
        ab = verdict_order(p, bias, a_first=True)
        ba = verdict_order(p, bias, a_first=False)
        outcome = two_order(p, bias)
        flip = "FLIPS -> abstain" if ab != ba else "holds"
        print("  %-3s A-first=%s  B-first=%s  %-16s two-order=%s" % (p["id"], ab, ba, flip, outcome))
    print("-" * 66)
    print("  pairs that flip are ones the judge cannot call; two-order abstains on them.")


def check(data):
    print("SELF-TEST — single-order crowns the first slot on close pairs; two-order is honest")
    print("-" * 66)
    bias = data["position_bias"]
    pairs = {p["id"]: p for p in data["pairs"]}

    # On the true tie (p2), single-order still declares a winner -- and it is A (the first slot).
    tie = pairs["p2"]
    single_tie = single_order(tie, bias)
    crowns_first = single_tie == "A"
    print("  single-order declares a winner on a TRUE TIE = %s (p2 -> %s)" % (crowns_first, single_tie))

    # Two-order abstains on that tie.
    two_tie = two_order(tie, bias)
    abstains_on_tie = two_tie == "abstain"
    print("  two-order ABSTAINS on the tie = %s (p2 -> %s)" % (abstains_on_tie, two_tie))

    # p3: B is truly better by 1, but bias (2) flips single-order to A -- a real error.
    close = pairs["p3"]
    single_close = single_order(close, bias)
    single_wrong = single_close != close["truly_better"]
    print("  single-order gets a close pair WRONG (position beats a small quality gap) = %s (p3 -> %s, truth %s)"
          % (single_wrong, single_close, close["truly_better"]))
    two_close = two_order(close, bias)
    two_abstains_close = two_close == "abstain"
    print("  two-order abstains on that close pair instead of erring = %s (p3 -> %s)" % (two_abstains_close, two_close))

    # On clear pairs (p1, p4) two-order agrees with truth.
    clear_ok = two_order(pairs["p1"], bias) == "A" and two_order(pairs["p4"], bias) == "B"
    print("  two-order matches truth on the CLEAR pairs = %s (p1->A, p4->B)" % clear_ok)

    ok = crowns_first and abstains_on_tie and single_wrong and two_abstains_close and clear_ok
    print("-" * 66)
    print("SELF-TEST %s  crowns_first=%s  abstains_on_tie=%s  single_wrong=%s  two_abstains=%s  clear_ok=%s"
          % ("PASS" if ok else "FAIL", crowns_first, abstains_on_tie, single_wrong, two_abstains_close, clear_ok))
    return ok


def main():
    p = argparse.ArgumentParser(description="LLM-as-judge position bias and the swap fix.")
    p.add_argument("--single", action="store_true")
    p.add_argument("--swap", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pairs=%d  position_bias=%.1f  file=%s  (qualities are a fixture)"
          % (len(data["pairs"]), data["position_bias"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.single:
        single_view(data)
    elif args.swap:
        swap_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
