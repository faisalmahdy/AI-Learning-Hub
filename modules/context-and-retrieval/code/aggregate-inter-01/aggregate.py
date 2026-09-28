"""Retrieve by relevance threshold, not a fixed top-k, for an aggregation query -- 'how many' and 'list all' answers are spread across every relevant passage, so a top-k smaller than the number of relevant passages returns a subset and the count comes out short.

Top-k retrieval is built for a needle query: 'what is X'. The answer lives in the single best passage or two, so returning the top few and stopping is exactly right, and a bigger k would just add noise. Almost all retrieval defaults -- a fixed k of 3, 5, 10 -- assume this shape.

An aggregation query has the opposite shape. 'How many security incidents were there in 2023', 'list all the affected customers', 'what are every error code we returned' -- the answer is not in one passage, it is the whole set of relevant passages, and each one contributes a piece: one incident, one customer, one code. The number of passages you need is the size of the answer, which is exactly what you do not know in advance.

A fixed top-k that is smaller than the number of relevant passages then undercounts. It returns its k best passages -- all genuinely relevant, no error raised -- and the answer built from them is short, because k was the wrong stopping rule for a question whose answer is a set. The retriever did its job; the query type broke the assumption baked into k.

The fix is to stop by relevance, not by rank. Retrieve every passage above a relevance threshold, so the amount retrieved adapts to how much is relevant: a needle query has one or two passages above the bar, an aggregation query has all of them, and each gets the evidence its answer actually needs. (Recognizing the query type and raising k, or aggregating in passes, are variants of the same move -- let the answer's size, not a constant, decide how much to pull.)

On this fixture five passages each describe one distinct 2023 incident and all score above the threshold, while two irrelevant passages score below it. Top-3 returns three incidents and counts 3; threshold retrieval returns all five and counts the true 5. This computes both.

  --topk       fixed top-3 retrieval: three of the five incidents, an undercount
  --threshold  relevance-threshold retrieval: all five incidents, the correct count
  --check      the top-k count is short of the truth while the threshold count matches it, and every incident passage was above the threshold

passages, the fixed k, the threshold, and the true count are the fixture; what each strategy retrieves and counts is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "aggregate.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def retrieve_topk(passages, k):
    """The k highest-relevance passages -- a fixed stopping rule, right for a needle query."""
    return sorted(passages, key=lambda p: p["relevance"], reverse=True)[:k]


def retrieve_threshold(passages, threshold):
    """Every passage at or above the relevance threshold -- the amount adapts to how much is relevant."""
    return [p for p in passages if p["relevance"] >= threshold]


def count_incidents(retrieved):
    """The answer to 'how many incidents': the retrieved passages that each describe one."""
    return sum(1 for p in retrieved if p["incident"])


# ----------------------------------------------------------------- printing

def _ids(passages):
    return [p["id"] for p in passages]


def topk_view(data):
    got = retrieve_topk(data["passages"], data["top_k"])
    print("TOPK — fixed top-%d retrieval" % data["top_k"])
    print("-" * 60)
    print("  retrieved: %s" % _ids(got))
    print("  incidents counted = %d   (true count %d)" % (count_incidents(got), data["true_count"]))
    print("-" * 60)
    print("  every retrieved passage is relevant, yet the count is short -- k stopped too early")


def threshold_view(data):
    got = retrieve_threshold(data["passages"], data["relevance_threshold"])
    print("THRESHOLD — retrieve every passage at or above relevance %.2f" % data["relevance_threshold"])
    print("-" * 60)
    print("  retrieved: %s" % _ids(got))
    print("  incidents counted = %d   (true count %d)" % (count_incidents(got), data["true_count"]))
    print("-" * 60)
    print("  the amount retrieved adapted to how much was relevant, so the count is complete")


def check(data):
    print("SELF-TEST — the top-k count is short of the truth while the threshold count matches it, and every incident passage was above the threshold")
    print("-" * 112)
    passages, true = data["passages"], data["true_count"]
    topk = retrieve_topk(passages, data["top_k"])
    thr = retrieve_threshold(passages, data["relevance_threshold"])

    topk_undercounts = count_incidents(topk) < true
    print("  the top-%d count is short of the true count = %s (%d < %d)" % (data["top_k"], topk_undercounts, count_incidents(topk), true))

    threshold_correct = count_incidents(thr) == true
    print("  the threshold count matches the true count = %s (%d == %d)" % (threshold_correct, count_incidents(thr), true))

    all_incidents_relevant = all(p["relevance"] >= data["relevance_threshold"] for p in passages if p["incident"])
    print("  every incident passage is above the threshold (retrieval is not at fault) = %s" % all_incidents_relevant)

    topk_returns_k = len(topk) == data["top_k"]
    print("  top-k returned exactly k passages (the cap) = %s (%d)" % (topk_returns_k, len(topk)))

    threshold_returns_all = len(thr) >= true
    print("  threshold returned at least the true count of passages = %s (%d)" % (threshold_returns_all, len(thr)))

    ok = (topk_undercounts and threshold_correct and all_incidents_relevant
          and topk_returns_k and threshold_returns_all)
    print("-" * 112)
    print("SELF-TEST %s  topk_undercounts=%s  threshold_correct=%s  all_incidents_relevant=%s  topk_returns_k=%s  threshold_returns_all=%s"
          % ("PASS" if ok else "FAIL", topk_undercounts, threshold_correct, all_incidents_relevant,
             topk_returns_k, threshold_returns_all))
    return ok


def main():
    p = argparse.ArgumentParser(description="Aggregation retrieval: for a counting or list-all query whose answer is spread across every relevant passage, retrieve by a relevance threshold rather than a fixed top-k, because a top-k smaller than the number of relevant passages returns a subset and the answer comes out incomplete -- k is a stopping rule tuned for needle queries, not aggregation ones.")
    p.add_argument("--topk", action="store_true")
    p.add_argument("--threshold", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("passages=%d  top_k=%d  threshold=%.2f  true_count=%d  file=%s"
          % (len(data["passages"]), data["top_k"], data["relevance_threshold"], data["true_count"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.topk:
        topk_view(data)
    elif args.threshold:
        threshold_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
