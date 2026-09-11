"""Conditioning on a common effect fakes a correlation between independent causes -- Berkson's paradox.

Two traits can be completely independent in the world and still look strongly related the moment you
study a group that was SELECTED using both of them. A studio casts an actor if they are talented
enough OR good-looking enough to carry a film. Talent and looks are independent in the general
population -- knowing one tells you nothing about the other. But among the cast, the two are
negatively correlated: a purely talented actor got in on talent and can be plain, a purely
good-looking one got in on looks and can be wooden, and someone weak on both never got cast. Study
only the famous and you will "discover" a tradeoff that does not exist in anyone who was not selected.

This is collider bias. The selection variable (cast / not cast) is a common effect of talent and
looks -- both arrows point INTO it -- so conditioning on it opens a spurious path between the two
causes. It is the opposite mistake to confounding: there you must adjust for the shared cause, here
adjusting for (selecting on) the shared effect is exactly what creates the illusion.

The fixture is the full 5x5 population of (talent, looks) pairs, one person per combination, so the
two traits are independent by construction and their population correlation is exactly 0. Casting
takes everyone with talent + looks >= 8. This computes the correlation in the whole population and
in the cast subset, and shows the sign appear out of nowhere.

  --population   the full grid and the cast subset, with each trait's marginal spread
  --corr        the talent-looks correlation over everyone vs over the cast only
  --check       the population correlation is ~0; selecting on the collider makes it negative

The population grid and the casting threshold are the fixture; every correlation is computed. Stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "population.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


# ------------------------------------------------------------- correlation

def pearson(pairs):
    """Pearson correlation of a list of (x, y). Returns 0.0 if either trait has no spread."""
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in pairs)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0
    return round(cov / (vx * vy) ** 0.5, 4)


# ------------------------------------------------------------- population and selection

def population(data):
    """Every (talent, looks) combination once -- independence by construction."""
    return [(p["talent"], p["looks"]) for p in data["people"]]


def cast(data):
    """The selected subset: talent + looks >= threshold. Selection depends on BOTH traits."""
    t = data["threshold"]
    return [(x, y) for x, y in population(data) if x + y >= t]


# ----------------------------------------------------------------- printing

def population_view(data):
    everyone = population(data)
    chosen = cast(data)
    t = data["threshold"]
    print("POPULATION — the full talent x looks grid; * marks who gets cast (talent+looks >= %d)" % t)
    print("-" * 54)
    print("        looks 1   2   3   4   5")
    for tal in range(5, 0, -1):
        row = "  talent %d " % tal
        for look in range(1, 6):
            row += "  %s " % ("*" if tal + look >= t else ".")
        print(row)
    print("-" * 54)
    print("  everyone: %d people;  cast: %d people (%d left out)"
          % (len(everyone), len(chosen), len(everyone) - len(chosen)))


def corr_view(data):
    everyone = population(data)
    chosen = cast(data)
    print("CORR — talent-looks correlation over everyone vs over the cast only")
    print("-" * 60)
    print("  whole population (%2d people): r = %+.4f" % (len(everyone), pearson(everyone)))
    print("  cast subset      (%2d people): r = %+.4f" % (len(chosen), pearson(chosen)))
    print("-" * 60)
    print("  independent in the world; negatively correlated once you condition on being cast.")


def check(data):
    print("SELF-TEST — the population correlation is ~0; selecting on the collider makes it negative")
    print("-" * 74)
    everyone = population(data)
    chosen = cast(data)

    r_all = pearson(everyone)
    independent = abs(r_all) < 1e-9
    print("  talent and looks are independent in the population = %s (r = %+.4f)" % (independent, r_all))

    r_cast = pearson(chosen)
    spurious_negative = r_cast < -0.2
    print("  within the cast they are negatively correlated = %s (r = %+.4f)" % (spurious_negative, r_cast))

    # selection depends on both traits -- that is what makes it a collider
    t = data["threshold"]
    depends_on_both = any(x + y < t for x, y in everyone) and any(x + y >= t for x, y in everyone)
    print("  casting depends on both traits (a common effect) = %s (threshold %d)" % (depends_on_both, t))

    # the illusion is created by selection, not present before it
    illusion_from_selection = independent and spurious_negative
    print("  the correlation appears only after conditioning on the collider = %s" % illusion_from_selection)

    ok = independent and spurious_negative and depends_on_both and illusion_from_selection
    print("-" * 74)
    print("SELF-TEST %s  independent=%s  spurious_negative=%s  depends_on_both=%s  illusion_from_selection=%s"
          % ("PASS" if ok else "FAIL", independent, spurious_negative, depends_on_both, illusion_from_selection))
    return ok


def main():
    p = argparse.ArgumentParser(description="Berkson's paradox: conditioning on a common effect fakes a correlation.")
    p.add_argument("--population", action="store_true")
    p.add_argument("--corr", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("people=%d  threshold=%d  file=%s  (the population grid is a fixture)"
          % (len(data["people"]), data["threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.population:
        population_view(data)
    elif args.corr:
        corr_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
