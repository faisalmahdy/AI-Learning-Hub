"""Put the most relevant documents at the ends of the context, not the middle -- a model attends least to the middle, so a gold document buried there is present but unused.

You retrieve the right documents and paste them into the context, and the model still misses the answer. The retrieval was not the problem; the ORDER was. A long-context model does not read its context uniformly -- it attends most strongly to the beginning and the end and least to the middle, an empirically robust 'lost in the middle' effect. So a document's usefulness depends not only on whether it is in the context but on WHERE: the same gold passage that would be used at position one or position last can be effectively invisible sitting in the middle of a stack of retrieved documents.

The naive pipeline makes this easy to trigger. Retrieve top-k, place the documents in whatever order the retriever returned, and hand the block to the model. If the retriever's order is not aligned with the context's positional bias -- and it usually is not, because retrievers rank by relevance, not by where relevance should sit -- the most relevant document can land in the low-attention middle. It is in the context; the model just does not lean on it. The failure looks like a retrieval miss (the answer is wrong) but the document was right there, in the dead zone.

The fix reorders the retrieved documents to match the context's attention profile: place the highest-relevance document at one end, the next at the other end, and continue folding inward, so the strongest documents occupy the high-attention positions and the weakest fall into the middle where being under-attended costs the least. This does not change what was retrieved or how many documents are included; it changes only their arrangement, and it moves the gold document out of the middle and onto an edge. As a bonus, arranging documents so relevance lines up with positional weight raises the total attended signal, not just the gold document's.

The rule: order retrieved documents so the most relevant sit at the START and END of the context and the least relevant in the middle, rather than pasting them in retrieval-rank order, because a model attends least to the middle of a long context -- so a highly relevant document placed there is present but effectively unused, while edge placement puts it where the model actually attends.

On this fixture the gold document d2 (the most relevant) is returned in the middle of the retriever's order, so naive placement gives it positional weight 0.2, below the 0.4 recall threshold -- lost. Edge reordering puts d2 at an end (weight 1.0), above threshold -- used -- and raises the total effective signal from 11.3 to 17.9. This computes both.

  --place     naive (retrieval-order) vs edge-reordered placement, and each slot's positional weight
  --signal    the gold document's positional weight under each, and the total effective signal (relevance x weight)
  --check     the gold is buried in the middle under naive placement and lost; edge reordering moves it to an end and recovers it

positional_weights, recall_threshold, gold, and retrieved_order are the fixture; every placement, weight, and signal total is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lostmiddle.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_placement(docs):
    """Place documents in the order the retriever returned them."""
    return list(docs)


def edge_placement(docs):
    """Reorder by relevance to the edges: highest at one end, next at the other, folding inward."""
    ranked = sorted(docs, key=lambda d: (-d["relevance"], d["id"]))
    slots = [None] * len(ranked)
    left, right = 0, len(ranked) - 1
    for i, d in enumerate(ranked):
        if i % 2 == 0:
            slots[left] = d
            left += 1
        else:
            slots[right] = d
            right -= 1
    return slots


def gold_weight(placement, weights, gold):
    """The positional weight of the slot the gold document lands in."""
    for i, d in enumerate(placement):
        if d["id"] == gold:
            return weights[i], i
    return 0.0, -1


def effective_signal(placement, weights):
    """Total attended signal: each document's relevance times its position's weight."""
    return sum(d["relevance"] * weights[i] for i, d in enumerate(placement))


# ----------------------------------------------------------------- printing

def place_view(data):
    docs, weights = data["retrieved_order"], data["positional_weights"]
    print("PLACE — naive (retrieval order) vs edge-reordered placement")
    print("-" * 62)
    print("  position weights (U-shaped): %s" % weights)
    print("  naive : %s" % " ".join("%s(r%d,w%.1f)" % (d["id"], d["relevance"], weights[i]) for i, d in enumerate(naive_placement(docs))))
    print("  edges : %s" % " ".join("%s(r%d,w%.1f)" % (d["id"], d["relevance"], weights[i]) for i, d in enumerate(edge_placement(docs))))


def signal_view(data):
    docs, weights, gold, thr = data["retrieved_order"], data["positional_weights"], data["gold"], data["recall_threshold"]
    nw, ni = gold_weight(naive_placement(docs), weights, gold)
    ew, ei = gold_weight(edge_placement(docs), weights, gold)
    print("SIGNAL — the gold document's positional weight and total effective signal")
    print("-" * 66)
    print("  gold = %s (threshold to be used = %.1f)" % (gold, thr))
    print("  naive: gold at position %d, weight %.1f -> %s" % (ni, nw, "USED" if nw >= thr else "LOST (below threshold)"))
    print("  edges: gold at position %d, weight %.1f -> %s" % (ei, ew, "USED" if ew >= thr else "LOST (below threshold)"))
    print("-" * 66)
    print("  total effective signal (sum relevance x weight):  naive = %.1f   edges = %.1f" % (effective_signal(naive_placement(docs), weights), effective_signal(edge_placement(docs), weights)))


def check(data):
    print("SELF-TEST — the gold is buried in the middle under naive placement and lost; edge reordering moves it to an end and recovers it")
    print("-" * 126)
    docs, weights, gold, thr = data["retrieved_order"], data["positional_weights"], data["gold"], data["recall_threshold"]
    naive = naive_placement(docs)
    edges = edge_placement(docs)
    nw, ni = gold_weight(naive, weights, gold)
    ew, ei = gold_weight(edges, weights, gold)
    n = len(weights)

    weights_u_shaped = weights[n // 2] < weights[0] and weights[n // 2] < weights[-1]
    print("  the position weights are U-shaped (middle < ends) = %s (mid %.1f < ends %.1f/%.1f)" % (weights_u_shaped, weights[n // 2], weights[0], weights[-1]))

    gold_is_most_relevant = gold == max(docs, key=lambda d: d["relevance"])["id"]
    print("  the gold document is the most relevant retrieved = %s" % gold_is_most_relevant)

    naive_buries_gold = 0 < ni < n - 1 and nw < thr
    print("  naive placement puts the gold in a low-weight middle slot = %s (position %d, weight %.1f < %.1f)" % (naive_buries_gold, ni, nw, thr))

    naive_loses_gold = nw < thr
    print("  under naive placement the gold is lost (below threshold) = %s" % naive_loses_gold)

    edge_places_gold_at_end = ei == 0 or ei == n - 1
    print("  edge reordering places the gold at an end position = %s (position %d)" % (edge_places_gold_at_end, ei))

    edge_recovers_gold = ew >= thr
    print("  under edge reordering the gold is used (at or above threshold) = %s (weight %.1f)" % (edge_recovers_gold, ew))

    edge_raises_signal = effective_signal(edges, weights) > effective_signal(naive, weights)
    print("  edge reordering raises the total effective signal = %s (%.1f > %.1f)" % (edge_raises_signal, effective_signal(edges, weights), effective_signal(naive, weights)))

    ok = weights_u_shaped and gold_is_most_relevant and naive_buries_gold and naive_loses_gold and edge_places_gold_at_end and edge_recovers_gold and edge_raises_signal
    print("-" * 126)
    print("SELF-TEST %s  weights_u_shaped=%s  gold_is_most_relevant=%s  naive_buries_gold=%s  naive_loses_gold=%s  edge_places_gold_at_end=%s  edge_recovers_gold=%s  edge_raises_signal=%s"
          % ("PASS" if ok else "FAIL", weights_u_shaped, gold_is_most_relevant, naive_buries_gold, naive_loses_gold, edge_places_gold_at_end, edge_recovers_gold, edge_raises_signal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Lost in the middle: order retrieved documents so the most relevant sit at the START and END of the context and the least relevant in the middle, rather than pasting them in retrieval-rank order, because a model attends least to the middle of a long context -- so a highly relevant document placed there is present but effectively unused, while edge placement puts it where the model actually attends.")
    p.add_argument("--place", action="store_true")
    p.add_argument("--signal", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  gold=%s  recall_threshold=%.1f  file=%s  (the docs, weights, and threshold are a fixture)"
          % (len(data["retrieved_order"]), data["gold"], data["recall_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.place:
        place_view(data)
    elif args.signal:
        signal_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
