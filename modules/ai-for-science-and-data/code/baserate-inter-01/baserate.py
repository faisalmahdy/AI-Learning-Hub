"""A 99% test for a 1% disease is right about a positive only half the time -- the base rate, not the accuracy, decides.

Ask most people: a test is 99% accurate, you test positive for a disease, how likely is it that you have it? The
intuitive answer is 99%. The correct answer, for a disease that 1% of people have, is 50% -- and the gap between those
two numbers is the single most consequential mistake in reading a diagnostic test, a spam filter, a fraud flag, or any
classifier for a rare event. The intuition confuses P(positive | disease), the test's sensitivity, with P(disease |
positive), the thing you actually want to know, and those are only equal when the disease is as common as its absence.
When the event is rare they diverge sharply, because the answer depends on the BASE RATE -- how common the disease is
before any test -- and the intuition simply leaves the base rate out.

Count actual people and it becomes obvious. Take 100,000 people with a 1% disease: 1,000 are sick and 99,000 are healthy.
A test with 99% sensitivity flags 990 of the 1,000 sick people (true positives). The same test with 99% specificity has a
1% false-positive rate, and 1% of the 99,000 healthy people is 990 people flagged in error (false positives). So a
positive test comes from a sick person 990 times and from a healthy person 990 times: 1,980 positives, of which exactly
half are real. The false positives are not a rounding error; they come from a group ninety-nine times larger than the
sick group, so even a tiny false-positive rate on that huge group produces as many positives as the accurate test does
on the few who are sick. The rarer the disease, the more the healthy group's false positives dominate, and the less a
positive means.

This is why the base rate cannot be dropped, and why the fix is to reason in natural frequencies (990 vs 990) rather than
in percentages, and to apply Bayes' theorem, which just formalizes the counting: the posterior probability of disease
given a positive is the true positives over all positives. It is also why rare-event screening confirms positives with a
second, independent test: one test cannot overcome a base rate, but stacking the (now much higher) post-test probability
into a second test can.

On this fixture, prevalence 1%, sensitivity 99%, specificity 99%: a positive test means disease with probability 0.50,
not 0.99. Sweeping the prevalence shows the base rate driving it: at 0.1% a positive is only 9% likely to be real, at 1%
it is 50%, at 10% it is 92%. This computes both.

  --posterior   the confusion counts for one positive test, the naive 99% answer, and the true PPV of 0.50
  --prevalence  the same 99%/99% test across base rates -- PPV climbs from 9% to 50% to 92% as the disease gets commoner
  --check       false positives equal true positives at 1% prevalence, so PPV is 0.50 not 0.99; PPV rises with prevalence

The population, prevalence, and test rates are the fixture; every count and probability is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "baserate.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def confusion(population, prevalence, sensitivity, specificity):
    """Count true/false positives and negatives over a whole population -- Bayes as headcount."""
    sick = round(population * prevalence)
    healthy = population - sick
    tp = round(sick * sensitivity)
    fn = sick - tp
    fp = round(healthy * (1 - specificity))
    tn = healthy - fp
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn}


def ppv(c):
    """Positive predictive value: P(disease | positive) = true positives / all positives."""
    positives = c["tp"] + c["fp"]
    return c["tp"] / positives if positives else 0.0


# ----------------------------------------------------------------- printing

def posterior_view(data):
    pop, prev = data["population"], data["prevalence"]
    sens, spec = data["sensitivity"], data["specificity"]
    c = confusion(pop, prev, sens, spec)
    print("POSTERIOR — P(disease | positive) for a %.0f%% test on a %.0f%% disease" % (sens * 100, prev * 100))
    print("-" * 66)
    print("  population %d: %d sick, %d healthy" % (pop, pop * prev, pop - pop * prev))
    print("  true positives  (sick, test +)    = %d" % c["tp"])
    print("  false positives (healthy, test +) = %d" % c["fp"])
    print("  total positives                   = %d" % (c["tp"] + c["fp"]))
    print("-" * 66)
    print("  naive answer (the sensitivity)      = %.2f" % sens)
    print("  true PPV = %d / %d                = %.2f  <- a positive is real only half the time"
          % (c["tp"], c["tp"] + c["fp"], ppv(c)))


def prevalence_view(data):
    pop = data["population"]
    sens, spec = data["sensitivity"], data["specificity"]
    print("PREVALENCE — the same %.0f%%/%.0f%% test across base rates" % (sens * 100, spec * 100))
    print("-" * 60)
    print("  prevalence   true pos   false pos   PPV")
    for prev in data["prevalence_sweep"]:
        c = confusion(pop, prev, sens, spec)
        print("  %-11s  %-9d  %-10d  %.4f" % ("%.1f%%" % (prev * 100), c["tp"], c["fp"], ppv(c)))
    print("-" * 60)
    print("  the test never changed; the base rate alone moves the PPV from 9% to 92%.")


def check(data):
    print("SELF-TEST — false positives equal true positives at 1% prevalence, so PPV is 0.50 not 0.99; PPV rises with prevalence")
    print("-" * 120)
    pop, prev = data["population"], data["prevalence"]
    sens, spec = data["sensitivity"], data["specificity"]
    c = confusion(pop, prev, sens, spec)

    fp_equals_tp = c["fp"] == c["tp"]
    print("  at 1%% prevalence the false positives equal the true positives = %s (%d == %d)" % (fp_equals_tp, c["fp"], c["tp"]))

    ppv_is_half = abs(ppv(c) - 0.5) < 1e-9
    print("  so PPV = P(disease | positive) is 0.50 = %s (%.4f)" % (ppv_is_half, ppv(c)))

    naive_overstates = sens - ppv(c) > 0.4
    print("  the naive answer (the %.2f sensitivity) overstates PPV by far = %s (%.2f vs %.2f)"
          % (sens, naive_overstates, sens, ppv(c)))

    ppvs = [ppv(confusion(pop, p, sens, spec)) for p in data["prevalence_sweep"]]
    ppv_rises = all(ppvs[i] < ppvs[i + 1] for i in range(len(ppvs) - 1))
    print("  PPV rises strictly with prevalence = %s (%s)" % (ppv_rises, [round(x, 3) for x in ppvs]))

    counts_sum = c["tp"] + c["fn"] + c["fp"] + c["tn"] == pop
    print("  the four cells sum to the whole population = %s (%d)" % (counts_sum, pop))

    ok = fp_equals_tp and ppv_is_half and naive_overstates and ppv_rises and counts_sum
    print("-" * 120)
    print("SELF-TEST %s  fp_equals_tp=%s  ppv_is_half=%s  naive_overstates=%s  ppv_rises=%s  counts_sum=%s"
          % ("PASS" if ok else "FAIL", fp_equals_tp, ppv_is_half, naive_overstates, ppv_rises, counts_sum))
    return ok


def main():
    p = argparse.ArgumentParser(description="Base-rate neglect: for a rare condition, P(disease | positive) depends on the base rate, not just the test accuracy, so a 99%-accurate test for a 1%-prevalence disease has a positive predictive value of only 50% because the huge healthy group's false positives match the sick group's true positives; count in natural frequencies and apply Bayes.")
    p.add_argument("--posterior", action="store_true")
    p.add_argument("--prevalence", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("population=%d  prevalence=%.3f  sensitivity=%.2f  specificity=%.2f  file=%s  (the rates are a fixture)"
          % (data["population"], data["prevalence"], data["sensitivity"], data["specificity"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.posterior:
        posterior_view(data)
    elif args.prevalence:
        prevalence_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
