"""Average a model comparison over a set of prompt templates, not off a single one -- a model's score is sensitive to trivial prompt formatting, and two models are sensitive differently, so which template you happen to pick can decide the winner even when every comparison is individually fair.

A companion rule says both models must run under the same prompt template for a fair head-to-head -- change the template between them and you are measuring the setup, not the model. That is necessary and it is not the end of the story. The single template you chose, fair as it is, is one arbitrary draw from the space of ways to phrase the task, and models do not score the same across that space. Option ordering, the exact instruction wording, whitespace, whether the answer is asked for as 'Answer:' or 'The answer is' -- these formatting choices move scores by several points, and they move different models by different amounts.

So a fair single-template comparison can still be an artifact of the template. Under one wording model A looks better; under another, equally reasonable wording, model B looks better -- both comparisons fair, opposite conclusions. If you report the one template you happened to run, you report which template you picked as much as which model is better.

The fix is to treat the template as a nuisance variable and average over it: run the head-to-head under a set of templates and compare the models on their mean scores across the set. The template-to-template swing then shows up as spread, so you can see whether the average gap is real or is smaller than the noise that template choice alone injects. A ranking that survives averaging over templates is about the models; a ranking that flips between templates is about the prompt.

On this fixture the four templates disagree -- t1 favors A, t2 and t4 favor B, t3 ties -- and the swing in the A-minus-B gap across templates is 7 items (out of 20), far larger than the true average gap of 1 item in B's favor. This computes both.

  --templates  each template's fair head-to-head, its winner, and the swing across templates
  --aggregate  the mean score of each model over the templates and the average gap
  --check      the per-template winner flips with the template and the swing dwarfs the mean gap; only the average gives a stable ranking

n_items and the per-template scores are the fixture; the per-template winners, the swing, the means, and the mean gap are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "promptsens.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def gaps(templates):
    """Per-template A-minus-B score gap (in items)."""
    return {name: t["a"] - t["b"] for name, t in templates.items()}


def winner(gap):
    """Who wins one template's fair head-to-head."""
    if gap > 0:
        return "A"
    if gap < 0:
        return "B"
    return "tie"


def mean(xs):
    return sum(xs) / len(xs)


def mean_score(templates, model):
    return mean([t[model] for t in templates.values()])


def swing(templates):
    """The spread of the per-template gap -- how much template choice alone moves the result."""
    gs = list(gaps(templates).values())
    return max(gs) - min(gs)


# ----------------------------------------------------------------- printing

def templates_view(data):
    templates = data["templates"]
    g = gaps(templates)
    print("TEMPLATES — each a fair head-to-head (both models, same template)")
    print("-" * 52)
    print("  template   A    B    gap(A-B)   winner")
    for name, t in templates.items():
        print("  %-9s  %-3d  %-3d  %+-8d   %s" % (name, t["a"], t["b"], g[name], winner(g[name])))
    print("-" * 52)
    print("  the winner is not the same template to template; swing in the gap = %d points" % swing(templates))


def aggregate_view(data):
    templates = data["templates"]
    a_mean = mean_score(templates, "a")
    b_mean = mean_score(templates, "b")
    print("AGGREGATE — mean score across the %d templates" % len(templates))
    print("-" * 52)
    print("  model A mean = %.2f / %d" % (a_mean, data["n_items"]))
    print("  model B mean = %.2f / %d" % (b_mean, data["n_items"]))
    print("  mean gap (A-B) = %+.2f  ->  %s is better on average" % (a_mean - b_mean, "A" if a_mean > b_mean else "B"))
    print("-" * 52)
    print("  averaging over templates gives one stable ranking; a single template does not")


def check(data):
    print("SELF-TEST — the per-template winner flips with the template and the swing dwarfs the mean gap; only the average gives a stable ranking")
    print("-" * 112)
    templates = data["templates"]
    g = gaps(templates)
    winners = [winner(v) for v in g.values()]

    a_mean = mean_score(templates, "a")
    b_mean = mean_score(templates, "b")
    mean_gap = a_mean - b_mean

    both_models_win_some = "A" in winners and "B" in winners
    print("  both models win at least one template = %s (winners %s)" % (both_models_win_some, winners))

    swing_pts = swing(templates)
    swing_exceeds_mean_gap = swing_pts > abs(mean_gap)
    print("  the template swing dwarfs the mean gap = %s (%d vs %.2f)" % (swing_exceeds_mean_gap, swing_pts, abs(mean_gap)))

    average_favors_one = mean_gap != 0
    print("  the average gives a definite ranking = %s (mean gap %+.2f, %s ahead)" % (average_favors_one, mean_gap, "A" if mean_gap > 0 else "B"))

    avg_winner = "A" if mean_gap > 0 else "B"
    a_template_flips_sign = any(winner(v) not in ("tie", avg_winner) for v in g.values())
    print("  at least one template names the opposite winner from the average = %s" % a_template_flips_sign)

    single_template_unreliable = both_models_win_some and swing_exceeds_mean_gap
    print("  a single-template comparison is unreliable here = %s" % single_template_unreliable)

    ok = (both_models_win_some and swing_exceeds_mean_gap and average_favors_one
          and a_template_flips_sign and single_template_unreliable)
    print("-" * 112)
    print("SELF-TEST %s  both_models_win_some=%s  swing_exceeds_mean_gap=%s  average_favors_one=%s  a_template_flips_sign=%s  single_template_unreliable=%s"
          % ("PASS" if ok else "FAIL", both_models_win_some, swing_exceeds_mean_gap, average_favors_one,
             a_template_flips_sign, single_template_unreliable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Prompt-format sensitivity: average a model comparison over a set of prompt templates, not off a single one, because a model's score is sensitive to trivial prompt formatting and two models are sensitive differently, so which fair template you pick can decide the winner.")
    p.add_argument("--templates", action="store_true")
    p.add_argument("--aggregate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_items=%d  templates=%s  file=%s  (these are a fixture)"
          % (data["n_items"], list(data["templates"].keys()), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.templates:
        templates_view(data)
    elif args.aggregate:
        aggregate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
