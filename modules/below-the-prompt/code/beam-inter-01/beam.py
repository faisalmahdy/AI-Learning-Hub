#!/usr/bin/env python3
"""Greedy decoding is myopic -- the highest-probability token can lead to the worst sequence.

Decoding a sequence from a language model means choosing tokens one at a time. Greedy decoding
takes the single highest-probability token at each step. It is fast and it is locally optimal --
and locally optimal is exactly the trap, because the best first token can open onto poor
continuations while a slightly-worse first token opens onto excellent ones. Greedy commits to
the local winner and never looks back, so it can return a sequence whose total probability is
far below one it walked right past.

Beam search keeps the trap from closing. Instead of one running sequence it keeps the top-k
partial sequences (the beam width), expands all of them each step, and keeps the best k of the
results -- so a first token that looked worse survives long enough to reveal its strong
continuations. On this tree greedy takes the 0.55 first token and is then stuck with a best
total of 0.275, while beam width 2 keeps the 0.45 token alive and finds the 0.4275 sequence
that is actually most probable. Same model, same probabilities; the difference is whether the
decoder can hold more than one hypothesis at once. This builds greedy and beam, enumerates every
full sequence's true probability, and shows greedy returning a sequence that is not the best.

  --tree     the probability tree, every full sequence, and its total probability
  --decode   the greedy sequence vs the beam sequence, with totals
  --check    beam finds a higher-probability sequence than greedy; width 1 reproduces greedy

The probability tree and beam width are the fixture; greedy, beam, and every total are computed.
Deterministic; stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tree.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- enumerate the tree

def all_sequences(tree):
    """Every root-to-leaf path with its total probability (product of step probabilities)."""
    out = []

    def walk(node, prefix, prob):
        nxt = node.get("next")
        if not nxt:
            out.append((prefix, prob))
            return
        for tok, child in nxt.items():
            walk(child, prefix + [tok], prob * child["p"])

    for tok, child in tree.items():
        walk(child, [tok], child["p"])
    return out


def best_sequence(tree):
    """The globally most-probable full sequence -- what a perfect decoder would return."""
    return max(all_sequences(tree), key=lambda s: s[1])


# ------------------------------------------------------------- greedy decoding

def greedy(tree):
    """Take the single highest-probability token at each step; never reconsider."""
    seq, prob, level = [], 1.0, tree
    while level:
        tok = min(level, key=lambda t: (-level[t]["p"], t))   # max prob, ties by smallest token
        seq.append(tok)
        prob *= level[tok]["p"]
        level = level[tok].get("next")
    return seq, prob


# ------------------------------------------------------------- beam search

def beam_search(tree, width):
    """Keep the top-`width` partial sequences at every step; expand and prune each round."""
    beams = [([tok], child["p"], child) for tok, child in tree.items()]
    beams = top(beams, width)
    while any(b[2].get("next") for b in beams):
        expanded = []
        for seq, prob, node in beams:
            nxt = node.get("next")
            if not nxt:
                expanded.append((seq, prob, node))          # a finished sequence rides along
            else:
                for tok, child in nxt.items():
                    expanded.append((seq + [tok], prob * child["p"], child))
        beams = top(expanded, width)
    return max(beams, key=lambda b: b[1])[:2]


def top(beams, width):
    return sorted(beams, key=lambda b: (-b[1], b[0]))[:width]


# ----------------------------------------------------------------- printing

def tree_view(data):
    seqs = sorted(all_sequences(data["tree"]), key=lambda s: -s[1])
    print("TREE — every full sequence and its total probability")
    print("-" * 56)
    for seq, prob in seqs:
        print("  %-12s %.4f" % ("-".join(seq), prob))
    print("-" * 56)
    b = best_sequence(data["tree"])
    print("  most probable sequence: %s (%.4f)" % ("-".join(b[0]), b[1]))


def decode_view(data):
    g_seq, g_prob = greedy(data["tree"])
    b_seq, b_prob = beam_search(data["tree"], data["beam_width"])
    print("DECODE — greedy vs beam (width %d)" % data["beam_width"])
    print("-" * 56)
    print("  greedy: %-12s total %.4f" % ("-".join(g_seq), g_prob))
    print("  beam:   %-12s total %.4f" % ("-".join(b_seq), b_prob))
    print("-" * 56)
    print("  greedy took the best first token and missed the best sequence.")


def check(data):
    print("SELF-TEST — beam finds a higher-probability sequence than greedy; width 1 == greedy")
    print("-" * 56)
    tree = data["tree"]

    g_seq, g_prob = greedy(tree)
    b_seq, b_prob = beam_search(tree, data["beam_width"])
    best_seq, best_prob = best_sequence(tree)

    # greedy takes the locally-best first token
    first_greedy = g_seq[0]
    local_best = max(tree, key=lambda t: (tree[t]["p"], t))
    greedy_local = first_greedy == local_best
    print("  greedy's first token is the local argmax = %s (%s, p=%.2f)"
          % (greedy_local, first_greedy, tree[first_greedy]["p"]))

    beam_better = b_prob > g_prob
    print("  beam's sequence is more probable than greedy's = %s (%.4f vs %.4f)"
          % (beam_better, b_prob, g_prob))

    greedy_suboptimal = g_seq != best_seq
    print("  greedy did NOT find the globally best sequence = %s (greedy %s, best %s)"
          % (greedy_suboptimal, "-".join(g_seq), "-".join(best_seq)))

    beam_optimal_here = b_seq == best_seq
    print("  beam found the globally best sequence here = %s" % beam_optimal_here)

    w1_seq, w1_prob = beam_search(tree, 1)
    width1_is_greedy = abs(w1_prob - g_prob) < 1e-12 and w1_seq == g_seq
    print("  beam width 1 reproduces greedy = %s" % width1_is_greedy)

    ok = greedy_local and beam_better and greedy_suboptimal and beam_optimal_here and width1_is_greedy
    print("-" * 56)
    print("SELF-TEST %s  greedy_local=%s  beam_better=%s  greedy_suboptimal=%s  beam_optimal=%s  w1=greedy=%s"
          % ("PASS" if ok else "FAIL", greedy_local, beam_better, greedy_suboptimal, beam_optimal_here, width1_is_greedy))
    return ok


def main():
    p = argparse.ArgumentParser(description="Greedy vs beam decoding on a probability tree.")
    p.add_argument("--tree", action="store_true")
    p.add_argument("--decode", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("beam_width=%d  file=%s  (the probability tree is a fixture)" % (data["beam_width"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.tree:
        tree_view(data)
    elif args.decode:
        decode_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
