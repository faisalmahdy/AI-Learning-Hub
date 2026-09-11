"""Size the mastery quiz to the decision, or a three-item gate misclassifies masters and non-masters alike.

A mastery gate turns a noisy measurement into a yes/no decision: answer enough items and you advance. But
a short quiz is a noisy measurement, and a noisy measurement makes an unreliable decision. Two errors
follow. A non-master gets a lucky run and passes -- a false pass, which advances a learner over a gap that
will compound downstream. A master has one bad item and fails -- a false fail, which wastes their time and
erodes trust in the tutor. A naive 'get them all right' gate on three items is bad at both: a learner who
truly knows 60% of the material passes three-for-three often enough to matter, and a learner who knows 90%
fails to run the table more often than you would ever accept.

The fix is not a cleverer threshold; it is more items. Each item is an independent noisy sample of the same
skill, so averaging more of them shrinks the noise, and a proportion threshold near the midpoint between a
master and a non-master separates them cleanly once you have enough items. The quiz length is not a matter
of taste -- it is set by how reliable the advance/hold decision needs to be, exactly as a poll's sample
size is set by the margin of error it must beat.

On this fixture a non-master truly knows 60% and a master 90%, and the gate requires 75% correct. At 3
items the total misclassification rate is 0.487 -- a coin flip -- with the master failing 27% of the time.
At 10 items it falls to 0.237, at 20 items to 0.137, and at 40 items to 0.037. Same learners, same
threshold; only the quiz length changed. This computes all four.

  --rates      false-pass, false-fail, and total error for each quiz length
  --gate       how many correct each length requires, and the naive all-correct short gate
  --check      a short quiz misclassifies both ways; lengthening it drives the total error down

The two skills, the pass fraction, and the quiz lengths are the fixture; every rate is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "quiz.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def p_at_least(k, n, p):
    """Probability of getting at least k of n items right at per-item skill p -- exact binomial."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def need(n, frac):
    """Items required to pass a length-n quiz at a pass fraction -- rounded up."""
    return math.ceil(frac * n)


def false_pass(n, frac, nonmaster):
    """A non-master clears the gate by luck."""
    return p_at_least(need(n, frac), n, nonmaster)


def false_fail(n, frac, master):
    """A master misses the gate by an unlucky slip."""
    return 1.0 - p_at_least(need(n, frac), n, master)


def total_error(n, frac, nonmaster, master):
    return false_pass(n, frac, nonmaster) + false_fail(n, frac, master)


# ----------------------------------------------------------------- printing

def rates_view(data):
    frac, nm, ms = data["pass_fraction"], data["nonmaster_skill"], data["master_skill"]
    print("RATES — misclassification at each quiz length (non-master %.0f%%, master %.0f%%, gate %.0f%%)"
          % (nm * 100, ms * 100, frac * 100))
    print("-" * 66)
    print("  items   need   false pass   false fail   total error")
    for n in data["quiz_lengths"]:
        print("  %-5d   %-4d   %10.3f   %10.3f   %10.3f"
              % (n, need(n, frac), false_pass(n, frac, nm), false_fail(n, frac, ms), total_error(n, frac, nm, ms)))
    print("-" * 66)
    print("  more items shrink the noise, so the total error falls.")


def gate_view(data):
    frac, nm, ms = data["pass_fraction"], data["nonmaster_skill"], data["master_skill"]
    print("GATE — what each quiz length requires, plus the naive all-correct short gate")
    print("-" * 66)
    for n in data["quiz_lengths"]:
        print("  %2d items: need %d correct (%.0f%%)" % (n, need(n, frac), frac * 100))
    print("-" * 66)
    short = min(data["quiz_lengths"])
    print("  naive gate — all %d correct:" % short)
    print("    non-master passes %.3f of the time (false pass)" % (nm ** short))
    print("    master passes only %.3f, so fails %.3f (false fail)" % (ms ** short, 1 - ms ** short))


def check(data):
    print("SELF-TEST — a short quiz misclassifies both ways; lengthening it drives the total error down")
    print("-" * 92)
    frac, nm, ms = data["pass_fraction"], data["nonmaster_skill"], data["master_skill"]
    lens = data["quiz_lengths"]
    errs = [total_error(n, frac, nm, ms) for n in lens]

    short_unreliable = errs[0] > 0.4
    print("  the shortest quiz is barely better than a coin flip = %s (total error %.3f at %d items)"
          % (short_unreliable, errs[0], lens[0]))

    short_fails_master = false_fail(lens[0], frac, ms) > 0.2
    print("  the shortest quiz fails a true master too often = %s (false fail %.3f)"
          % (short_fails_master, false_fail(lens[0], frac, ms)))

    error_shrinks = all(errs[i] > errs[i + 1] for i in range(len(errs) - 1))
    print("  total error falls monotonically as the quiz lengthens = %s (%s)"
          % (error_shrinks, [round(e, 3) for e in errs]))

    long_reliable = errs[-1] < 0.1
    print("  the longest quiz is reliable = %s (total error %.3f at %d items)"
          % (long_reliable, errs[-1], lens[-1]))

    ok = short_unreliable and short_fails_master and error_shrinks and long_reliable
    print("-" * 92)
    print("SELF-TEST %s  short_unreliable=%s  short_fails_master=%s  error_shrinks=%s  long_reliable=%s"
          % ("PASS" if ok else "FAIL", short_unreliable, short_fails_master, error_shrinks, long_reliable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Size the mastery quiz to the decision so it does not misclassify learners.")
    p.add_argument("--rates", action="store_true")
    p.add_argument("--gate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("nonmaster=%.2f  master=%.2f  pass_fraction=%.2f  lengths=%s  file=%s  (the skills and lengths are a fixture)"
          % (data["nonmaster_skill"], data["master_skill"], data["pass_fraction"], data["quiz_lengths"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rates:
        rates_view(data)
    elif args.gate:
        gate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
