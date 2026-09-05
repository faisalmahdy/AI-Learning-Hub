#!/usr/bin/env python3
"""Temperature and top-p shape the softmax -- and truncation must renormalize.

A model emits logits; sampling turns them into a next token in two tunable steps.
Temperature divides the logits before the softmax: below 1 it sharpens the
distribution toward the top token (T -> 0 is greedy argmax), above 1 it flattens it
toward uniform (more surprising, more mistakes). Top-p (nucleus) sampling then keeps
only the smallest set of tokens whose probability sums to at least p and samples from
those, cutting the unreliable tail while letting the head stay as wide as it needs.

The trap is in the word 'keep'. Truncating to the nucleus removes probability mass,
so the surviving tokens no longer sum to 1 -- you MUST renormalize, divide by the
surviving mass, or you are sampling from an invalid distribution that under-counts
every kept token. Skip that one division and the bug is silent: the top token is
under-weighted, and rejection- or cumulative-based samplers drift. This measures the
temperature knob, the nucleus cut, and the renormalization the cut requires.

  --temperature   the distribution and its entropy at T = 0.5, 1.0, 2.0
  --nucleus       top-p truncation at p=0.9: which tokens survive, and the renormalized mass
  --check         softmax sums to 1; T sharpens/flattens; the nucleus renormalizes to 1

Stdlib only. Deterministic (this scores distributions; it does not draw samples).
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "logits.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the distribution

def softmax(logits, temperature=1.0):
    """exp(logit / T) normalized. Lower T sharpens toward the top; higher T flattens."""
    scaled = [l / temperature for l in logits]
    m = max(scaled)  # subtract max for numerical stability
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def entropy(probs):
    """Shannon entropy in bits -- low when peaked, high when flat."""
    return -sum(p * math.log2(p) for p in probs if p > 0)


# ------------------------------------------------------------- nucleus (top-p)

def nucleus(probs, p, renormalize=True):
    """Keep the smallest set of tokens whose mass reaches p; renormalize to a valid dist.

    Returns a list of (index, prob) for the surviving tokens. With renormalize=False
    the kept probs are left as-is -- the BUG: they no longer sum to 1.
    """
    ranked = sorted(range(len(probs)), key=lambda i: (-probs[i], i))
    kept, cum = [], 0.0
    for i in ranked:
        kept.append(i)
        cum += probs[i]
        if cum >= p:
            break  # smallest prefix that reaches p, INCLUDING the token that crosses it
    mass = sum(probs[i] for i in kept)
    if renormalize:
        return [(i, probs[i] / mass) for i in kept]
    return [(i, probs[i]) for i in kept]


# ----------------------------------------------------------------- printing

def temperature_view(data):
    tokens, logits = data["tokens"], data["logits"]
    print("TEMPERATURE — the same logits, three temperatures")
    print("-" * 66)
    for T in (0.5, 1.0, 2.0):
        probs = softmax(logits, T)
        top = tokens[max(range(len(probs)), key=lambda i: probs[i])]
        bars = "  ".join("%s=%.2f" % (tokens[i], probs[i]) for i in range(len(tokens)))
        print("  T=%.1f  entropy=%.2f bits  top=%-5s" % (T, entropy(probs), top))
        print("        %s" % bars)
    print("-" * 66)
    print("  low T concentrates mass on 'the'; high T spreads it toward uniform.")


def nucleus_view(data):
    tokens, logits = data["tokens"], data["logits"]
    p = 0.9
    probs = softmax(logits, 1.0)
    kept = nucleus(probs, p)
    print("NUCLEUS — top-p at p=%.2f (T=1.0): keep the head, renormalize" % p)
    print("-" * 66)
    print("  full distribution: %s" % "  ".join("%s=%.2f" % (tokens[i], probs[i]) for i in range(len(tokens))))
    print("  kept (%d of %d tokens), renormalized to sum 1:" % (len(kept), len(tokens)))
    for i, pr in kept:
        print("     %-6s %.3f" % (tokens[i], pr))
    print("  dropped tail: %s" % [tokens[i] for i in range(len(tokens)) if i not in [k for k, _ in kept]])
    print("-" * 66)
    print("  the low-probability tail (quantum, zebra) is cut before sampling.")


def check(data):
    print("SELF-TEST — softmax normalizes; T sharpens and flattens; the nucleus renormalizes")
    print("-" * 66)
    logits = data["logits"]

    probs = softmax(logits, 1.0)
    sums_to_one = abs(sum(probs) - 1.0) < 1e-9
    print("  softmax sums to 1 = %s (%.6f)" % (sums_to_one, sum(probs)))

    e_cold, e_hot = entropy(softmax(logits, 0.5)), entropy(softmax(logits, 2.0))
    temp_orders = e_cold < entropy(probs) < e_hot
    print("  entropy rises with temperature = %s (%.2f < %.2f < %.2f bits)"
          % (temp_orders, e_cold, entropy(probs), e_hot))

    top_i = max(range(len(probs)), key=lambda i: probs[i])
    colder_sharper = softmax(logits, 0.5)[top_i] > probs[top_i]
    print("  lower T concentrates mass on the top token = %s (%.2f > %.2f)"
          % (colder_sharper, softmax(logits, 0.5)[top_i], probs[top_i]))

    kept = nucleus(probs, 0.9, renormalize=True)
    renorm_valid = abs(sum(pr for _, pr in kept) - 1.0) < 1e-9
    print("  renormalized nucleus sums to 1 = %s (%.6f)" % (renorm_valid, sum(pr for _, pr in kept)))

    buggy = nucleus(probs, 0.9, renormalize=False)
    bug_undercounts = sum(pr for _, pr in buggy) < 1.0 - 1e-9
    print("  BUG: un-renormalized nucleus sums to < 1 = %s (%.4f)"
          % (bug_undercounts, sum(pr for _, pr in buggy)))

    ok = sums_to_one and temp_orders and colder_sharper and renorm_valid and bug_undercounts
    print("-" * 66)
    print("SELF-TEST %s  softmax_ok=%s  temp_orders=%s  colder_sharper=%s  renorm_valid=%s  bug_seen=%s"
          % ("PASS" if ok else "FAIL", sums_to_one, temp_orders, colder_sharper, renorm_valid, bug_undercounts))
    return ok


def main():
    p = argparse.ArgumentParser(description="Temperature, top-p nucleus sampling, and renormalization.")
    p.add_argument("--temperature", action="store_true")
    p.add_argument("--nucleus", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("vocab=%d  file=%s  (logits are a fixture)" % (len(data["tokens"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.temperature:
        temperature_view(data)
    elif args.nucleus:
        nucleus_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
