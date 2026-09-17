"""The standard deviation and the standard error answer two different questions and cannot be swapped -- the SD says how spread out the individual measurements are and does not shrink with more data, while the standard error of the mean (SD / sqrt(n)) says how precisely the sample mean estimates the true mean and shrinks as sqrt(n); putting one where the other belongs either overstates the mean's uncertainty by a factor of sqrt(n) or understates the spread of individuals by the same factor.

You measure something n times and report "mean +/- something". The something is where the confusion lives, because there are two different spreads and they are not interchangeable.

The standard deviation (SD) describes the data: how far a typical single measurement sits from the mean. It is a property of the thing you are measuring and the noise in one measurement, so collecting more data pins it down but does NOT make it smaller -- people genuinely vary by that much no matter how many you sample.

The standard error of the mean (SEM = SD / sqrt(n)) describes the estimate: how far the sample mean is likely to sit from the true mean. It is not about the data's spread but about the precision of one number computed from the data, so it shrinks as you gather more -- quadruple n and the SEM halves.

Swap them and you get two symmetric errors. Report the mean with an error bar of one SD and you overstate its uncertainty by sqrt(n), and the bar absurdly never tightens as data piles up. Report a range for a typical individual as mean +/- SEM and you understate the spread by sqrt(n), claiming most measurements land in a band that most measurements actually fall outside. The tell is coverage: only a minority of individual points lie within mean +/- SEM, while most lie within mean +/- SD, because SEM was never a range for individuals.

On this fixture of n measurements the code computes the mean, the sample SD, and the SEM = SD/sqrt(n), shows how the SEM would change at 4x and 1/4x the sample size while the SD would not, and counts how many individual points fall within mean +/- SD versus mean +/- SEM.

  --describe  the mean, SD, and SEM, and how the SEM (not the SD) scales with the sample size
  --coverage  how many individual points fall within mean +/- SD versus mean +/- SEM
  --check     the SEM is SD/sqrt(n) and smaller than the SD, quadrupling n halves it, most individuals fall within one SD, and only a minority within one SEM

the measurements are the fixture; the mean, SD, SEM, its scaling, and both coverage counts are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "sdse.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    """The arithmetic mean of the sample."""
    return sum(xs) / len(xs)


def sample_sd(xs):
    """The sample standard deviation: the spread of individual measurements (uses n-1)."""
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def sem(xs):
    """The standard error of the mean: the uncertainty of the sample mean, SD / sqrt(n)."""
    return sample_sd(xs) / math.sqrt(len(xs))


def sem_at(sd, n):
    """The SEM the same SD would give at a chosen sample size -- shows the sqrt(n) scaling."""
    return sd / math.sqrt(n)


def coverage(xs, half_width):
    """How many individual points fall within mean +/- half_width."""
    m = mean(xs)
    return sum(1 for x in xs if m - half_width <= x <= m + half_width)


# ----------------------------------------------------------------- printing

def describe_view(data):
    xs = data["measurements"]
    n = len(xs)
    m, sd, se = mean(xs), sample_sd(xs), sem(xs)
    print("DESCRIBE — %s, n=%d" % (data["label"], n))
    print("-" * 64)
    print("  mean            = %.2f" % m)
    print("  SD  (spread of individuals)      = %.2f   -- does not shrink with n" % sd)
    print("  SEM (uncertainty of the mean)    = %.2f   = SD / sqrt(%d)" % (se, n))
    print("  if n were %d (4x):  SEM = %.2f   SD = %.2f (unchanged)" % (4 * n, sem_at(sd, 4 * n), sd))
    print("  if n were %d (1/4x): SEM = %.2f   SD = %.2f (unchanged)" % (n // 4, sem_at(sd, n // 4), sd))
    print("-" * 64)
    print("  more data tightens the mean (SEM falls) but not the spread (SD holds)")


def coverage_view(data):
    xs = data["measurements"]
    n = len(xs)
    m, sd, se = mean(xs), sample_sd(xs), sem(xs)
    in_sd, in_se = coverage(xs, sd), coverage(xs, se)
    print("COVERAGE — how many of the %d points fall in each band" % n)
    print("-" * 64)
    print("  mean +/- SD  = [%.2f, %.2f]  contains %d of %d points (%.0f%%)" % (m - sd, m + sd, in_sd, n, 100 * in_sd / n))
    print("  mean +/- SEM = [%.2f, %.2f]  contains %d of %d points (%.0f%%)" % (m - se, m + se, in_se, n, 100 * in_se / n))
    print("-" * 64)
    print("  SD is a range for individuals; SEM is not -- most points fall outside +/- SEM")


def check(data):
    print("SELF-TEST — the SEM is SD/sqrt(n) and smaller than the SD, quadrupling n halves it, most individuals fall within one SD, and only a minority within one SEM")
    print("-" * 112)
    xs = data["measurements"]
    n = len(xs)
    m, sd, se = mean(xs), sample_sd(xs), sem(xs)

    sem_is_sd_over_sqrt_n = abs(se * math.sqrt(n) - sd) < 1e-9
    print("  SEM * sqrt(n) equals the SD (SEM = SD/sqrt(n)) = %s (%.4f == %.4f)" % (sem_is_sd_over_sqrt_n, se * math.sqrt(n), sd))

    sem_smaller_than_sd = se < sd
    print("  SEM is smaller than the SD = %s (%.2f < %.2f)" % (sem_smaller_than_sd, se, sd))

    quadrupling_halves_sem = abs(sem_at(sd, 4 * n) - se / 2) < 1e-9
    print("  quadrupling n halves the SEM = %s (%.4f == %.4f)" % (quadrupling_halves_sem, sem_at(sd, 4 * n), se / 2))

    in_sd, in_se = coverage(xs, sd), coverage(xs, se)
    sd_covers_most = in_sd / n >= 0.6
    print("  most individuals fall within mean +/- SD = %s (%d of %d)" % (sd_covers_most, in_sd, n))

    sem_covers_few = in_se / n <= 0.4
    print("  only a minority fall within mean +/- SEM = %s (%d of %d)" % (sem_covers_few, in_se, n))

    ok = (sem_is_sd_over_sqrt_n and sem_smaller_than_sd and quadrupling_halves_sem
          and sd_covers_most and sem_covers_few)
    print("-" * 112)
    print("SELF-TEST %s  sem_is_sd_over_sqrt_n=%s  sem_smaller_than_sd=%s  quadrupling_halves_sem=%s  sd_covers_most=%s  sem_covers_few=%s"
          % ("PASS" if ok else "FAIL", sem_is_sd_over_sqrt_n, sem_smaller_than_sd, quadrupling_halves_sem,
             sd_covers_most, sem_covers_few))
    return ok


def main():
    p = argparse.ArgumentParser(description="SD versus SEM: the standard deviation describes the spread of individual measurements and does not shrink with more data, while the standard error of the mean (SD/sqrt(n)) describes the uncertainty of the sample mean and shrinks as sqrt(n) -- so an error bar of one SD on the mean overstates its uncertainty by sqrt(n) and never tightens, and a range of mean +/- SEM for a typical individual understates the spread by sqrt(n) and excludes most of the data.")
    p.add_argument("--describe", action="store_true")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n=%d  label=%s  file=%s" % (len(data["measurements"]), data["label"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.describe:
        describe_view(data)
    elif args.coverage:
        coverage_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
