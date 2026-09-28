"""Hold the harness config fixed when comparing two models -- if they run under different generation configs the measured gap is model plus config, and a real winner can be erased by a stingy output cap.

A model comparison is supposed to isolate one variable: the model. Everything else in the harness -- the prompt template, the decoding temperature, the maximum output length -- has to be identical for both, or the comparison stops measuring the model and starts measuring the difference in setup. This is the eval version of a controlled experiment: change one thing at a time, or you cannot attribute the result.

The output-length cap is the sneakiest of these to get wrong, because it does not corrupt an answer visibly -- it truncates it. A model that knew the answer but was cut off mid-response scores exactly like a model that did not know it. So if model B runs with a smaller max_tokens than model A, every item whose correct answer is longer than B's cap is scored against B as a failure, even on items B would have aced under A's cap. Those lost points are a property of the config, not the model.

Run the comparison that way and the arithmetic is merciless: the reported gap is the true model gap plus the config penalty, with opposite signs when the throttled model is the better one. A model that is genuinely better can be dragged down to a tie, or below, by nothing but a lower token cap. The eval reports 'no difference' and the better model loses the bake-off for a reason that has nothing to do with quality.

The rule: hold every harness setting except the model identical across a comparison -- prompt, temperature, and especially the output-length cap -- because a config difference confounds the model gap, and a stingy cap on one side can truncate correct answers and erase a real winner.

On this fixture model B is genuinely better than A (it solves one harder item by skill). Under a matched config B wins by that item; under an unfair config that throttles B's max_tokens, that same item is truncated and lost, and the comparison reports a tie. This computes both.

  --scores     each model's score under the matched config and the unfair config, with the winner
  --attribute  which items the throttled model loses, split into lost-to-skill vs lost-to-truncation
  --check      a matched config shows B's true win; an unfair token cap truncates a correct answer and erases it

items, skills, and the two configs are the fixture; the scores, winners, and truncation losses are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "configparity.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def solved(item, skill, max_tokens):
    """An item is scored correct only if skill meets the difficulty AND the cap fits the answer."""
    return skill >= item["difficulty"] and max_tokens >= item["tokens_needed"]


def score(items, skill, max_tokens):
    return sum(solved(it, skill, max_tokens) for it in items)


def truncated_wins(items, skill, max_tokens):
    """Items the model would solve by skill but loses only because the cap truncates the answer."""
    return [it["id"] for it in items
            if skill >= it["difficulty"] and max_tokens < it["tokens_needed"]]


# ----------------------------------------------------------------- printing

def scores_view(data):
    items, sa, sb = data["items"], data["skill_a"], data["skill_b"]
    m, u = data["matched_config"], data["unfair_config"]
    print("SCORES — each model under the matched config vs the unfair config")
    print("-" * 62)
    print("  config     max_a  max_b   score_a  score_b   winner")
    for name, c in (("matched", m), ("unfair", u)):
        a = score(items, sa, c["max_tokens_a"])
        b = score(items, sb, c["max_tokens_b"])
        win = "A" if a > b else ("B" if b > a else "tie")
        print("  %-9s  %-5d  %-5d   %-7d  %-7d   %s"
              % (name, c["max_tokens_a"], c["max_tokens_b"], a, b, win))
    print("-" * 62)
    print("  same models, same items -- only the token cap changed, and the winner changed with it")


def attribute_view(data):
    items, sb = data["items"], data["skill_b"]
    u = data["unfair_config"]
    lost_trunc = truncated_wins(items, sb, u["max_tokens_b"])
    lost_skill = [it["id"] for it in items if sb < it["difficulty"]]
    print("ATTRIBUTE — why model B loses each item under the unfair config (cap %d)" % u["max_tokens_b"])
    print("-" * 60)
    print("  id    difficulty  tokens_needed  skill_ok  cap_ok  lost_to")
    for it in items:
        skill_ok = sb >= it["difficulty"]
        cap_ok = u["max_tokens_b"] >= it["tokens_needed"]
        reason = "-" if (skill_ok and cap_ok) else ("truncation" if skill_ok else "skill")
        print("  %-4s  %-10d  %-13d  %-8s  %-6s  %s"
              % (it["id"], it["difficulty"], it["tokens_needed"], skill_ok, cap_ok, reason))
    print("-" * 60)
    print("  lost to truncation (config): %s   lost to skill (model): %s" % (lost_trunc, lost_skill))


def check(data):
    print("SELF-TEST — a matched config shows B's true win; an unfair token cap truncates a correct answer and erases it")
    print("-" * 116)
    items, sa, sb = data["items"], data["skill_a"], data["skill_b"]
    m, u = data["matched_config"], data["unfair_config"]

    ma, mb = score(items, sa, m["max_tokens_a"]), score(items, sb, m["max_tokens_b"])
    ua, ub = score(items, sa, u["max_tokens_a"]), score(items, sb, u["max_tokens_b"])

    matched_config_equal = m["max_tokens_a"] == m["max_tokens_b"]
    print("  matched config gives both models the same cap = %s" % matched_config_equal)

    b_truly_better = mb > ma
    print("  under the matched config B beats A = %s (%d vs %d)" % (b_truly_better, mb, ma))

    unfair_config_unequal = u["max_tokens_a"] != u["max_tokens_b"]
    print("  unfair config gives the two models different caps = %s" % unfair_config_unequal)

    unfair_erases_win = ub <= ua
    print("  under the unfair config B no longer beats A = %s (%d vs %d)" % (unfair_erases_win, ub, ua))

    lost_to_truncation = truncated_wins(items, sb, u["max_tokens_b"])
    erased_by_truncation = len(lost_to_truncation) > 0 and (mb - ub) == len(lost_to_truncation)
    print("  B's lost points are correct answers truncated by the cap = %s (%s)"
          % (erased_by_truncation, lost_to_truncation))

    ok = (matched_config_equal and b_truly_better and unfair_config_unequal
          and unfair_erases_win and erased_by_truncation)
    print("-" * 116)
    print("SELF-TEST %s  matched_config_equal=%s  b_truly_better=%s  unfair_config_unequal=%s  unfair_erases_win=%s  erased_by_truncation=%s"
          % ("PASS" if ok else "FAIL", matched_config_equal, b_truly_better, unfair_config_unequal,
             unfair_erases_win, erased_by_truncation))
    return ok


def main():
    p = argparse.ArgumentParser(description="Config parity: hold every harness setting except the model identical across a comparison -- prompt, temperature, and especially the output-length cap -- because a config difference confounds the model gap, and a stingy cap on one side can truncate correct answers and erase a real winner.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--attribute", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%d  skill_a=%d  skill_b=%d  file=%s  (the items and configs are a fixture)"
          % (len(data["items"]), data["skill_a"], data["skill_b"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.attribute:
        attribute_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
