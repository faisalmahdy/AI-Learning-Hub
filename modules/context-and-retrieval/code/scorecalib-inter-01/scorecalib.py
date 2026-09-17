"""A fixed absolute similarity threshold does not transfer across queries -- similarity scores are not calibrated between queries, so the cutoff that correctly separates relevant from irrelevant for a high-scoring query rejects the genuinely relevant answer for a low-scoring one; calibrate the threshold per query, relative to that query's own top score.

A retriever scores each candidate by similarity to the query, and to decide which candidates are relevant -- or whether to abstain -- a system compares the score to a threshold. The tempting choice is a single absolute number, like keep everything with cosine at least 0.70.

The flaw is that similarity scores mean different things for different queries. A query whose topic is richly represented in the corpus produces high scores, its best match near the top of the range. A query about a rare or narrow topic produces lower scores across the board, so even its single genuinely-best match sits well below the easy query's matches. The absolute threshold does not know which kind of query it is looking at, so one constant is simultaneously too loose for the easy query -- admitting marginal candidates -- and too strict for the hard query -- rejecting the correct answer because its absolute score is low.

The fix is to make the threshold relative to the query. Keep candidates whose score is at least a fraction of that query's own top score, so the cutoff scales with each query's range: a high-scoring query gets a high cutoff, a low-scoring one gets a low cutoff, and each keeps the candidates that stand out within its own distribution. (The gap between the top scores works similarly.) This is a different point from whether to have an abstention threshold at all -- the point is that its value cannot be one global constant.

On this fixture the easy query scores 0.90, 0.82, 0.45, 0.30 with 2 truly relevant, and the hard query scores 0.58, 0.40, 0.35, 0.30 with 1 truly relevant. An absolute threshold of 0.70 keeps the right 2 for the easy query but keeps 0 for the hard query, missing its relevant answer at 0.58; a relative threshold of 0.85 times the query's top score keeps 2 and 1, both correct. This computes both.

  --absolute  a fixed 0.70 cutoff: right for the easy query, wrong for the hard one
  --relative  0.85 times each query's top score: right for both
  --check     the absolute threshold matches the truth for the high-scoring query but not the low-scoring one, while the relative threshold matches both

the queries, their scores, and the true relevant counts are the fixture; the retrieved counts under each strategy are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "scorecalib.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def keep_absolute(scores, threshold):
    """Keep candidates whose score meets a fixed absolute threshold."""
    return [s for s in scores if s >= threshold]


def keep_relative(scores, ratio):
    """Keep candidates whose score is at least a fraction of this query's own top score."""
    cutoff = ratio * max(scores)
    return [s for s in scores if s >= cutoff]


def correct(kept, relevant):
    """Whether the number kept equals the number of truly relevant candidates."""
    return len(kept) == relevant


# ----------------------------------------------------------------- printing

def absolute_view(d):
    t = d["absolute_threshold"]
    print("ABSOLUTE — one fixed cutoff of %.2f for every query" % t)
    print("-" * 64)
    for q in d["queries"]:
        kept = keep_absolute(q["scores"], t)
        print("  %-5s scores %s  kept %d  (truth %d)  %s"
              % (q["name"], q["scores"], len(kept), q["relevant"], "ok" if correct(kept, q["relevant"]) else "WRONG"))
    print("-" * 64)
    print("  the cutoff that fits the high-scoring query rejects the low-scoring query's real answer")


def relative_view(d):
    r = d["relative_ratio"]
    print("RELATIVE — cutoff = %.2f x each query's own top score" % r)
    print("-" * 64)
    for q in d["queries"]:
        kept = keep_relative(q["scores"], r)
        print("  %-5s top %.2f  cutoff %.3f  kept %d  (truth %d)  %s"
              % (q["name"], max(q["scores"]), r * max(q["scores"]), len(kept), q["relevant"], "ok" if correct(kept, q["relevant"]) else "WRONG"))
    print("-" * 64)
    print("  the cutoff scales to each query's range, so each keeps what stands out for it")


def check(d):
    print("SELF-TEST — the absolute threshold matches the truth for the high-scoring query but not the low-scoring one, while the relative threshold matches both")
    print("-" * 112)
    t, r = d["absolute_threshold"], d["relative_ratio"]
    easy = next(q for q in d["queries"] if q["name"] == "easy")
    hard = next(q for q in d["queries"] if q["name"] == "hard")

    abs_ok_easy = correct(keep_absolute(easy["scores"], t), easy["relevant"])
    print("  absolute threshold is correct for the high-scoring query = %s (kept %d, truth %d)" % (abs_ok_easy, len(keep_absolute(easy["scores"], t)), easy["relevant"]))

    abs_fails_hard = not correct(keep_absolute(hard["scores"], t), hard["relevant"])
    print("  absolute threshold is WRONG for the low-scoring query = %s (kept %d, truth %d)" % (abs_fails_hard, len(keep_absolute(hard["scores"], t)), hard["relevant"]))

    rel_ok_easy = correct(keep_relative(easy["scores"], r), easy["relevant"])
    rel_ok_hard = correct(keep_relative(hard["scores"], r), hard["relevant"])
    print("  relative threshold is correct for both queries = %s (easy %s, hard %s)" % (rel_ok_easy and rel_ok_hard, rel_ok_easy, rel_ok_hard))

    not_transferable = abs_ok_easy and abs_fails_hard
    print("  the same absolute cutoff works for one query and not the other (not transferable) = %s" % not_transferable)

    ok = (abs_ok_easy and abs_fails_hard and rel_ok_easy and rel_ok_hard and not_transferable)
    print("-" * 112)
    print("SELF-TEST %s  abs_ok_easy=%s  abs_fails_hard=%s  rel_ok_easy=%s  rel_ok_hard=%s  not_transferable=%s"
          % ("PASS" if ok else "FAIL", abs_ok_easy, abs_fails_hard, rel_ok_easy, rel_ok_hard, not_transferable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Per-query score calibration: a fixed absolute similarity threshold does not transfer across queries, because scores are not calibrated between queries -- a high-scoring query's cutoff admits marginal candidates and a low-scoring query's genuinely-best answer falls below the same cutoff and is rejected; make the threshold relative to each query's own top score (or the gap between top scores) so it scales with the query's range.")
    p.add_argument("--absolute", action="store_true")
    p.add_argument("--relative", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("absolute_threshold=%.2f  relative_ratio=%.2f  queries=%d  file=%s"
          % (d["absolute_threshold"], d["relative_ratio"], len(d["queries"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.absolute:
        absolute_view(d)
    elif args.relative:
        relative_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
