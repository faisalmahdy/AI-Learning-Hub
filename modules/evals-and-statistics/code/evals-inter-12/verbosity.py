"""An LLM judge prefers longer answers -- length bias crowns the padded worse answer over the concise better one.

LLM-as-judge scoring has a systematic bias: judges tend to prefer longer, more detailed-looking answers,
somewhat independent of whether the extra length is correct or even relevant. Model the judge as scoring
quality plus a length term, score = quality + beta * length. When beta is zero the judge ranks purely on
quality; when beta is positive the length term can outweigh a real quality difference, so a verbose but
worse answer beats a concise but better one. A model that learns to pad its answers then wins the eval
without being better -- it is gaming the judge's length preference, a form of reward hacking.

The tell is that the judge's winner is systematically the longer answer even when it is the lower-quality
one. Controlling for length -- comparing at equal length, penalizing length, or removing the length term --
makes the bias visible: the ranking flips back to the genuinely better answers. If you evaluate with a
length-biased judge and do not control for it, you will select for verbosity and call it quality.

On this fixture three pairs each have a short answer that is genuinely better (higher quality) and a long
answer that is worse. Under the length-biased judge (beta=0.03) the long, worse answer wins all three.
Under the unbiased judge (beta=0) the short, better answer wins all three. Same answers; only the judge's
length bias differs. This computes both judges' verdicts.

  --pairs      each pair's short (better) and long (worse) answer, with quality and length
  --judge      who each judge picks: length-biased vs unbiased, and whether it is the better answer
  --check      the biased judge picks the longer worse answer every time; removing the bias flips to quality

The qualities, lengths, and beta are the fixture; every judge decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pairs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def judge_score(answer, beta):
    """The judge's score: quality plus a length bias. beta>0 rewards verbosity regardless of quality."""
    return answer["quality"] + beta * answer["length"]


def winner(pair, beta):
    """Which answer the judge prefers under length-bias coefficient beta."""
    s = judge_score(pair["short"], beta)
    l = judge_score(pair["long"], beta)
    return "long" if l > s else "short"


def true_better(pair):
    """The genuinely better answer, by quality alone."""
    return "short" if pair["short"]["quality"] > pair["long"]["quality"] else "long"


# ----------------------------------------------------------------- printing

def pairs_view(data):
    print("PAIRS — a concise better answer vs a verbose worse one")
    print("-" * 58)
    for p in data["pairs"]:
        print("  %s  short: q=%d len=%-3d   long: q=%d len=%-3d   (better: %s)"
              % (p["id"], p["short"]["quality"], p["short"]["length"],
                 p["long"]["quality"], p["long"]["length"], true_better(p)))
    print("-" * 58)
    print("  in every pair the SHORT answer is higher quality; the LONG one is more verbose.")


def judge_view(data):
    beta = data["beta"]
    print("JUDGE — length-biased (beta=%.2f) vs unbiased (beta=0)" % beta)
    print("-" * 62)
    print("  pair   biased pick   correct?   unbiased pick   correct?")
    for p in data["pairs"]:
        b = winner(p, beta)
        u = winner(p, 0)
        print("  %s     %-11s   %-8s   %-13s   %s"
              % (p["id"], b, "yes" if b == true_better(p) else "NO",
                 u, "yes" if u == true_better(p) else "NO"))
    print("-" * 62)
    print("  the biased judge picks the long worse answer; the unbiased judge picks the short better one.")


def check(data):
    print("SELF-TEST — the biased judge picks the longer worse answer every time; removing the bias flips to quality")
    print("-" * 96)
    beta = data["beta"]
    pairs = data["pairs"]

    biased_picks_long = all(winner(p, beta) == "long" for p in pairs)
    print("  the length-biased judge picks the longer answer in every pair = %s" % biased_picks_long)

    biased_picks_worse = all(winner(p, beta) != true_better(p) for p in pairs)
    print("  and that longer answer is the worse one every time = %s" % biased_picks_worse)

    unbiased_picks_better = all(winner(p, 0) == true_better(p) for p in pairs)
    print("  the unbiased judge picks the better answer every time = %s" % unbiased_picks_better)

    removing_bias_flips = all(winner(p, beta) != winner(p, 0) for p in pairs)
    print("  removing the length bias flips every verdict = %s" % removing_bias_flips)

    ok = biased_picks_long and biased_picks_worse and unbiased_picks_better and removing_bias_flips
    print("-" * 96)
    print("SELF-TEST %s  biased_picks_long=%s  biased_picks_worse=%s  unbiased_picks_better=%s  removing_bias_flips=%s"
          % ("PASS" if ok else "FAIL", biased_picks_long, biased_picks_worse, unbiased_picks_better, removing_bias_flips))
    return ok


def main():
    p = argparse.ArgumentParser(description="An LLM judge prefers longer answers -- length bias crowns the padded worse one.")
    p.add_argument("--pairs", action="store_true")
    p.add_argument("--judge", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pairs=%d  beta=%.2f  file=%s  (the qualities and lengths are a fixture)"
          % (len(data["pairs"]), data["beta"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pairs:
        pairs_view(data)
    elif args.judge:
        judge_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
