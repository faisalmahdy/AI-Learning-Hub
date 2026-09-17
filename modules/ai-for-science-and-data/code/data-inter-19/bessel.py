"""Divide the sample variance by n-1, or dividing by n underestimates the spread every time.

To estimate how spread out a population is, you take a sample and compute its variance: the average squared
distance of the points from their mean. The obvious formula divides the sum of squared deviations by n, the
sample size. It is biased -- it comes out too small, systematically, on average. The reason is subtle: you
measure the deviations from the SAMPLE mean, not the true population mean, and the sample mean is the point
that MINIMIZES the sum of squared deviations for that sample. So the sample's points are always at least as
close to their own mean as to the true mean, and dividing by n inherits that closeness as an underestimate.
You are using the data twice -- once to locate the center, once to measure spread around it -- and the second
use gets an unfair discount from the first.

Bessel's correction fixes it: divide by n-1 instead of n. Estimating the mean from the sample "used up" one
degree of freedom, and dividing by the remaining n-1 exactly compensates, so the corrected variance is
unbiased -- its average over all possible samples equals the true population variance. The correction matters
most for small samples (n-1 is a big discount off n) and fades as n grows (n-1 approaches n). This is why the
sample-variance button on a calculator, and the default in numpy's ddof and pandas, divides by n-1.

On this fixture the population is 1, 4, 7 with true variance 6. Enumerating all 9 samples of size 2 and
averaging: the n-divisor variance averages 3.0 -- exactly half the truth -- while the (n-1)-divisor averages
6.0, dead on. This computes both, exactly, by enumeration.

  --samples    every sample of size n, its mean, and its variance under each divisor
  --bias       the average of each divisor's variance vs the true population variance
  --check      dividing by n is biased low by (n-1)/n; dividing by n-1 is unbiased

The population and sample size are the fixture; every variance is computed. Stdlib only.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "population.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def population_variance(pop):
    """The true variance: average squared deviation from the population mean."""
    m = mean(pop)
    return sum((x - m) ** 2 for x in pop) / len(pop)


def sample_variance(sample, ddof):
    """Sum of squared deviations from the sample mean, divided by (n - ddof). ddof=0 is /n; ddof=1 is /(n-1)."""
    m = mean(sample)
    ss = sum((x - m) ** 2 for x in sample)
    return ss / (len(sample) - ddof)


def all_samples(pop, n):
    return list(itertools.product(pop, repeat=n))


# ----------------------------------------------------------------- printing

def samples_view(data):
    pop, n = data["population"], data["sample_size"]
    print("SAMPLES — every size-%d sample of %s, with both sample variances" % (n, pop))
    print("-" * 60)
    print("  sample     mean    var (/n)   var (/n-1)")
    for s in all_samples(pop, n):
        print("  %-9s  %.2f    %6.2f      %6.2f" % (str(s), mean(s), sample_variance(s, 0), sample_variance(s, 1)))
    print("-" * 60)
    print("  the /n column runs small; the /n-1 column runs larger.")


def bias_view(data):
    pop, n = data["population"], data["sample_size"]
    samples = all_samples(pop, n)
    avg_n = mean([sample_variance(s, 0) for s in samples])
    avg_n1 = mean([sample_variance(s, 1) for s in samples])
    sig2 = population_variance(pop)
    print("BIAS — expected sample variance (averaged over all %d samples) vs the truth" % len(samples))
    print("-" * 60)
    print("  true population variance:       %.2f" % sig2)
    print("  average of /n     variance:     %.2f   (biased low)" % avg_n)
    print("  average of /(n-1) variance:     %.2f   (unbiased)" % avg_n1)
    print("  the /n bias factor is (n-1)/n = %d/%d = %.2f, so %.2f*%.2f = %.2f" % (n - 1, n, (n - 1) / n, sig2, (n - 1) / n, sig2 * (n - 1) / n))
    print("-" * 60)
    print("  using the sample mean to center costs one degree of freedom.")


def check(data):
    print("SELF-TEST — dividing by n is biased low by (n-1)/n; dividing by n-1 is unbiased")
    print("-" * 100)
    pop, n = data["population"], data["sample_size"]
    samples = all_samples(pop, n)
    avg_n = mean([sample_variance(s, 0) for s in samples])
    avg_n1 = mean([sample_variance(s, 1) for s in samples])
    sig2 = population_variance(pop)

    n_divisor_biased_low = avg_n < sig2
    print("  the /n variance averages below the truth = %s (%.2f < %.2f)" % (n_divisor_biased_low, avg_n, sig2))

    n1_divisor_unbiased = abs(avg_n1 - sig2) < 1e-9
    print("  the /(n-1) variance averages exactly the truth = %s (%.2f = %.2f)" % (n1_divisor_unbiased, avg_n1, sig2))

    bias_is_n1_over_n = abs(avg_n - sig2 * (n - 1) / n) < 1e-9
    print("  the /n bias is exactly the factor (n-1)/n = %s (%.2f = %.2f*%.2f)" % (bias_is_n1_over_n, avg_n, sig2, (n - 1) / n))

    correction_scales_each = all(abs(sample_variance(s, 1) - sample_variance(s, 0) * n / (n - 1)) < 1e-9 for s in samples)
    print("  each /(n-1) variance is n/(n-1) times its /n variance = %s" % correction_scales_each)

    enumerated_all = len(samples) == len(pop) ** n
    print("  the expectation was computed by full enumeration = %s (%d samples)" % (enumerated_all, len(samples)))

    ok = n_divisor_biased_low and n1_divisor_unbiased and bias_is_n1_over_n and correction_scales_each and enumerated_all
    print("-" * 100)
    print("SELF-TEST %s  n_divisor_biased_low=%s  n1_divisor_unbiased=%s  bias_is_n1_over_n=%s  correction_scales_each=%s  enumerated_all=%s"
          % ("PASS" if ok else "FAIL", n_divisor_biased_low, n1_divisor_unbiased, bias_is_n1_over_n, correction_scales_each, enumerated_all))
    return ok


def main():
    p = argparse.ArgumentParser(description="Divide the sample variance by n-1 (Bessel's correction) so it is an unbiased estimate.")
    p.add_argument("--samples", action="store_true")
    p.add_argument("--bias", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("population=%s  sample_size=%d  file=%s  (the population is a fixture)"
          % (data["population"], data["sample_size"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.samples:
        samples_view(data)
    elif args.bias:
        bias_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
