"""Place the best retrieved chunks at the context edges -- models lose the middle.

Retrieval hands the model a set of chunks to read, and there is a real choice in what order to
put them. The natural order is by relevance, best first. But long-context models do not attend
uniformly across their input: they use information at the very start and the very end far more
than information buried in the middle -- the 'lost in the middle' effect, a U-shaped attention
profile. So the order that matters is not 'best first' but 'best at the edges', and a chunk's
usefulness is its relevance times how much the model attends to the slot you put it in.

The naive placement sorts chunks by relevance and drops them into slots in that order, which
sends the second- and third-best chunks straight into the dead middle. The edge-aware placement
pairs the most relevant chunks with the highest-attention slots -- the two edges first, then
working inward -- so the strongest evidence lands where the model actually reads and the weakest
chunk is the one left in the middle. On this fixture the edge-aware order carries 2.12 units of
effective information to the naive order's 1.80, a 18% gain, with no change to which chunks were
retrieved -- only where they sit. This computes both placements' effective information and shows
the edge-aware one dominates, which is the rearrangement inequality in action.

  --slots      the position-attention profile and each placement's chunk-to-slot assignment
  --effective  the effective information (relevance x slot attention) of each placement
  --check      the middle is low-attention; edge-aware beats naive; the gold sits at an edge

The chunk relevances and slot-attention weights are the fixture; every placement and score is
computed. Deterministic; stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chunks.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two placements

def naive_placement(relevances):
    """Sort chunks by relevance and drop them into slots 0,1,2,... in that order."""
    order = sorted(range(len(relevances)), key=lambda i: (-relevances[i], i))
    # slot s holds the s-th most relevant chunk
    return {s: chunk for s, chunk in enumerate(order)}


def edge_aware_placement(relevances, weights):
    """Pair the most relevant chunks with the highest-attention slots (edges first)."""
    chunks_by_rel = sorted(range(len(relevances)), key=lambda i: (-relevances[i], i))
    slots_by_attn = sorted(range(len(weights)), key=lambda s: (-weights[s], s))
    return {slot: chunk for slot, chunk in zip(slots_by_attn, chunks_by_rel)}


# ------------------------------------------------------------- effective information

def effective_information(placement, relevances, weights):
    """Sum over slots of (chunk relevance) x (slot attention) -- what the model actually gets."""
    return sum(relevances[chunk] * weights[slot] for slot, chunk in placement.items())


def slot_of(placement, chunk):
    for slot, c in placement.items():
        if c == chunk:
            return slot
    return None


# ----------------------------------------------------------------- printing

def slots_view(data):
    rel, w = data["relevances"], data["slot_weights"]
    naive = naive_placement(rel)
    edge = edge_aware_placement(rel, w)
    print("SLOTS — attention per position (U-shaped: edges high, middle low)")
    print("-" * 62)
    print("  slot   attention   naive chunk (rel)     edge-aware chunk (rel)")
    for s in range(len(w)):
        print("  %-6d %-11.2f c%d (%.2f)             c%d (%.2f)"
              % (s, w[s], naive[s], rel[naive[s]], edge[s], rel[edge[s]]))
    print("-" * 62)
    print("  naive puts the 2nd/3rd-best chunks in the middle; edge-aware puts the worst there.")


def effective_view(data):
    rel, w = data["relevances"], data["slot_weights"]
    naive = naive_placement(rel)
    edge = edge_aware_placement(rel, w)
    en = effective_information(naive, rel, w)
    ee = effective_information(edge, rel, w)
    print("EFFECTIVE — information delivered (relevance x slot attention)")
    print("-" * 62)
    print("  naive placement:      %.4f" % en)
    print("  edge-aware placement: %.4f" % ee)
    print("  gain from reordering: %.4f (%.0f%%), same chunks, different slots"
          % (ee - en, 100 * (ee - en) / en))
    print("-" * 62)
    print("  reordering alone -- no new retrieval -- lifts the information the model can use.")


def check(data):
    print("SELF-TEST — the middle is low-attention; edge-aware beats naive; the gold sits at an edge")
    print("-" * 62)
    rel, w = data["relevances"], data["slot_weights"]
    n = len(w)

    mid = n // 2
    middle_lowest = w[mid] == min(w) and w[0] == max(w) and w[-1] == max(w)
    print("  the middle slot has the least attention, the edges the most = %s (mid %.2f, edge %.2f)"
          % (middle_lowest, w[mid], w[0]))

    naive = naive_placement(rel)
    edge = edge_aware_placement(rel, w)
    en = effective_information(naive, rel, w)
    ee = effective_information(edge, rel, w)

    edge_better = ee > en
    print("  edge-aware carries more effective information than naive = %s (%.4f vs %.4f)"
          % (edge_better, ee, en))

    gold = max(range(len(rel)), key=lambda i: rel[i])
    gold_slot = slot_of(edge, gold)
    gold_at_edge = w[gold_slot] == max(w)
    print("  the most relevant chunk sits in a max-attention (edge) slot = %s (chunk c%d at slot %d)"
          % (gold_at_edge, gold, gold_slot))

    worst = min(range(len(rel)), key=lambda i: rel[i])
    worst_slot = slot_of(edge, worst)
    worst_in_middle = w[worst_slot] == min(w)
    print("  the least relevant chunk is the one left in the dead middle = %s (chunk c%d at slot %d)"
          % (worst_in_middle, worst, worst_slot))

    ok = middle_lowest and edge_better and gold_at_edge and worst_in_middle
    print("-" * 62)
    print("SELF-TEST %s  middle_lowest=%s  edge_better=%s  gold_at_edge=%s  worst_in_middle=%s"
          % ("PASS" if ok else "FAIL", middle_lowest, edge_better, gold_at_edge, worst_in_middle))
    return ok


def main():
    p = argparse.ArgumentParser(description="Place the best retrieved chunks at the context edges.")
    p.add_argument("--slots", action="store_true")
    p.add_argument("--effective", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("chunks=%d  slots=%d  file=%s  (relevances and slot attention are a fixture)"
          % (len(data["relevances"]), len(data["slot_weights"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.slots:
        slots_view(data)
    elif args.effective:
        effective_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
