"""Aggregate a per-item eval comparison with a robust statistic, not the mean -- the mean of a continuous per-item score gives a single anomalous item unbounded leverage, so one outlier flips which system wins the leaderboard even though the other system is better on almost every item, while the median, a trimmed mean, or the paired per-item win rate all report the robust verdict.

An eval that scores each item on a continuous scale -- an LLM-judge quality score, a graded rubric total, a latency -- has to collapse the per-item scores into one number per system to rank them. The reflex is the mean. The mean is a fine descriptive summary and a terrible comparison aggregate, because it has a breakdown point of zero: a single item, pushed far enough, moves the mean as far as you like. In an eval that single item can be a judge glitch, a mis-scaled grade, one freak easy case -- and it should not decide the leaderboard.

On this fixture system B scores a little above system A on nine of ten items. On the tenth, A has an outlier score of 200. That one item drags A's mean above B's, so a leaderboard ranked by mean crowns A -- the system that lost nine of ten items. Every robust summary disagrees: B wins on the median, B wins on a trimmed mean that drops the extremes, and B wins the paired head-to-head 9 to 1. Drop the single outlier item and even the mean flips back to B, which is the tell that one point was driving the whole verdict.

The fix is to aggregate a comparison with a statistic that a lone item cannot capture: the median, a trimmed mean, or the paired per-item win rate. This is not the descriptive point that a mean can be unrepresentative of a skewed distribution; it is that a non-robust aggregate lets one item flip a decision between two systems, which a comparison metric must never do.

  --aggregate  each system's mean, median, and trimmed mean, and which system each picks
  --items      the per-item head-to-head, and how dropping the single outlier item changes the mean verdict
  --check      the mean picks A while the median, the trimmed mean, and the item majority all pick B, and removing the one outlier item flips the mean back to B

each item's two scores and the trim fraction are the fixture; every aggregate, win count, and the drop-one-item mean are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "trimmean.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    """The arithmetic mean -- breakdown point zero, so one item has unbounded leverage."""
    return sum(xs) / len(xs)


def median(xs):
    """The middle value (or mean of the two middle) -- unmoved by how extreme the tails are."""
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def trimmed_mean(xs, trim_frac):
    """The mean after dropping the top and bottom trim_frac of the values -- discards the extremes."""
    s = sorted(xs)
    k = int(len(s) * trim_frac)
    kept = s[k:len(s) - k]
    return sum(kept) / len(kept)


def item_wins(items):
    """How many items each system scores strictly higher on -- the paired head-to-head."""
    a = sum(1 for it in items if it["A"] > it["B"])
    b = sum(1 for it in items if it["B"] > it["A"])
    return a, b


def winner(a_val, b_val):
    return "A" if a_val > b_val else ("B" if b_val > a_val else "tie")


# ----------------------------------------------------------------- printing

def _cols(items):
    return [it["A"] for it in items], [it["B"] for it in items]


def aggregate_view(data):
    A, B = _cols(data["items"])
    tf = data["trim_frac"]
    print("AGGREGATE — each system's score under three aggregates")
    print("-" * 64)
    print("  mean:         A = %6.2f   B = %6.2f   -> picks %s" % (mean(A), mean(B), winner(mean(A), mean(B))))
    print("  median:       A = %6.2f   B = %6.2f   -> picks %s" % (median(A), median(B), winner(median(A), median(B))))
    print("  trimmed %.0f%%:  A = %6.2f   B = %6.2f   -> picks %s" % (tf * 100, trimmed_mean(A, tf), trimmed_mean(B, tf), winner(trimmed_mean(A, tf), trimmed_mean(B, tf))))
    print("-" * 64)
    print("  the mean alone crowns A; every robust aggregate crowns B")


def items_view(data):
    items = data["items"]
    a_wins, b_wins = item_wins(items)
    print("ITEMS — per-item head-to-head (B better on almost every item)")
    print("-" * 64)
    for it in items:
        w = winner(it["A"], it["B"])
        print("  %-4s A=%3d  B=%3d  -> %s%s" % (it["id"], it["A"], it["B"], w, "   <- A's outlier" if it["A"] > 150 else ""))
    A, B = _cols(items)
    # drop the single item where A is most extreme
    out = max(range(len(items)), key=lambda i: items[i]["A"])
    A2 = [items[i]["A"] for i in range(len(items)) if i != out]
    B2 = [items[i]["B"] for i in range(len(items)) if i != out]
    print("-" * 64)
    print("  item wins: A %d, B %d" % (a_wins, b_wins))
    print("  mean with all items:        A = %.2f  B = %.2f  -> %s" % (mean(A), mean(B), winner(mean(A), mean(B))))
    print("  mean dropping %s (A's outlier): A = %.2f  B = %.2f  -> %s" % (items[out]["id"], mean(A2), mean(B2), winner(mean(A2), mean(B2))))


def check(data):
    print("SELF-TEST — the mean picks A while the median, the trimmed mean, and the item majority all pick B, and removing the one outlier item flips the mean back to B")
    print("-" * 112)
    items = data["items"]
    A, B = _cols(items)
    tf = data["trim_frac"]

    mean_picks_a = winner(mean(A), mean(B)) == "A"
    print("  the mean picks A = %s (%.2f vs %.2f)" % (mean_picks_a, mean(A), mean(B)))

    median_picks_b = winner(median(A), median(B)) == "B"
    print("  the median picks B = %s (%.2f vs %.2f)" % (median_picks_b, median(A), median(B)))

    trimmed_picks_b = winner(trimmed_mean(A, tf), trimmed_mean(B, tf)) == "B"
    print("  the trimmed mean picks B = %s (%.2f vs %.2f)" % (trimmed_picks_b, trimmed_mean(A, tf), trimmed_mean(B, tf)))

    a_wins, b_wins = item_wins(items)
    item_majority_b = b_wins > a_wins
    print("  the item-by-item majority favors B = %s (B %d, A %d)" % (item_majority_b, b_wins, a_wins))

    out = max(range(len(items)), key=lambda i: items[i]["A"])
    A2 = [items[i]["A"] for i in range(len(items)) if i != out]
    B2 = [items[i]["B"] for i in range(len(items)) if i != out]
    drop_flips_mean = winner(mean(A2), mean(B2)) == "B"
    print("  removing the single outlier item flips the mean to B = %s (%.2f vs %.2f)" % (drop_flips_mean, mean(A2), mean(B2)))

    ok = (mean_picks_a and median_picks_b and trimmed_picks_b and item_majority_b and drop_flips_mean)
    print("-" * 112)
    print("SELF-TEST %s  mean_picks_a=%s  median_picks_b=%s  trimmed_picks_b=%s  item_majority_b=%s  drop_flips_mean=%s"
          % ("PASS" if ok else "FAIL", mean_picks_a, median_picks_b, trimmed_picks_b, item_majority_b, drop_flips_mean))
    return ok


def main():
    p = argparse.ArgumentParser(description="Robust eval aggregation: rank two systems by the median, a trimmed mean, or the paired per-item win rate rather than the mean of a continuous per-item score, because the mean has a breakdown point of zero -- one anomalous item has unbounded leverage and can flip which system wins the leaderboard even when the other is better on almost every item, while robust aggregates report the verdict the item-level majority supports.")
    p.add_argument("--aggregate", action="store_true")
    p.add_argument("--items", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%d  trim_frac=%.2f  file=%s" % (len(data["items"]), data["trim_frac"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.aggregate:
        aggregate_view(data)
    elif args.items:
        items_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
