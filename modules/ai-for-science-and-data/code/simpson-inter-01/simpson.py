"""A treatment can win every subgroup and lose the total -- Simpson's paradox is an allocation artifact, not a contradiction.

A rate is a fraction: recoveries over patients. When you pool two subgroups, the pooled rate is not the average of the two
subgroup rates -- it is their count-weighted average, so the pooled number leans toward whichever subgroup contributed
more patients. That is the whole mechanism behind Simpson's paradox: if the subgroup where a treatment does worse also
happens to be the subgroup where MOST of its patients are, the pooled rate is dragged down toward that worse subgroup,
even while the treatment beats its rival in every subgroup taken alone. Two treatments can each be pooled toward
different subgroups, and the pooled comparison can then point the opposite way from every subgroup comparison. Nothing is
inconsistent; the pooled rates are answering a different question than the subgroup rates, because the two treatments
were not given to comparable patients.

The cause is a confounder: a variable that is associated with BOTH the treatment assignment and the outcome. Here stone
size is the confounder -- large stones recover less often (they affect the outcome), and treatment A was given mostly to
large-stone patients while B was given mostly to small-stone patients (it is associated with the assignment). So A's
overall rate is a report on a harder population, and comparing A's overall rate to B's overall rate compares treatment
tangled with case-mix. The fix is to compare like with like: look within each subgroup, or standardize -- apply each
treatment's per-subgroup rates to one common population mix, so both treatments are scored on the same case-mix and the
confounder is held fixed. Standardized, the comparison agrees with the subgroups.

On this fixture treatment A recovers 81/87 = 93.1% of small stones and 192/263 = 73.0% of large ones; B recovers
234/270 = 86.7% and 55/80 = 68.8%. A beats B in BOTH subgroups. But A treated 263 large stones (the hard cases) against
B's 80, so A's overall rate is 273/350 = 78.0% while B's is 289/350 = 82.6% -- B wins the pooled comparison, reversing
every subgroup. Standardizing both to the combined case-mix puts A back on top, 83.3% vs 77.9%. This computes all of it.

  --rates       each treatment's per-subgroup recovery rates and its overall rate -- A wins both subgroups, B wins overall
  --confound    the allocation that causes it (A got the hard large-stone cases) and the standardized rates that undo it
  --check       treatment A wins each subgroup but loses overall; the allocation is confounded; standardizing restores A

The recovery counts are the fixture; every rate and the standardized comparison are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "simpson.json"

SUBGROUPS = ["small", "large"]


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rate(cell):
    """Recovery rate of one subgroup cell: recovered / total."""
    return cell["recovered"] / cell["total"]


def overall(treatment):
    """Pooled recovery rate: total recoveries over total patients -- the count-weighted mix of the subgroup rates."""
    rec = sum(treatment[g]["recovered"] for g in SUBGROUPS)
    tot = sum(treatment[g]["total"] for g in SUBGROUPS)
    return rec / tot


def combined_mix(treatments):
    """The shared case-mix: total patients per subgroup across both treatments."""
    return {g: sum(treatments[t][g]["total"] for t in treatments) for g in SUBGROUPS}


def standardized(treatment, mix):
    """Apply this treatment's per-subgroup rates to a common population mix -- holds the confounder fixed."""
    total = sum(mix.values())
    return sum(rate(treatment[g]) * mix[g] for g in SUBGROUPS) / total


# ----------------------------------------------------------------- printing

def rates_view(data):
    t = data["treatments"]
    print("RATES — per-subgroup and overall recovery")
    print("-" * 60)
    print("  treatment   small           large           overall")
    for name in ("A", "B"):
        print("  %-10s  %3d/%-3d (%.1f%%)  %3d/%-3d (%.1f%%)  %3d/%-3d (%.1f%%)" % (
            name,
            t[name]["small"]["recovered"], t[name]["small"]["total"], rate(t[name]["small"]) * 100,
            t[name]["large"]["recovered"], t[name]["large"]["total"], rate(t[name]["large"]) * 100,
            sum(t[name][g]["recovered"] for g in SUBGROUPS), sum(t[name][g]["total"] for g in SUBGROUPS), overall(t[name]) * 100))
    print("-" * 60)
    print("  A wins small (%.1f > %.1f) and large (%.1f > %.1f), but B wins overall (%.1f > %.1f)." % (
        rate(t["A"]["small"]) * 100, rate(t["B"]["small"]) * 100,
        rate(t["A"]["large"]) * 100, rate(t["B"]["large"]) * 100,
        overall(t["B"]) * 100, overall(t["A"]) * 100))


def confound_view(data):
    t = data["treatments"]
    print("CONFOUND — the allocation that flips the total, and standardizing that undoes it")
    print("-" * 66)
    print("  large-stone (hard cases) share of each treatment's patients:")
    for name in ("A", "B"):
        tot = sum(t[name][g]["total"] for g in SUBGROUPS)
        print("    %-3s  %3d of %3d = %.0f%% large stones" % (name, t[name]["large"]["total"], tot, t[name]["large"]["total"] / tot * 100))
    mix = combined_mix(data["treatments"])
    print("  common case-mix (both treatments): small=%d, large=%d" % (mix["small"], mix["large"]))
    print("-" * 66)
    print("  standardized to that mix:  A = %.1f%%   B = %.1f%%   -> A wins, agreeing with the subgroups." % (
        standardized(t["A"], mix) * 100, standardized(t["B"], mix) * 100))


def check(data):
    print("SELF-TEST — treatment A wins each subgroup but loses overall; the allocation is confounded; standardizing restores A")
    print("-" * 116)
    t = data["treatments"]

    a_wins_small = rate(t["A"]["small"]) > rate(t["B"]["small"])
    print("  A beats B on small stones = %s (%.1f%% vs %.1f%%)" % (a_wins_small, rate(t["A"]["small"]) * 100, rate(t["B"]["small"]) * 100))

    a_wins_large = rate(t["A"]["large"]) > rate(t["B"]["large"])
    print("  A beats B on large stones = %s (%.1f%% vs %.1f%%)" % (a_wins_large, rate(t["A"]["large"]) * 100, rate(t["B"]["large"]) * 100))

    b_wins_overall = overall(t["B"]) > overall(t["A"])
    print("  yet B beats A overall (the reversal) = %s (%.1f%% vs %.1f%%)" % (b_wins_overall, overall(t["B"]) * 100, overall(t["A"]) * 100))

    a_large_share = t["A"]["large"]["total"] / sum(t["A"][g]["total"] for g in SUBGROUPS)
    b_large_share = t["B"]["large"]["total"] / sum(t["B"][g]["total"] for g in SUBGROUPS)
    allocation_confounded = a_large_share > b_large_share
    print("  A was given far more hard (large-stone) cases = %s (%.0f%% vs %.0f%%)" % (allocation_confounded, a_large_share * 100, b_large_share * 100))

    mix = combined_mix(t)
    standardized_restores_a = standardized(t["A"], mix) > standardized(t["B"], mix)
    print("  standardizing to a common case-mix restores A on top = %s (%.1f%% vs %.1f%%)" % (
        standardized_restores_a, standardized(t["A"], mix) * 100, standardized(t["B"], mix) * 100))

    ok = a_wins_small and a_wins_large and b_wins_overall and allocation_confounded and standardized_restores_a
    print("-" * 116)
    print("SELF-TEST %s  a_wins_small=%s  a_wins_large=%s  b_wins_overall=%s  allocation_confounded=%s  standardized_restores_a=%s"
          % ("PASS" if ok else "FAIL", a_wins_small, a_wins_large, b_wins_overall, allocation_confounded, standardized_restores_a))
    return ok


def main():
    p = argparse.ArgumentParser(description="Simpson's paradox: a pooled rate is the count-weighted average of subgroup rates, so a treatment that wins every subgroup can lose overall when a confounder (here stone size) is allocated unevenly; comparing within subgroups or standardizing to a common case-mix holds the confounder fixed and resolves the reversal.")
    p.add_argument("--rates", action="store_true")
    p.add_argument("--confound", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    t = data["treatments"]
    print("treatments=%s  file=%s  (the recovery counts are a fixture)"
          % ({name: {g: "%d/%d" % (t[name][g]["recovered"], t[name][g]["total"]) for g in SUBGROUPS} for name in t}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rates:
        rates_view(data)
    elif args.confound:
        confound_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
