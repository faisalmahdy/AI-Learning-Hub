"""Real data's leading digits follow Benford's law -- fabricated numbers don't, and that flags them.

Count the first digit of every number in a large real-world dataset -- populations, prices,
physical constants, transaction amounts -- and the digits are not uniform. The digit 1 leads
about 30% of the time and 9 barely 5%, following Benford's law: the probability that the first
digit is d is log10(1 + 1/d). It arises whenever data spans several orders of magnitude, because
what is uniform is the exponent, not the value, so numbers spend more of their range with a
small leading digit.

This is a fraud detector. A person inventing numbers to look random tends to spread the first
digits evenly, because uniform feels random -- but real data is Benford, not uniform, so the
fabricated set's flat first-digit distribution stands out. Here a genuine multi-scale dataset
matches Benford with a total deviation of 0.024, while a fabricated dataset with hand-picked
'random' values deviates 0.47 -- twenty times as far -- so a deviation threshold flags the fake
and clears the real one. This generates both datasets, tallies their leading digits, compares
each to Benford's expected distribution, and shows the fabricated one caught.

  --benford    Benford's expected first-digit distribution
  --data       each dataset's observed first-digit distribution and its deviation from Benford
  --check      the real data conforms, the fabricated data deviates, and the threshold flags the fake

The dataset sizes and the flag threshold are the fixture; the numbers, digits, and deviations
are all generated and computed. Deterministic; stdlib only.
"""
import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "config.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- Benford's law

def benford_expected():
    """P(first digit = d) = log10(1 + 1/d), for d in 1..9."""
    return {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def first_digit(x):
    """The leading significant digit of x (scale-invariant)."""
    x = abs(x)
    if x == 0:
        return 0
    while x >= 10:
        x /= 10
    while x < 1:
        x *= 10
    return int(x)


# ------------------------------------------------------------- the two datasets (generated)

def real_dataset(n):
    """Genuine multi-scale data: values spanning many orders of magnitude (log-uniform)."""
    return [10 ** (k / 120) for k in range(n)]


def fabricated_dataset(n):
    """Made-up 'random' numbers: a person spreading first digits evenly (uniform), which real data never is."""
    return [((k % 9) + 1) * 10 ** (k % 4) + (k % 7) for k in range(n)]


# ------------------------------------------------------------- observed distribution and deviation

def observed(dataset):
    c = Counter(first_digit(v) for v in dataset)
    total = sum(c[d] for d in range(1, 10))
    return {d: c[d] / total for d in range(1, 10)}


def deviation(dataset):
    """Total absolute distance between the observed and Benford's expected first-digit distribution."""
    obs, exp = observed(dataset), benford_expected()
    return sum(abs(obs[d] - exp[d]) for d in range(1, 10))


# ----------------------------------------------------------------- printing

def benford_view(data):
    exp = benford_expected()
    print("BENFORD — expected first-digit distribution (log10(1 + 1/d))")
    print("-" * 46)
    for d in range(1, 10):
        print("  digit %d: %.3f  %s" % (d, exp[d], "#" * round(exp[d] * 100)))
    print("-" * 46)
    print("  1 leads ~30% of the time, 9 barely 5% -- not uniform.")


def data_view(data):
    real = real_dataset(data["n_real"])
    fake = fabricated_dataset(data["n_fabricated"])
    exp = benford_expected()
    o_real, o_fake = observed(real), observed(fake)
    print("DATA — observed first-digit distribution vs Benford")
    print("-" * 60)
    print("  digit  benford  real data  fabricated")
    for d in range(1, 10):
        print("  %d      %.3f    %.3f      %.3f" % (d, exp[d], o_real[d], o_fake[d]))
    print("-" * 60)
    print("  real deviation: %.4f    fabricated deviation: %.4f" % (deviation(real), deviation(fake)))


def check(data):
    print("SELF-TEST — real data conforms to Benford; fabricated data deviates; the threshold flags the fake")
    print("-" * 66)
    thr = data["threshold"]
    real = real_dataset(data["n_real"])
    fake = fabricated_dataset(data["n_fabricated"])

    exp = benford_expected()
    benford_sums = abs(sum(exp.values()) - 1.0) < 1e-9 and max(exp, key=exp.get) == 1
    print("  Benford's expected distribution sums to 1 and peaks at digit 1 = %s" % benford_sums)

    d_real, d_fake = deviation(real), deviation(fake)
    real_conforms = d_real < thr
    print("  the real dataset conforms to Benford (deviation below threshold) = %s (%.4f < %.2f)"
          % (real_conforms, d_real, thr))

    fake_deviates = d_fake > thr
    print("  the fabricated dataset deviates from Benford = %s (%.4f > %.2f)" % (fake_deviates, d_fake, thr))

    fake_far_worse = d_fake > 5 * d_real
    print("  the fabricated deviation is many times the real one = %s (%.4f vs %.4f, %.1fx)"
          % (fake_far_worse, d_fake, d_real, d_fake / d_real))

    ok = benford_sums and real_conforms and fake_deviates and fake_far_worse
    print("-" * 66)
    print("SELF-TEST %s  benford_sums=%s  real_conforms=%s  fake_deviates=%s  fake_far_worse=%s"
          % ("PASS" if ok else "FAIL", benford_sums, real_conforms, fake_deviates, fake_far_worse))
    return ok


def main():
    p = argparse.ArgumentParser(description="Benford's law as a fabricated-data detector.")
    p.add_argument("--benford", action="store_true")
    p.add_argument("--data", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_real=%d  n_fabricated=%d  threshold=%.2f  file=%s  (sizes and threshold are a fixture)"
          % (data["n_real"], data["n_fabricated"], data["threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.benford:
        benford_view(data)
    elif args.data:
        data_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
