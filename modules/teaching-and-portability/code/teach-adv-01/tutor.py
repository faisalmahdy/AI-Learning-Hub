#!/usr/bin/env python3
"""An adaptive tutor composing the whole teaching track into one next-step decision.

The teaching modules each answered a slice of "what should this learner do next": the
prerequisite frontier (what can they absorb), calibration (study what they failed, not
what feels weak), and expertise reversal (how much scaffolding to give). This composes all
three into one tutor and measures it against the naive alternative, because a good
recommendation must satisfy every constraint at once -- a concept that is unlocked but
already known is a waste, one that is failed but locked is a bounce, and the right concept
at the wrong scaffolding is still mistaught.

The composed tutor recommends concepts that are UNLOCKED (prerequisites mastered) AND
actually FAILED on the last recall, delivered at scaffolding FADED to competence. The naive
tutor sorts by self-rated confidence (studying what feels weakest), ignores prerequisites,
and gives everyone full scaffolding -- so it recommends locked concepts the learner bounces
off, wastes slots on concepts they already recall, and misses the overconfident-but-failed
concepts that are the real gaps. This measures both against a "good recommendation" that
holds all three constraints.

  --state       each concept's status: mastered, unlocked, failed, and its faded scaffold level
  --recommend   the composed tutor's picks vs the naive (confidence-sorted) tutor's
  --check       the composed tutor's picks are all good; the naive tutor's are not

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "state.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the three signals

def mastered_set(concepts):
    return {c for c, s in concepts.items() if s["mastered"]}


def unlocked(concept_id, concepts):
    """Frontier: prerequisites all mastered, and not itself mastered."""
    s = concepts[concept_id]
    mastered = mastered_set(concepts)
    return (not s["mastered"]) and all(p in mastered for p in s["prereqs"])


def needs_study(concept_id, concepts):
    """Calibration: study what the last RECALL failed -- not what confidence feels weak."""
    return concepts[concept_id]["recalled"] == 0


def faded_scaffold(concept_id, concepts, reversal):
    """Expertise reversal: full scaffolding below the reversal competence, none above."""
    return 1.0 if concepts[concept_id]["competence"] < reversal else 0.0


# ------------------------------------------------------------- a good recommendation

def is_good(concept_id, concepts):
    """A recommendation is good only if the concept is unlocked AND actually failed."""
    return unlocked(concept_id, concepts) and needs_study(concept_id, concepts)


# ------------------------------------------------------------- the two tutors

def recommend_composed(concepts, reversal, budget):
    """Unlocked AND failed, each at scaffolding faded to competence."""
    picks = [c for c in concepts if unlocked(c, concepts) and needs_study(c, concepts)]
    picks.sort()
    return [(c, faded_scaffold(c, concepts, reversal)) for c in picks[:budget]]


def recommend_naive(concepts, reversal, budget):
    """The bug: lowest self-rated confidence first, ignore prereqs, full scaffolding for all."""
    cand = sorted((c for c in concepts if not concepts[c]["mastered"]),
                  key=lambda c: (concepts[c]["confidence"], c))
    return [(c, 1.0) for c in cand[:budget]]


# ----------------------------------------------------------------- printing

def state_view(data):
    cs, rev = data["concepts"], data["reversal"]
    print("STATE — each concept's signals (reversal competence %.2f)" % rev)
    print("-" * 66)
    print("  concept    mastered unlocked failed conf  comp  scaffold")
    for c in cs:
        print("  %-10s %-8s %-8s %-6s %.2f  %.2f  %s"
              % (c, cs[c]["mastered"], unlocked(c, cs), needs_study(c, cs) and not cs[c]["mastered"],
                 cs[c]["confidence"], cs[c]["competence"],
                 "%.0f" % faded_scaffold(c, cs, rev) if unlocked(c, cs) else "-"))
    print("-" * 66)
    print("  a good next step is unlocked AND failed; scaffold fades past the reversal competence.")


def recommend_view(data):
    cs, rev, b = data["concepts"], data["reversal"], data["budget"]
    comp = recommend_composed(cs, rev, b)
    nai = recommend_naive(cs, rev, b)
    print("RECOMMEND — composed tutor vs naive (confidence-sorted), budget %d" % b)
    print("-" * 66)
    print("  composed: %s" % [(c, "full" if s == 1.0 else "none") for c, s in comp])
    for c, _ in comp:
        print("     %-10s unlocked=%s failed=%s  -> good" % (c, unlocked(c, cs), needs_study(c, cs)))
    print("  naive:    %s" % [c for c, _ in nai])
    for c, _ in nai:
        why = "LOCKED (bounce)" if not unlocked(c, cs) else ("already recalled (waste)" if not needs_study(c, cs) else "ok")
        print("     %-10s %s" % (c, why))
    print("-" * 66)
    print("  the naive tutor picks by feeling: a locked concept and one already known.")


def check(data):
    print("SELF-TEST — the composed tutor's picks are all good; the naive tutor's are not")
    print("-" * 66)
    cs, rev, b = data["concepts"], data["reversal"], data["budget"]

    comp = recommend_composed(cs, rev, b)
    nai = recommend_naive(cs, rev, b)

    comp_good = all(is_good(c, cs) for c, _ in comp) and len(comp) > 0
    print("  every composed recommendation is unlocked AND failed = %s (%s)" % (comp_good, [c for c, _ in comp]))

    scaffold_faded = dict(comp).get("vectors") == 1.0 and dict(comp).get("calculus") == 0.0
    print("  scaffolding is faded to competence = %s (vectors full, calculus none)" % scaffold_faded)

    naive_locked = any(not unlocked(c, cs) for c, _ in nai)
    print("  naive recommends a LOCKED concept (a bounce) = %s (%s)"
          % (naive_locked, [c for c, _ in nai if not unlocked(c, cs)]))

    naive_waste = any(not needs_study(c, cs) for c, _ in nai)
    print("  naive recommends an already-recalled concept (a waste) = %s (%s)"
          % (naive_waste, [c for c, _ in nai if not needs_study(c, cs)]))

    comp_n = sum(is_good(c, cs) for c, _ in comp)
    naive_n = sum(is_good(c, cs) for c, _ in nai)
    composed_wins = comp_n > naive_n
    print("  composed makes more good recommendations = %s (%d vs %d)" % (composed_wins, comp_n, naive_n))

    ok = comp_good and scaffold_faded and naive_locked and naive_waste and composed_wins
    print("-" * 66)
    print("SELF-TEST %s  comp_good=%s  scaffold_faded=%s  naive_locked=%s  naive_waste=%s  composed_wins=%s"
          % ("PASS" if ok else "FAIL", comp_good, scaffold_faded, naive_locked, naive_waste, composed_wins))
    return ok


def main():
    p = argparse.ArgumentParser(description="An adaptive tutor composing frontier, calibration, and scaffolding.")
    p.add_argument("--state", action="store_true")
    p.add_argument("--recommend", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("concepts=%d  reversal=%.2f  budget=%d  file=%s  (learner state is a fixture)"
          % (len(data["concepts"]), data["reversal"], data["budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.state:
        state_view(data)
    elif args.recommend:
        recommend_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
