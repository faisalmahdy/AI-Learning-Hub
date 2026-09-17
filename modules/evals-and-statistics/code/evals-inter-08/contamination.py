"""A leaked test item inflates the score -- and on a head-to-head it can crown a false winner.

An eval is only honest if the system has not seen the answers. When test items leak into a
system's training data, its context, or its memory, it does not solve them, it recalls them, and
it scores near-perfect on exactly those items. Averaged into the aggregate, that memorized
performance inflates the score -- and the danger is sharpest in a comparison, because if one
system was contaminated and its baseline was not, the contaminated system wins the eval on
memorized items alone, while on the clean items where real ability shows they are tied.

Here system A has seen 4 of the 10 test items and system B has not. On the 6 clean items the two
are dead even at 0.60 -- there is no real difference in ability. But A scores a perfect 1.0 on
its 4 contaminated items, so the naive aggregate over all 10 items gives A 0.76 to B's 0.60 and
declares A the clear winner. Score only the clean items and the win vanishes: 0.60 to 0.60, a
tie. The contamination did not just inflate a number, it manufactured a ranking that reverses on
honest data. This computes both the naive and clean-only scores for both systems and shows the
false winner disappear.

  --items      each item's A and B score and whether it is contaminated for A
  --scores     naive (all items) vs clean-only aggregate for each system, and the verdict each gives
  --check      contamination inflates A's naive score and crowns a false winner the clean eval undoes

The per-item scores and the contamination flags are the fixture; every aggregate is computed.
Deterministic; stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "eval.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- aggregates

def mean(xs):
    return sum(xs) / len(xs)


def naive_score(items, system):
    """Average over ALL items -- including the ones the system has already seen."""
    return mean([it[system] for it in items])


def clean_score(items, system):
    """Average over only the items that did NOT leak to the system."""
    clean = [it for it in items if not it["contaminated"]]
    return mean([it[system] for it in clean])


def contaminated_mean(items, system):
    con = [it for it in items if it["contaminated"]]
    return mean([it[system] for it in con]) if con else 0.0


def winner(a, b, eps=1e-9):
    if abs(a - b) < eps:
        return "tie"
    return "A" if a > b else "B"


# ----------------------------------------------------------------- printing

def items_view(data):
    items = data["items"]
    print("ITEMS — per-item scores; contaminated = A has already seen this item")
    print("-" * 52)
    print("  id    A score  B score  contaminated (for A)")
    for it in items:
        print("  %-5s %-8.2f %-8.2f %s" % (it["id"], it["A"], it["B"], it["contaminated"]))
    print("-" * 52)
    print("  A scores a perfect 1.0 on the items it has seen -- recall, not skill.")


def scores_view(data):
    items = data["items"]
    na, nb = naive_score(items, "A"), naive_score(items, "B")
    ca, cb = clean_score(items, "A"), clean_score(items, "B")
    print("SCORES — naive (all items) vs clean-only")
    print("-" * 52)
    print("  naive:      A %.4f   B %.4f   -> winner %s" % (na, nb, winner(na, nb)))
    print("  clean-only: A %.4f   B %.4f   -> winner %s" % (ca, cb, winner(ca, cb)))
    print("-" * 52)
    print("  the naive eval crowns A; the clean eval says tie -- contamination made the winner.")


def check(data):
    print("SELF-TEST — contamination inflates A's naive score and crowns a false winner")
    print("-" * 62)
    items = data["items"]

    a_con = contaminated_mean(items, "A")
    a_clean = clean_score(items, "A")
    inflates = a_con > a_clean
    print("  A scores higher on seen items than on clean ones (recall) = %s (%.2f vs %.2f)"
          % (inflates, a_con, a_clean))

    na, nb = naive_score(items, "A"), naive_score(items, "B")
    naive_says_a = winner(na, nb) == "A"
    print("  the naive eval (all items) declares A the winner = %s (%.4f vs %.4f)" % (naive_says_a, na, nb))

    ca, cb = clean_score(items, "A"), clean_score(items, "B")
    clean_says_tie = winner(ca, cb) == "tie"
    print("  the clean-only eval declares a tie = %s (%.4f vs %.4f)" % (clean_says_tie, ca, cb))

    false_winner = naive_says_a and not (winner(ca, cb) == "A")
    print("  so the naive winner is FALSE -- it reverses on clean data = %s" % false_winner)

    ok = inflates and naive_says_a and clean_says_tie and false_winner
    print("-" * 62)
    print("SELF-TEST %s  inflates=%s  naive_says_a=%s  clean_says_tie=%s  false_winner=%s"
          % ("PASS" if ok else "FAIL", inflates, naive_says_a, clean_says_tie, false_winner))
    return ok


def main():
    p = argparse.ArgumentParser(description="Test-set contamination inflates scores and fakes winners.")
    p.add_argument("--items", action="store_true")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    n_con = sum(1 for it in data["items"] if it["contaminated"])
    print("items=%d  contaminated=%d  file=%s  (per-item scores and flags are a fixture)"
          % (len(data["items"]), n_con, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.items:
        items_view(data)
    elif args.scores:
        scores_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
