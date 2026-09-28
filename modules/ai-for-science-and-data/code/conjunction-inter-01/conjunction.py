"""A conjunction is never more probable than its parts -- yet the detailed, representative story feels the most likely.

Ask which is more probable: that someone is a bank teller, or that they are a bank teller AND an activist. Add a vivid,
fitting detail -- the person was described as socially engaged -- and intuition insists the second is more likely,
because it paints a more coherent, representative picture. It cannot be. The people who are both tellers and activists
are a SUBSET of the people who are tellers, so their count is smaller or equal, and their probability is smaller or
equal. Every condition you add to a hypothesis can only shrink the set of things that satisfy it, so a more specific
hypothesis is never more probable than a less specific one it contains. P(A and B) <= P(A), always, with no exceptions.

The trap is that the mind judges probability by REPRESENTATIVENESS -- how well the description fits a mental prototype --
not by set size, and adding a fitting detail raises representativeness while lowering probability. The two move in
opposite directions, so the more a story is fleshed out to match the evidence, the more plausible it feels and the less
probable it actually is. This is not a party trick about tellers; it is why a specific, detailed forecast ("recession
caused by an oil shock in the third quarter") is rated more likely than the broad event that contains it ("recession"),
why an over-fitted narrative that explains every data point beats a simple one, and why adding assumptions to an
explanation makes it feel stronger while making it mathematically weaker.

On this fixture the population has 4 tellers, of whom 1 is also an activist, so P(teller) = 4/12 = 0.33 while
P(teller and activist) = 1/12 = 0.08 -- the conjunction is a quarter as probable, though it sounds more specific and
fitting. The same holds for every tag pair: the conjunction's probability never exceeds either part's. This computes it.

  --rank     the single-hypothesis probability vs the conjunction's, for each pair -- the conjunction is always lower
  --space    the people matching the broad hypothesis vs the conjunction -- the conjunction is a strict subset
  --check    P(A and B) <= P(A) and <= P(B) for every pair; adding a condition never raises probability

The population and tag pairs are the fixture; every probability is an exact count. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "conjunction.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def matches(population, tags):
    """Indices of people whose tag set contains every tag in `tags`."""
    return [i for i, person in enumerate(population) if all(t in person for t in tags)]


def prob(population, tags):
    """The fraction of the population matching all of `tags` -- our probability estimate."""
    return len(matches(population, tags)) / len(population)


# ----------------------------------------------------------------- printing

def rank_view(data):
    pop = data["population"]
    print("RANK — P(single hypothesis) vs P(the conjunction), for each pair (n=%d)" % len(pop))
    print("-" * 70)
    print("  broad hypothesis        conjunction                     P(broad)  P(both)")
    for broad, extra in data["pairs"]:
        pb = prob(pop, [broad])
        pj = prob(pop, [broad, extra])
        print("  %-22s  %-30s  %.3f     %.3f" % ("'%s'" % broad, "'%s and %s'" % (broad, extra), pb, pj))
    print("-" * 70)
    print("  the conjunction sounds more specific and fitting, yet its probability is never higher.")


def space_view(data):
    pop = data["population"]
    broad, extra = data["pairs"][0]
    b = matches(pop, [broad])
    j = matches(pop, [broad, extra])
    print("SPACE — who matches '%s' vs '%s and %s'" % (broad, broad, extra))
    print("-" * 60)
    print("  match '%s':            people %s  (%d)" % (broad, b, len(b)))
    print("  match '%s and %s':  people %s  (%d)" % (broad, extra, j, len(j)))
    print("  is the conjunction a subset of the broad set? %s" % set(j).issubset(set(b)))
    print("-" * 60)
    print("  adding 'and %s' can only remove people, never add them, so the count only shrinks." % extra)


def check(data):
    print("SELF-TEST — P(A and B) <= P(A) and <= P(B) for every pair; adding a condition never raises probability")
    print("-" * 108)
    pop = data["population"]

    conj_le_broad = all(prob(pop, [a, b]) <= prob(pop, [a]) for a, b in data["pairs"])
    print("  every conjunction is no more probable than its broad part = %s" % conj_le_broad)

    conj_le_extra = all(prob(pop, [a, b]) <= prob(pop, [b]) for a, b in data["pairs"])
    print("  every conjunction is no more probable than its extra part = %s" % conj_le_extra)

    subset_always = all(set(matches(pop, [a, b])).issubset(set(matches(pop, [a]))) for a, b in data["pairs"])
    print("  the conjunction's people are always a subset of the broad set = %s" % subset_always)

    strict_somewhere = any(prob(pop, [a, b]) < prob(pop, [a]) for a, b in data["pairs"])
    print("  at least one conjunction is strictly less probable (the detail costs mass) = %s" % strict_somewhere)

    a0, b0 = data["pairs"][0]
    example_gap = prob(pop, [a0]) - prob(pop, [a0, b0])
    print("  example: P('%s')=%.3f vs P('%s and %s')=%.3f, gap %.3f"
          % (a0, prob(pop, [a0]), a0, b0, prob(pop, [a0, b0]), example_gap))

    ok = conj_le_broad and conj_le_extra and subset_always and strict_somewhere and example_gap > 0
    print("-" * 108)
    print("SELF-TEST %s  conj_le_broad=%s  conj_le_extra=%s  subset_always=%s  strict_somewhere=%s  example_gap>0=%s"
          % ("PASS" if ok else "FAIL", conj_le_broad, conj_le_extra, subset_always, strict_somewhere, example_gap > 0))
    return ok


def main():
    p = argparse.ArgumentParser(description="The conjunction fallacy: P(A and B) can never exceed P(A) or P(B), because the conjunction is a subset -- yet a more detailed, representative hypothesis feels more probable.")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--space", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("population=%d people  pairs=%d  file=%s  (the population is a fixture)"
          % (len(data["population"]), len(data["pairs"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rank:
        rank_view(data)
    elif args.space:
        space_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
