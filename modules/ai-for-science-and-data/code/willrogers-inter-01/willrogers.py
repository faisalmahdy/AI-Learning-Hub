"""Check the overall average, not just the group averages -- reclassifying a borderline case can raise both groups' means while nothing improved.

Two groups, ranked -- early-stage patients and late-stage patients, weak schools and strong schools, low-risk and high-risk accounts -- and you track the average outcome in each. Then the boundary between the groups moves: a better scanner reclassifies some borderline patients, a new rule shifts some schools between tiers, a model re-scores some accounts. Afterward BOTH groups show a better average, and it is tempting to declare progress. But you can get exactly that result with no one's outcome changing at all -- purely by moving a case from one group to the other. This is the Will Rogers phenomenon, named for the quip that when the Okies left Oklahoma for California they raised the average intelligence of both states.

The mechanism is a fact about averages, not about the world. Take a case that sits BELOW its current group's average but ABOVE the other group's average. Remove it from the first group and the first group's average goes UP (you dropped a below-average member). Add it to the second group and the second group's average also goes UP (you added an above-average member). One move, both means rise, and the case itself is completely unchanged -- same survival, same score, same value, just a different label. In medicine this is 'stage migration': more sensitive imaging finds tiny metastases in patients who would have been called early-stage, so they are relabeled late-stage; the early-stage group loses its sickest members (its average survival rises) and the late-stage group gains its healthiest members (its average survival rises too), while not one patient lives a day longer.

The tell is the OVERALL average -- the mean across everyone, ignoring the grouping. Because no value changed, only labels, the overall average is exactly the same before and after. A real improvement raises the overall average; a Will Rogers artifact leaves it untouched while both subgroup averages climb. So the way to not be fooled is to always compute the pooled, ungrouped average alongside the per-group ones: if the subgroups improved but the whole did not, the 'improvement' is reclassification, not progress.

The rule: when comparing group averages across a change that could move cases between the groups (a reclassification, a new threshold, a better test), check the OVERALL ungrouped average too, because moving a case that is below its old group's mean and above its new group's mean raises both group means with no change to any individual -- so improved subgroup averages can be pure stage-migration artifact, which the unchanged overall average exposes.

On this fixture a borderline patient (survival 5) is reclassified from localized (mean 6) to advanced (mean 2). Localized rises to 6.5 and advanced rises to 2.75 -- both up -- while the overall average stays 4.0, because no patient's survival changed. This computes both.

  --groups    the group survival times and means before and after the reclassification, and the overall mean each time
  --move      why the single moved case raises both means: it is below its old group's mean and above its new group's mean
  --check     both group means rise while the overall mean is unchanged -- the improvement is reclassification, not real

groups and reclassify are the fixture; every mean and the move conditions are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "willrogers.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(vals):
    return sum(vals) / len(vals)


def apply_move(groups, move):
    """Return new groups with the reclassified value moved from one group to the other (value unchanged)."""
    after = {k: list(v) for k, v in groups.items()}
    after[move["from"]].remove(move["value"])
    after[move["to"]].append(move["value"])
    return after


def overall(groups):
    """The pooled mean across every case, ignoring the grouping."""
    allvals = [v for g in groups.values() for v in g]
    return mean(allvals)


# ----------------------------------------------------------------- printing

def groups_view(data):
    groups, move = data["groups"], data["reclassify"]
    after = apply_move(groups, move)
    print("GROUPS — survival means before and after reclassifying a %s=%d from %s to %s"
          % (data["metric"], move["value"], move["from"], move["to"]))
    print("-" * 70)
    print("  before: %s mean %.2f ; %s mean %.2f ; OVERALL %.2f"
          % (move["from"], mean(groups[move["from"]]), move["to"], mean(groups[move["to"]]), overall(groups)))
    print("          %s=%s  %s=%s" % (move["from"], groups[move["from"]], move["to"], groups[move["to"]]))
    print("  after : %s mean %.2f ; %s mean %.2f ; OVERALL %.2f"
          % (move["from"], mean(after[move["from"]]), move["to"], mean(after[move["to"]]), overall(after)))
    print("          %s=%s  %s=%s" % (move["from"], after[move["from"]], move["to"], after[move["to"]]))
    print("-" * 70)
    print("  both group means rose; overall mean unchanged (%.2f -> %.2f)" % (overall(groups), overall(after)))


def move_view(data):
    groups, move = data["groups"], data["reclassify"]
    v = move["value"]
    print("MOVE — why one reclassified case raises both group means")
    print("-" * 60)
    print("  moved case: %s = %d, from %s to %s" % (data["metric"], v, move["from"], move["to"]))
    print("  it is BELOW its old group's mean: %d < %.2f (%s)" % (v, mean(groups[move["from"]]), move["from"]))
    print("  it is ABOVE its new group's mean: %d > %.2f (%s)" % (v, mean(groups[move["to"]]), move["to"]))
    print("-" * 60)
    print("  removing a below-average member raises the old group's mean;")
    print("  adding an above-average member raises the new group's mean.")


def check(data):
    print("SELF-TEST — both group means rise while the overall mean is unchanged -- the improvement is reclassification, not real")
    print("-" * 120)
    groups, move = data["groups"], data["reclassify"]
    after = apply_move(groups, move)
    fr, to = move["from"], move["to"]
    v = move["value"]

    from_mean_rises = mean(after[fr]) > mean(groups[fr])
    print("  the %s group mean rises = %s (%.2f -> %.2f)" % (fr, from_mean_rises, mean(groups[fr]), mean(after[fr])))

    to_mean_rises = mean(after[to]) > mean(groups[to])
    print("  the %s group mean rises = %s (%.2f -> %.2f)" % (to, to_mean_rises, mean(groups[to]), mean(after[to])))

    overall_unchanged = abs(overall(after) - overall(groups)) < 1e-9
    print("  the overall (ungrouped) mean is unchanged = %s (%.2f == %.2f)" % (overall_unchanged, overall(groups), overall(after)))

    below_old = v < mean(groups[fr])
    print("  the moved case is below its old group's mean = %s (%d < %.2f)" % (below_old, v, mean(groups[fr])))

    above_new = v > mean(groups[to])
    print("  the moved case is above its new group's mean = %s (%d > %.2f)" % (above_new, v, mean(groups[to])))

    no_value_changed = sorted(v for g in after.values() for v in g) == sorted(v for g in groups.values() for v in g)
    print("  no individual's value changed (only the label) = %s" % no_value_changed)

    ok = from_mean_rises and to_mean_rises and overall_unchanged and below_old and above_new and no_value_changed
    print("-" * 120)
    print("SELF-TEST %s  from_mean_rises=%s  to_mean_rises=%s  overall_unchanged=%s  below_old=%s  above_new=%s  no_value_changed=%s"
          % ("PASS" if ok else "FAIL", from_mean_rises, to_mean_rises, overall_unchanged, below_old, above_new, no_value_changed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Will Rogers phenomenon: when comparing group averages across a change that could move cases between the groups (a reclassification, a new threshold, a better test), check the OVERALL ungrouped average too, because moving a case that is below its old group's mean and above its new group's mean raises both group means with no change to any individual -- so improved subgroup averages can be pure stage-migration artifact, which the unchanged overall average exposes.")
    p.add_argument("--groups", action="store_true")
    p.add_argument("--move", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("metric=%s  groups=%s  reclassify=%s  file=%s  (the groups and the move are a fixture)"
          % (data["metric"], {k: len(v) for k, v in data["groups"].items()}, data["reclassify"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.groups:
        groups_view(data)
    elif args.move:
        move_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
