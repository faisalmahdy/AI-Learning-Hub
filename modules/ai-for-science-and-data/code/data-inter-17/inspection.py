"""Average over the right population, or a student experiences a bigger class than the school reports.

"What is the average class size?" has two answers, and they disagree. The administrator averages over
CLASSES: add the sizes, divide by the number of classes. A student, though, does not sample classes -- the
student IS in a class, and a big class holds more students to be in it. So the average size EXPERIENCED by a
randomly chosen student weights each class by its own size: a 40-person class contributes 40 students who all
see a class of 40, while a 10-person class contributes only 10. The student-experienced average is therefore
pulled toward the big classes, and it exceeds the administrator's average whenever class sizes vary at all.

This is length-biased sampling, and it is everywhere: the average number of riders on a bus you board exceeds
the operator's average bus load; the average length of the line you join exceeds the average line length; the
gap between buses that YOU wait in exceeds the average gap, because a long gap is more likely to contain your
random arrival. Sampling proportional to size over-represents the big things. The fix is not a better estimator
-- both averages are correct -- it is naming the population the average is over, because "average class size"
is ambiguous until you say "per class" or "per student."

There is a clean identity: the gap between the two averages is exactly the variance of the sizes divided by
their mean. If every class were the same size, the variance is zero and the two averages coincide; the more
the sizes spread, the wider the gap. On this fixture the classes are 10, 10, 40. The administrator reports a
mean of 20; the average student is in a class of 30 -- a gap of 10, which is the variance 200 over the mean 20.
This computes both.

  --averages   the per-class average vs the per-student average, and how each weights the classes
  --identity   the gap equals variance / mean, and it vanishes when all classes are equal
  --check      the student-experienced average exceeds the per-class average by exactly variance / mean

The class sizes are the fixture; every average is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "classes.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def per_class_mean(sizes):
    """The administrator's average: each class counts once."""
    return sum(sizes) / len(sizes)


def per_student_mean(sizes):
    """The average class size a random student is in: each class weighted by its own size."""
    return sum(s * s for s in sizes) / sum(sizes)


def variance(sizes):
    m = per_class_mean(sizes)
    return sum((s - m) ** 2 for s in sizes) / len(sizes)


# ----------------------------------------------------------------- printing

def averages_view(data):
    sizes = data["sizes"]
    total = sum(sizes)
    print("AVERAGES — the same classes, two populations")
    print("-" * 64)
    print("  class sizes: %s   (%d classes, %d students)" % (sizes, len(sizes), total))
    print("  per class (admin):    %.2f   each class weighted 1" % per_class_mean(sizes))
    print("  per student:          %.2f   each class weighted by its size" % per_student_mean(sizes))
    print("-" * 64)
    print("  weighting classes by their student count pulls the average up.")


def identity_view(data):
    sizes = data["sizes"]
    m, v = per_class_mean(sizes), variance(sizes)
    print("IDENTITY — the gap equals variance / mean")
    print("-" * 64)
    print("  per-student %.2f - per-class %.2f = %.2f" % (per_student_mean(sizes), m, per_student_mean(sizes) - m))
    print("  variance %.2f / mean %.2f = %.2f" % (v, m, v / m))
    uniform = [round(m)] * len(sizes)
    print("  if every class were %d: per-class %.2f, per-student %.2f (gap %.2f)"
          % (round(m), per_class_mean(uniform), per_student_mean(uniform), per_student_mean(uniform) - per_class_mean(uniform)))
    print("-" * 64)
    print("  the spread of sizes IS the gap; equalize the sizes and it disappears.")


def check(data):
    print("SELF-TEST — the student-experienced average exceeds the per-class average by exactly variance / mean")
    print("-" * 104)
    sizes = data["sizes"]
    m, v = per_class_mean(sizes), variance(sizes)
    pc, ps = per_class_mean(sizes), per_student_mean(sizes)

    student_exceeds_class = ps > pc
    print("  the per-student average exceeds the per-class average = %s (%.2f > %.2f)" % (student_exceeds_class, ps, pc))

    gap_is_variance_over_mean = abs((ps - pc) - v / m) < 1e-9
    print("  the gap equals variance / mean = %s (%.4f vs %.4f)" % (gap_is_variance_over_mean, ps - pc, v / m))

    variance_positive = v > 0
    print("  the class sizes actually vary = %s (variance %.2f)" % (variance_positive, v))

    uniform = [m] * len(sizes)
    equal_when_uniform = abs(per_student_mean(uniform) - per_class_mean(uniform)) < 1e-9
    print("  equal-sized classes make the two averages coincide = %s" % equal_when_uniform)

    both_valid = pc == sum(sizes) / len(sizes) and ps == sum(s * s for s in sizes) / sum(sizes)
    print("  both averages are correct for their own population = %s" % both_valid)

    ok = student_exceeds_class and gap_is_variance_over_mean and variance_positive and equal_when_uniform and both_valid
    print("-" * 104)
    print("SELF-TEST %s  student_exceeds_class=%s  gap_is_variance_over_mean=%s  variance_positive=%s  equal_when_uniform=%s  both_valid=%s"
          % ("PASS" if ok else "FAIL", student_exceeds_class, gap_is_variance_over_mean, variance_positive, equal_when_uniform, both_valid))
    return ok


def main():
    p = argparse.ArgumentParser(description="Average over the right population -- per class and per student differ by variance/mean.")
    p.add_argument("--averages", action="store_true")
    p.add_argument("--identity", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("classes=%d  students=%d  file=%s  (the class sizes are a fixture)"
          % (len(data["sizes"]), sum(data["sizes"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.averages:
        averages_view(data)
    elif args.identity:
        identity_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
