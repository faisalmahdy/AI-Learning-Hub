"""Rank models by a strength that accounts for opponents, or raw win-rate rewards an easy schedule.

You have pairwise results -- model A beat model B 7 of 10 times, and so on -- and you want one ranking. The
tempting summary is raw win-rate: total wins over total games. It is wrong whenever the schedule is
unbalanced, because a win against a weak opponent counts the same as a win against a strong one. A mediocre
model that mostly played weak opponents racks up a high win-rate; a strong model that mostly faced tough
opponents posts a low one. Rank by raw win-rate and you crown the model with the easiest schedule, not the
best model.

Bradley-Terry (the model behind Elo and the Chatbot Arena leaderboard) fixes this by fitting each model a
strength such that the predicted win probability between any two is strength_i / (strength_i + strength_j).
It explains all the results at once, so beating a strong opponent counts for more than beating a weak one,
and losing to a strong opponent costs less than losing to a weak one. The fitted strengths recover the true
ranking regardless of who played whom, because the schedule is baked into the fit rather than ignored.

On this fixture four models have a genuine strength order A > B > C > D, but the schedule is rigged: C
farmed the weak D while B was ground down by the strong A. Raw win-rate ranks C above B -- the wrong order
-- because C's wins were cheap and B's losses were to the best model. Bradley-Terry, accounting for
opponents, ranks B above C, recovering the true order. This computes both.

  --winrate    each model's raw win-rate and the ranking it produces
  --strength   the fitted Bradley-Terry strengths and their ranking
  --check      raw win-rate misranks the easy-schedule model; Bradley-Terry recovers the true order

The match results and true order are the fixture; every rating is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "matches.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def wins_of(wins, m):
    return sum(wins[m].values())


def games_of(wins, m, players):
    return sum(wins[m].get(o, 0) + wins[o].get(m, 0) for o in players if o != m)


def win_rate(wins, m, players):
    g = games_of(wins, m, players)
    return round(wins_of(wins, m) / g, 3) if g else 0.0


def ranking(scores):
    """Player ids ordered from highest score to lowest."""
    return sorted(scores, key=lambda m: scores[m], reverse=True)


def bradley_terry(wins, players, iters=200):
    """Fit each player's strength by the MM algorithm; strengths explain all pairwise results at once."""
    p = {m: 1.0 for m in players}
    for _ in range(iters):
        new = {}
        for m in players:
            w = wins_of(wins, m)
            denom = sum((wins[m].get(o, 0) + wins[o].get(m, 0)) / (p[m] + p[o]) for o in players if o != m)
            new[m] = w / denom if denom else p[m]
        s = sum(new.values())
        p = {m: v / s * len(players) for m, v in new.items()}   # normalize to keep scale stable
    return {m: round(p[m], 3) for m in players}


# ----------------------------------------------------------------- printing

def winrate_view(data):
    wins, players = data["wins"], data["players"]
    wr = {m: win_rate(wins, m, players) for m in players}
    print("WINRATE — raw wins / games and the ranking it gives")
    print("-" * 52)
    for m in players:
        print("  %s  wins %2d  games %2d  win-rate %.3f" % (m, wins_of(wins, m), games_of(wins, m, players), wr[m]))
    print("-" * 52)
    print("  raw ranking: %s   (true: %s)" % (" > ".join(ranking(wr)), " > ".join(data["true_order"])))


def strength_view(data):
    wins, players = data["wins"], data["players"]
    bt = bradley_terry(wins, players)
    print("STRENGTH — fitted Bradley-Terry strengths and the ranking they give")
    print("-" * 52)
    for m in ranking(bt):
        print("  %s  strength %.3f" % (m, bt[m]))
    print("-" * 52)
    print("  BT ranking: %s   (true: %s)" % (" > ".join(ranking(bt)), " > ".join(data["true_order"])))


def check(data):
    print("SELF-TEST — raw win-rate misranks the easy-schedule model; Bradley-Terry recovers the true order")
    print("-" * 96)
    wins, players, true = data["wins"], data["players"], data["true_order"]
    wr = {m: win_rate(wins, m, players) for m in players}
    bt = bradley_terry(wins, players)
    wr_rank = ranking(wr)
    bt_rank = ranking(bt)

    winrate_wrong = wr_rank != true
    print("  raw win-rate's ranking is not the true order = %s (%s)" % (winrate_wrong, " > ".join(wr_rank)))

    bt_correct = bt_rank == true
    print("  Bradley-Terry's ranking is the true order = %s (%s)" % (bt_correct, " > ".join(bt_rank)))

    # the specific inversion: C (easy schedule) above B (hard schedule) under win-rate
    easy, hard = data["easy_model"], data["hard_model"]
    winrate_inverts = wr_rank.index(easy) < wr_rank.index(hard)
    print("  win-rate puts the easy-schedule %s above the hard-schedule %s = %s" % (easy, hard, winrate_inverts))

    bt_fixes = bt_rank.index(hard) < bt_rank.index(easy)
    print("  Bradley-Terry puts %s back above %s = %s" % (hard, easy, bt_fixes))

    easy_higher_winrate = wr[easy] > wr[hard]
    print("  the easy-schedule model really did have the higher win-rate = %s (%.3f > %.3f)" % (easy_higher_winrate, wr[easy], wr[hard]))

    ok = winrate_wrong and bt_correct and winrate_inverts and bt_fixes and easy_higher_winrate
    print("-" * 96)
    print("SELF-TEST %s  winrate_wrong=%s  bt_correct=%s  winrate_inverts=%s  bt_fixes=%s  easy_higher_winrate=%s"
          % ("PASS" if ok else "FAIL", winrate_wrong, bt_correct, winrate_inverts, bt_fixes, easy_higher_winrate))
    return ok


def main():
    p = argparse.ArgumentParser(description="Rank models by Bradley-Terry strength, not raw win-rate.")
    p.add_argument("--winrate", action="store_true")
    p.add_argument("--strength", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("players=%d  file=%s  (the match results are a fixture)" % (len(data["players"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.winrate:
        winrate_view(data)
    elif args.strength:
        strength_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
