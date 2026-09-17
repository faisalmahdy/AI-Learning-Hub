"""Report an eval score as a mean over seeds, not one run -- a single noisy run can flip the winner between two models.

A model's score on a benchmark is not a fixed number. Any evaluation that samples the model's outputs (temperature above
zero, nucleus sampling, tool calls with nondeterministic ordering) produces a DIFFERENT score every time you run it with a
different random seed, because different generations are sampled and graded. The variation is not a bug to be eliminated;
it is the real uncertainty of the measurement. Yet the near-universal habit is to run the benchmark ONCE, report that
single number as 'the model's score,' and compare two models by their single numbers. That comparison is unreliable
exactly to the degree that the per-run spread is large, and for many benchmarks it is large enough to change the answer.

The trap is that a single run puts a model somewhere within its own distribution -- possibly a lucky high draw, possibly
an unlucky low one -- and comparing two single draws compares two points that each carry that noise. If model A truly
averages a few points above model B, but each has a run-to-run spread of several points, then a single run of A can land
low while a single run of B lands high, and the one-shot comparison will report that B beat A -- the opposite of the truth.
You have not measured which model is better; you have measured which model got the luckier seed. Rerun with new seeds and
the 'winner' can change, which is the tell that the comparison was never about the models.

The fix is to run each model over several seeds and report the MEAN with its spread (standard deviation, or a standard
error / confidence interval), and to judge a difference against that spread. The mean over seeds is a far more stable
estimate of the model's true score than any single run, and the standard error of the mean shrinks as you add seeds, so a
real gap becomes distinguishable from noise. A difference between two models is only credible when it is large relative to
the combined run-to-run spread -- the same 'test the difference against its uncertainty' discipline that applies to every
noisy measurement, here with the noise coming from the sampling seed rather than the choice of test cases.

The rule: report a sampled model's benchmark score as a mean over multiple seeds together with its spread, and compare
models by those means against the combined standard error -- never by a single run, because run-to-run variance can make
one lucky or unlucky seed flip the apparent winner even when the true, seed-averaged gap is solid.

On this fixture A averages 72 across five seeds and B averages 66, a 6-point gap that is about 3 standard errors -- solid.
But A's runs dip to 68 and B's rise to 70, so a single-run comparison can show B ahead of A by 2, the opposite verdict.
This computes both.

  --seeds    each model's five per-seed scores, the mean, and the run-to-run standard deviation
  --single   the range of gaps a single-run comparison can produce (B+2 up to A+14) versus the stable seed-mean gap of 6
  --check    a single run can flip the winner, while the seed-averaged gap of 6 points is about 3 standard errors and solid

The per-seed scores are the fixture; every mean, standard deviation, standard error, gap range, and t-statistic is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "seedvar.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def sample_variance(xs):
    """Unbiased (n-1) variance of the per-seed scores."""
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def sample_std(xs):
    return math.sqrt(sample_variance(xs))


def se_of_difference(a, b):
    """Standard error of the difference in means of two independent samples."""
    return math.sqrt(sample_variance(a) / len(a) + sample_variance(b) / len(b))


def single_run_gap_range(a, b):
    """The most extreme A-minus-B a single-run comparison could report: (worst for A, best for A)."""
    return min(a) - max(b), max(a) - min(b)


# ----------------------------------------------------------------- printing

def seeds_view(data):
    a, b = data["model_a"], data["model_b"]
    print("SEEDS — five runs of each model, different seed each time")
    print("-" * 60)
    print("  model  per-seed scores        mean    run-to-run std")
    for m in (a, b):
        print("  %-5s  %-22s %-7.1f %.2f"
              % (m["name"], m["seed_scores"], mean(m["seed_scores"]), sample_std(m["seed_scores"])))
    print("-" * 60)
    print("  the spread within each model is real -- each run samples different generations.")


def single_view(data):
    a, b = data["model_a"]["seed_scores"], data["model_b"]["seed_scores"]
    worst, best = single_run_gap_range(a, b)
    print("SINGLE — what a one-run-each comparison can report vs the seed-mean gap")
    print("-" * 68)
    print("  seed-mean gap (A - B)          = %+.1f  (A really is better on average)" % (mean(a) - mean(b)))
    print("  single-run gap, worst for A    = %+.1f  (A's low %d vs B's high %d -> B 'wins')" % (worst, min(a), max(b)))
    print("  single-run gap, best for A     = %+.1f  (A's high %d vs B's low %d)" % (best, max(a), min(b)))
    print("-" * 68)
    print("  one run each can report anything from %+.1f to %+.1f -- the sign itself is not safe." % (worst, best))


def check(data):
    print("SELF-TEST — a single run can flip the winner, while the seed-averaged gap is solid")
    print("-" * 100)
    a = data["model_a"]["seed_scores"]
    b = data["model_b"]["seed_scores"]
    mean_a, mean_b = mean(a), mean(b)
    gap = mean_a - mean_b
    se = se_of_difference(a, b)
    worst, best = single_run_gap_range(a, b)

    mean_gap_is_six = abs(gap - 6.0) < 1e-9
    print("  seed-mean gap A - B = %s (%.1f - %.1f = %.1f)" % (mean_gap_is_six, mean_a, mean_b, gap))

    single_run_can_flip = worst < 0
    print("  a single-run comparison can show B ahead of A = %s (worst-for-A gap = %+.1f)" % (single_run_can_flip, worst))

    single_run_range_wide = (best - worst) > abs(gap)
    print("  the single-run gap range (%+.1f..%+.1f) dwarfs the true gap = %s" % (worst, best, single_run_range_wide))

    mean_gap_solid = abs(gap) / se >= 2.0
    print("  the seed-mean gap is large vs its standard error = %s (t = %.1f / %.1f = %.1f)" % (mean_gap_solid, gap, se, gap / se))

    runs_vary = sample_std(a) > 0 and sample_std(b) > 0
    print("  the per-seed scores genuinely vary run to run = %s (std A=%.2f, B=%.2f)" % (runs_vary, sample_std(a), sample_std(b)))

    ok = mean_gap_is_six and single_run_can_flip and single_run_range_wide and mean_gap_solid and runs_vary
    print("-" * 100)
    print("SELF-TEST %s  mean_gap_is_six=%s  single_run_can_flip=%s  single_run_range_wide=%s  mean_gap_solid=%s  runs_vary=%s"
          % ("PASS" if ok else "FAIL", mean_gap_is_six, single_run_can_flip, single_run_range_wide, mean_gap_solid, runs_vary))
    return ok


def main():
    p = argparse.ArgumentParser(description="Run-to-run variance: report a sampled model's benchmark score as a mean over multiple seeds together with its spread, and compare models by those means against the combined standard error, never by a single run, because run-to-run variance can make one lucky or unlucky seed flip the apparent winner even when the true seed-averaged gap is solid.")
    p.add_argument("--seeds", action="store_true")
    p.add_argument("--single", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("model_a=%s  model_b=%s  file=%s  (the per-seed scores are a fixture)"
          % (data["model_a"]["seed_scores"], data["model_b"]["seed_scores"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.seeds:
        seeds_view(data)
    elif args.single:
        single_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
