"""Penalize already-emitted tokens, or greedy decoding loops forever on the model's favorite token.

A decoder picks the next token from the model's logits. If one token has the highest logit and the context
barely changes, greedy decoding picks it -- then picks it again, and again, because nothing in plain greedy
decoding remembers what it already said. The result is the classic degenerate loop: "the the the the" or a
sentence that repeats verbatim without end. The model is not broken; greedy is just memoryless, so a token
that is best once is best every step, and it never gets off it.

A repetition penalty gives the decoder that memory. Before choosing, it lowers the logit of every token it
has already emitted -- divide by a penalty factor for each prior occurrence -- so a token's appeal shrinks
the more it has been used. The first time, the favorite still wins; the second time it would repeat, its
penalized logit has dropped below the runner-up, so a different token is chosen. The loop cannot form,
because repeating a token makes it progressively less attractive. Same model, same logits; the penalty only
changes which token wins once repetition sets in.

On this fixture the model's static logits most favor token X, then Y, then Z. Greedy (no penalty) emits X
eight times -- one unique token, a run of 8. With a penalty of 2.0, no token is ever emitted twice in a row
(max run 1) and the output uses more of the vocabulary. Same base logits; the penalty broke the loop. This
computes both.

  --generate   the tokens greedy vs penalized decoding emit
  --stats      the longest repeated run and the unique-token count for each
  --check      greedy loops on one token; the penalty stops immediate repetition and adds variety

The base logits, penalty, and length are the fixture; every pick is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "logits.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def generate(base, penalty, n):
    """Greedy decode n tokens, dividing an already-emitted token's logit by penalty**(times emitted)."""
    counts, out = {}, []
    for _ in range(n):
        adjusted = {t: base[t] / (penalty ** counts.get(t, 0)) for t in base}
        pick = max(adjusted, key=lambda t: adjusted[t])
        out.append(pick)
        counts[pick] = counts.get(pick, 0) + 1
    return out


def max_run(seq):
    """Longest run of the same token in a row."""
    best = run = 1
    for i in range(1, len(seq)):
        run = run + 1 if seq[i] == seq[i - 1] else 1
        best = max(best, run)
    return best if seq else 0


def unique(seq):
    return len(set(seq))


# ----------------------------------------------------------------- printing

def generate_view(data):
    base, pen, n = data["logits"], data["penalty"], data["length"]
    print("GENERATE — %d tokens, greedy vs penalty %.1f (base logits %s)" % (n, pen, base))
    print("-" * 58)
    print("  greedy:     %s" % " ".join(generate(base, 1.0, n)))
    print("  penalized:  %s" % " ".join(generate(base, pen, n)))
    print("-" * 58)
    print("  greedy sticks on the top token; the penalty moves off it.")


def stats_view(data):
    base, pen, n = data["logits"], data["penalty"], data["length"]
    g, p = generate(base, 1.0, n), generate(base, pen, n)
    print("STATS — longest repeated run and unique tokens")
    print("-" * 58)
    print("  greedy:     max run %d   unique %d" % (max_run(g), unique(g)))
    print("  penalized:  max run %d   unique %d" % (max_run(p), unique(p)))
    print("-" * 58)
    print("  the penalty caps the run and widens the vocabulary used.")


def check(data):
    print("SELF-TEST — greedy loops on one token; the penalty stops immediate repetition and adds variety")
    print("-" * 92)
    base, pen, n = data["logits"], data["penalty"], data["length"]
    g, p = generate(base, 1.0, n), generate(base, pen, n)

    greedy_loops = max_run(g) == n and unique(g) == 1
    print("  greedy emits one token for the whole output = %s (run %d, unique %d)" % (greedy_loops, max_run(g), unique(g)))

    penalized_no_immediate_repeat = max_run(p) == 1
    print("  the penalty never repeats a token immediately = %s (max run %d)" % (penalized_no_immediate_repeat, max_run(p)))

    penalized_more_variety = unique(p) > unique(g)
    print("  the penalty uses more of the vocabulary = %s (%d vs %d)" % (penalized_more_variety, unique(p), unique(g)))

    top = max(base, key=lambda t: base[t])
    penalty_lowers_emitted = base[top] / (pen ** 1) < base[top]
    print("  emitting a token lowers its next logit = %s (%s: %.2f -> %.2f)" % (penalty_lowers_emitted, top, base[top], base[top] / pen))

    same_base = generate(base, 1.0, 1) == generate(base, pen, 1)
    print("  both start from the identical base logits (first pick same) = %s" % same_base)

    ok = greedy_loops and penalized_no_immediate_repeat and penalized_more_variety and penalty_lowers_emitted and same_base
    print("-" * 92)
    print("SELF-TEST %s  greedy_loops=%s  penalized_no_immediate_repeat=%s  penalized_more_variety=%s  penalty_lowers_emitted=%s  same_base=%s"
          % ("PASS" if ok else "FAIL", greedy_loops, penalized_no_immediate_repeat, penalized_more_variety, penalty_lowers_emitted, same_base))
    return ok


def main():
    p = argparse.ArgumentParser(description="Penalize already-emitted tokens so greedy decoding does not loop.")
    p.add_argument("--generate", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("vocab=%d  penalty=%.1f  length=%d  file=%s  (the logits are a fixture)"
          % (len(data["logits"]), data["penalty"], data["length"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.generate:
        generate_view(data)
    elif args.stats:
        stats_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
