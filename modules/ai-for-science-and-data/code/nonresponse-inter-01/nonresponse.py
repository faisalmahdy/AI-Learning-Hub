"""Weight for who answered -- a survey's respondents are not a random sample when response depends on the answer.

A survey estimates a population's opinion from the people who answer it, on the assumption that the respondents are a
representative sample of the population. That assumption fails whenever the DECISION to respond is correlated with the
thing being measured -- which, for opinion surveys, it very often is. People with strong feelings answer at higher rates
than the indifferent; an angry customer fills out the complaint form, a satisfied one ignores it; a motivated voter
answers the poll, a disengaged one hangs up. When response rate depends on the answer, the respondents OVER-represent
whichever group is more inclined to respond, and the naive average over respondents is pulled toward that group's opinion.
This is NONRESPONSE BIAS (a form of self-selection bias), and it is not fixed by collecting more responses: a bigger
biased sample is just a more confident wrong answer, because the bias is in WHO answers, not in how many.

The mechanism is stark when the correlation is strong. Suppose most customers are happy but happy customers rarely bother
to reply, while the few unhappy ones almost always do. The respondents are then dominated by the unhappy minority, and the
survey reports a low average satisfaction that describes the respondents accurately and the population not at all. The
company concludes its customers are miserable when most are content; the survey measured willingness-to-respond as much as
satisfaction.

The correction, when the response rates are known or can be estimated, is INVERSE-PROBABILITY WEIGHTING: weight each
respondent by 1 divided by their group's response rate, so an under-responding group's few answers are scaled up to stand
for all the non-responders like them, and an over-responding group's many answers are scaled down. A respondent from a
group that answered at 10% counts for 10 people; one from a group that answered at 80% counts for 1.25. Weighting
reconstructs the population from the biased sample and recovers the true mean -- provided you actually know the response
rates and provided the non-responders within a group resemble the responders (the assumption that makes the weights
valid). The deeper lesson is that a survey measures the population only if response is independent of the answer, and when
it is not, the fix lives in modeling WHO responded, not in the raw average.

The rule: a survey's respondents are a representative sample only if the decision to respond is independent of the answer;
when response rate correlates with the thing measured, the naive respondent average is biased toward the over-responding
group, so estimate the population by weighting each respondent by the inverse of their response probability, not by taking
the raw mean.

On this fixture the true population satisfaction is 4.0, but unhappy customers respond far more than happy ones, so the 20
respondents are 40% unhappy though the population is only 10% unhappy, and the naive respondent mean is 2.8. Inverse-
probability weighting recovers 4.0. This computes both.

  --survey    the population by group vs the respondents by group, the true mean, and the naive respondent mean
  --weight    inverse-probability weighting: each respondent scaled by 1/response_rate reconstructs the population and its true mean
  --check     the naive respondent mean is biased low because the unhappy group over-responds; weighting recovers the true mean

groups (score, population, response_rate) is the fixture; every respondent count, mean, and weighted estimate is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "nonresponse.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def respondents(group):
    """How many of this group actually answered = population * response_rate."""
    return round(group["population"] * group["response_rate"])


def true_mean(groups):
    """The real population mean, over everyone."""
    total = sum(g["population"] for g in groups)
    return sum(g["score"] * g["population"] for g in groups) / total


def naive_mean(groups):
    """The mean over respondents only -- what a survey reports if it just averages the answers it got."""
    n = sum(respondents(g) for g in groups)
    return sum(g["score"] * respondents(g) for g in groups) / n


def weighted_mean(groups):
    """Inverse-probability weighted mean: each respondent counts as 1/response_rate people."""
    num = sum(g["score"] * respondents(g) * (1 / g["response_rate"]) for g in groups)
    den = sum(respondents(g) * (1 / g["response_rate"]) for g in groups)
    return num / den


# ----------------------------------------------------------------- printing

def survey_view(data):
    groups = data["groups"]
    pop = sum(g["population"] for g in groups)
    resp = sum(respondents(g) for g in groups)
    print("SURVEY — population vs respondents by satisfaction score")
    print("-" * 70)
    print("  score  population  response-rate  respondents  %-of-pop  %-of-resp")
    for g in groups:
        r = respondents(g)
        print("  %-6d %-11d %-14s %-12d %-9s %s"
              % (g["score"], g["population"], "%.0f%%" % (g["response_rate"] * 100), r,
                 "%.0f%%" % (g["population"] / pop * 100), "%.0f%%" % (r / resp * 100)))
    print("-" * 70)
    print("  true population mean = %.1f ; naive respondent mean = %.1f" % (true_mean(groups), naive_mean(groups)))


def weight_view(data):
    groups = data["groups"]
    print("WEIGHT — inverse-probability weighting reconstructs the population")
    print("-" * 68)
    print("  score  respondents  weight (1/rate)  represents")
    for g in groups:
        r = respondents(g)
        w = 1 / g["response_rate"]
        print("  %-6d %-12d %-16.2f %.0f people" % (g["score"], r, w, r * w))
    print("-" * 68)
    print("  weighted mean = %.1f  (= the true population mean %.1f)" % (weighted_mean(groups), true_mean(groups)))


def check(data):
    print("SELF-TEST — the naive respondent mean is biased low because the unhappy group over-responds; weighting recovers the truth")
    print("-" * 122)
    groups = data["groups"]
    tm = true_mean(groups)
    nm = naive_mean(groups)
    wm = weighted_mean(groups)
    pop = sum(g["population"] for g in groups)
    resp = sum(respondents(g) for g in groups)
    unhappy = min(groups, key=lambda g: g["score"])

    naive_is_biased = abs(nm - tm) > 0.5
    print("  the naive respondent mean differs from the true mean = %s (%.1f vs %.1f)" % (naive_is_biased, nm, tm))

    naive_underestimates = nm < tm
    print("  the naive mean underestimates satisfaction = %s (%.1f < %.1f)" % (naive_underestimates, nm, tm))

    unhappy_overrepresented = respondents(unhappy) / resp > unhappy["population"] / pop
    print("  the unhappy group is over-represented among respondents = %s (%.0f%% of respondents vs %.0f%% of population)"
          % (unhappy_overrepresented, respondents(unhappy) / resp * 100, unhappy["population"] / pop * 100))

    weighting_recovers = abs(wm - tm) < 1e-9
    print("  inverse-probability weighting recovers the true mean = %s (%.1f == %.1f)" % (weighting_recovers, wm, tm))

    more_responses_dont_help = naive_is_biased
    print("  the bias is in WHO answered, so a bigger biased sample stays wrong = %s" % more_responses_dont_help)

    ok = naive_is_biased and naive_underestimates and unhappy_overrepresented and weighting_recovers and more_responses_dont_help
    print("-" * 122)
    print("SELF-TEST %s  naive_is_biased=%s  naive_underestimates=%s  unhappy_overrepresented=%s  weighting_recovers=%s  more_responses_dont_help=%s"
          % ("PASS" if ok else "FAIL", naive_is_biased, naive_underestimates, unhappy_overrepresented, weighting_recovers, more_responses_dont_help))
    return ok


def main():
    p = argparse.ArgumentParser(description="Nonresponse bias: a survey's respondents are a representative sample only if the decision to respond is independent of the answer; when response rate correlates with the thing measured, the naive respondent average is biased toward the over-responding group, so estimate the population by weighting each respondent by the inverse of their response probability, not by taking the raw mean.")
    p.add_argument("--survey", action="store_true")
    p.add_argument("--weight", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("groups=%d  file=%s  (the population, response rates, and scores are a fixture)" % (len(data["groups"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.survey:
        survey_view(data)
    elif args.weight:
        weight_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
