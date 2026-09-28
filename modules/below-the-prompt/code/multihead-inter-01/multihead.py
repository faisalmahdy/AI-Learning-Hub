"""Split attention into several heads -- one head is a single weighted average and cannot retrieve two things at once.

An attention head does one specific thing: it scores every token against the query, softmaxes the scores into a
probability distribution, and returns the WEIGHTED AVERAGE of the tokens' value vectors under that distribution. The output
of one head is therefore a convex combination of the value vectors -- a single point inside their convex hull -- and that
is a real limitation. If the query needs to gather information from two DIFFERENT tokens for two DIFFERENT reasons (the
subject of a sentence AND its object, a noun's article AND the verb it governs), one head cannot do it cleanly, because one
softmax can only be in one place. It can spread its weight across both targets, but then it returns the average of the two,
a blend that is neither one -- the two distinct pieces of information have been collapsed into their midpoint and can no
longer be separated. A single head has one question it can ask of the sequence, and it must answer with one blended value.

MULTI-HEAD ATTENTION removes the limitation by running several attention heads in PARALLEL, each with its own scores and
its own softmax, and concatenating their outputs. Now head A can attend fully to the subject and head B fully to the
object, and because their outputs occupy different slots of the concatenated vector, both are retrieved at full strength and
kept distinct. Each head learns to attend to a different kind of relationship (a different subspace of the values), so the
model can gather several distinct pieces of information about a token in a single attention layer instead of being forced to
average them. The heads are cheap -- the model dimension is split among them, so each head works in a lower-dimensional
subspace and the total compute is about the same as one full-width head -- so the win is qualitative (several independent
retrievals) at roughly no extra cost.

The point is not that a head is weak; it is that a head is SINGULAR -- one distribution, one weighted average -- and much of
what attention must do requires several independent lookups at once. Splitting into heads is how a transformer buys those
parallel lookups.

The rule: use multiple attention heads, because one head is a single softmax that returns one weighted average of the value
vectors -- a convex blend that collapses two distinct retrievals into their midpoint -- while several heads run independent
distributions in parallel and concatenate, so the model can attend to different tokens for different reasons and keep the
results separate.

On this fixture the query needs signal A (token 0's [1,0]) AND signal B (token 2's [0,1]). A single head, forced to cover
both, splits its weight and returns [0.5, 0.5] -- each signal recovered at only 0.5, blended and inseparable. Two heads
attend one to each: their outputs [1,0] and [0,1] recover A and B at full strength 1.0. This computes both.

  --attend    the single head's blended output vs the two heads' separate outputs (head A, head B), concatenated
  --recover   how strongly signal A and signal B are recovered by each scheme -- 0.5 each (single) vs 1.0 each (two heads)
  --check     one head blends the two signals to their midpoint; two heads retrieve both at full strength and keep them distinct

values and the per-head weights are the fixture; every weighted output and recovery is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "multihead.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def weighted_average(weights, values):
    """One attention head's output: the weighted average of the value vectors under the softmax distribution `weights`."""
    dim = len(values[0])
    return [sum(w * v[k] for w, v in zip(weights, values)) for k in range(dim)]


def recovery(output, signal):
    """How strongly `output` carries `signal`: the projection of output onto the unit signal direction."""
    norm2 = sum(s * s for s in signal)
    return sum(o * s for o, s in zip(output, signal)) / norm2


# ----------------------------------------------------------------- printing

def attend_view(data):
    vals = data["values"]
    single = weighted_average(data["single_head_weights"], vals)
    head_a = weighted_average(data["head_a_weights"], vals)
    head_b = weighted_average(data["head_b_weights"], vals)
    print("ATTEND — one head's blended output vs two heads' separate outputs")
    print("-" * 60)
    print("  values: %s  (token 0 = signal A, token 2 = signal B)" % vals)
    print("  SINGLE head weights %s -> output %s" % (data["single_head_weights"], single))
    print("  TWO heads:")
    print("    head A weights %s -> output %s" % (data["head_a_weights"], head_a))
    print("    head B weights %s -> output %s" % (data["head_b_weights"], head_b))
    print("    concatenated -> %s" % (head_a + head_b))
    print("-" * 60)
    print("  single head returns the midpoint of A and B; two heads keep them separate.")


def recover_view(data):
    vals, sa, sb = data["values"], data["signal_a"], data["signal_b"]
    single = weighted_average(data["single_head_weights"], vals)
    head_a = weighted_average(data["head_a_weights"], vals)
    head_b = weighted_average(data["head_b_weights"], vals)
    print("RECOVER — how strongly each signal is retrieved (1.0 = full, 0 = absent)")
    print("-" * 58)
    print("  single head output %s:" % single)
    print("    signal A recovered = %.1f    signal B recovered = %.1f" % (recovery(single, sa), recovery(single, sb)))
    print("  two heads (A output %s, B output %s):" % (head_a, head_b))
    print("    signal A recovered = %.1f    signal B recovered = %.1f" % (recovery(head_a, sa), recovery(head_b, sb)))
    print("-" * 58)
    print("  one head recovers each signal at half strength; two heads recover each at full strength.")


def check(data):
    print("SELF-TEST — one head blends the two signals to their midpoint; two heads retrieve both at full strength")
    print("-" * 104)
    vals, sa, sb = data["values"], data["signal_a"], data["signal_b"]
    single = weighted_average(data["single_head_weights"], vals)
    head_a = weighted_average(data["head_a_weights"], vals)
    head_b = weighted_average(data["head_b_weights"], vals)

    single_blends = single == [0.5, 0.5]
    print("  single head output is the blend (midpoint) of A and B = %s (%s)" % (single_blends, single))

    single_half_each = recovery(single, sa) == 0.5 and recovery(single, sb) == 0.5
    print("  single head recovers each signal at only 0.5 = %s (A %.1f, B %.1f)"
          % (single_half_each, recovery(single, sa), recovery(single, sb)))

    twohead_recovers_a = recovery(head_a, sa) == 1.0
    print("  head A recovers signal A at full strength = %s (%.1f)" % (twohead_recovers_a, recovery(head_a, sa)))

    twohead_recovers_b = recovery(head_b, sb) == 1.0
    print("  head B recovers signal B at full strength = %s (%.1f)" % (twohead_recovers_b, recovery(head_b, sb)))

    twohead_beats_single = min(recovery(head_a, sa), recovery(head_b, sb)) > min(recovery(single, sa), recovery(single, sb))
    print("  two heads' weakest recovery beats the single head's = %s (%.1f > %.1f)"
          % (twohead_beats_single, min(recovery(head_a, sa), recovery(head_b, sb)), min(recovery(single, sa), recovery(single, sb))))

    ok = single_blends and single_half_each and twohead_recovers_a and twohead_recovers_b and twohead_beats_single
    print("-" * 104)
    print("SELF-TEST %s  single_blends=%s  single_half_each=%s  twohead_recovers_a=%s  twohead_recovers_b=%s  twohead_beats_single=%s"
          % ("PASS" if ok else "FAIL", single_blends, single_half_each, twohead_recovers_a, twohead_recovers_b, twohead_beats_single))
    return ok


def main():
    p = argparse.ArgumentParser(description="Multi-head attention: use multiple attention heads, because one head is a single softmax that returns one weighted average of the value vectors -- a convex blend that collapses two distinct retrievals into their midpoint -- while several heads run independent distributions in parallel and concatenate, so the model can attend to different tokens for different reasons and keep the results separate.")
    p.add_argument("--attend", action="store_true")
    p.add_argument("--recover", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("values=%s  single_head_weights=%s  file=%s  (the values and per-head weights are a fixture)"
          % (data["values"], data["single_head_weights"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.attend:
        attend_view(data)
    elif args.recover:
        recover_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
