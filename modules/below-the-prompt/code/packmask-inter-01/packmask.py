"""Give packed training sequences a block-diagonal (document-aware) attention mask, not just a causal one -- otherwise a token in one packed document attends back into an unrelated document and learns dependencies that will never exist at inference.

Short training sequences waste compute. If the block length is 2048 and a document is 200 tokens, padding it out means the model runs attention over 1848 padding positions for every 200 real ones. Packing fixes this by concatenating many short documents into one full-length sequence, so nearly every position carries a real token and almost no compute is spent on padding. It is one of the highest-leverage efficiency tricks in training, and it is nearly free -- except for one thing that is easy to miss.

Packing changes what a 'sequence' is. The usual causal mask says a position may attend to itself and every position before it, which is exactly right when the sequence is one document. But after packing, the positions before a token may belong to a DIFFERENT document that was concatenated ahead of it. The first token of the second document, under a plain causal mask, can attend to every token of the first document -- two unrelated texts, now bleeding into each other. The model learns to predict the second document's tokens using the first document's content. That dependency is pure contamination: at inference each document arrives on its own, with nothing packed before it, so the model has learned to lean on a signal that will not be there, and it has been taught spurious cross-document correlations from whatever happened to be packed together.

The fix is a block-diagonal attention mask. Keep the causal constraint, and add one more: a position may attend to another only if they are in the same document (same segment id). Attention then splits into independent blocks along the diagonal -- each document attends only within itself -- so the packed sequence trains exactly as if each document had been run separately, but at full token efficiency. The mask is the only change; the tokens, the model, and the loss are untouched.

The rule: mask packed sequences block-diagonally by document, not with a bare causal mask, because packing puts unrelated documents in one sequence and a causal mask lets a later document attend into an earlier one -- teaching cross-document dependencies that never occur at inference; requiring same-segment attention confines each document to itself.

On this fixture two 3-token documents are packed into one sequence. Under a bare causal mask the second document has 9 attention edges reaching into the first document; the block-diagonal mask has 0, while preserving all 12 within-document edges. This computes both.

  --masks    the causal vs block-diagonal attention mask, position by position
  --leak     the cross-document and intra-document attention edges each mask allows
  --check    the causal mask leaks attention across the document boundary; the block-diagonal mask confines each document to itself

tokens and segment are the fixture; both masks, the edge counts, and each position's allowed attention are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "packmask.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def causal_mask(i, j):
    """A position may attend to itself and earlier positions."""
    return j <= i


def blockdiag_mask(i, j, segment):
    """Causal AND same document: a position attends only within its own segment."""
    return j <= i and segment[i] == segment[j]


def edges(n, allowed):
    return [(i, j) for i in range(n) for j in range(n) if allowed(i, j)]


def cross_doc(edge_list, segment):
    return [(i, j) for i, j in edge_list if segment[i] != segment[j]]


# ----------------------------------------------------------------- printing

def masks_view(data):
    seg = data["segment"]
    n = len(data["tokens"])
    print("MASKS — attention allowed (. = blocked, A = allowed) rows attend to columns")
    print("-" * 60)
    for name, allowed in (("causal", lambda i, j: causal_mask(i, j)),
                          ("block-diagonal", lambda i, j: blockdiag_mask(i, j, seg))):
        print("  %s (segments %s):" % (name, seg))
        for i in range(n):
            row = "".join("A" if allowed(i, j) else "." for j in range(n))
            print("    pos %d [doc %d]  %s" % (i, seg[i], row))
    print("-" * 60)
    print("  the causal mask's lower triangle crosses the doc boundary; the block-diagonal mask does not")


def leak_view(data):
    seg = data["segment"]
    n = len(data["tokens"])
    c_edges = edges(n, lambda i, j: causal_mask(i, j))
    b_edges = edges(n, lambda i, j: blockdiag_mask(i, j, seg))
    print("LEAK — attention edges each mask allows (%d tokens, 2 packed docs)" % n)
    print("-" * 60)
    print("  causal:         %d edges, %d cross-document" % (len(c_edges), len(cross_doc(c_edges, seg))))
    print("  block-diagonal: %d edges, %d cross-document" % (len(b_edges), len(cross_doc(b_edges, seg))))
    print("  cross-document edges under causal: %s" % cross_doc(c_edges, seg))
    print("-" * 60)
    print("  every cross-document edge is contamination: doc B attending into doc A")


def check(data):
    print("SELF-TEST — the causal mask leaks attention across the document boundary; the block-diagonal mask confines each document to itself")
    print("-" * 130)
    seg = data["segment"]
    n = len(data["tokens"])
    c_edges = edges(n, lambda i, j: causal_mask(i, j))
    b_edges = edges(n, lambda i, j: blockdiag_mask(i, j, seg))
    c_cross = cross_doc(c_edges, seg)
    b_cross = cross_doc(b_edges, seg)
    c_intra = [e for e in c_edges if seg[e[0]] == seg[e[1]]]
    b_intra = [e for e in b_edges if seg[e[0]] == seg[e[1]]]

    multiple_docs_packed = len(set(seg)) > 1
    print("  more than one document is packed into the sequence = %s (%d docs)" % (multiple_docs_packed, len(set(seg))))

    causal_leaks_across = len(c_cross) > 0
    print("  the causal mask allows attention across the document boundary = %s (%d edges)" % (causal_leaks_across, len(c_cross)))

    blockdiag_no_cross = len(b_cross) == 0
    print("  the block-diagonal mask allows NO cross-document attention = %s (%d edges)" % (blockdiag_no_cross, len(b_cross)))

    intra_preserved = c_intra == b_intra and len(b_intra) > 0
    print("  both masks preserve every within-document edge = %s (%d edges)" % (intra_preserved, len(b_intra)))

    first_b = seg.index(1)
    causal_b_sees_a = any(seg[j] == 0 for j in range(n) if causal_mask(first_b, j))
    blockdiag_b_isolated = all(seg[j] == 1 for j in range(n) if blockdiag_mask(first_b, j, seg))
    boundary_fixed = causal_b_sees_a and blockdiag_b_isolated
    print("  doc B's first token sees doc A under causal but not block-diagonal = %s (pos %d)" % (boundary_fixed, first_b))

    ok = (multiple_docs_packed and causal_leaks_across and blockdiag_no_cross and intra_preserved and boundary_fixed)
    print("-" * 130)
    print("SELF-TEST %s  multiple_docs_packed=%s  causal_leaks_across=%s  blockdiag_no_cross=%s  intra_preserved=%s  boundary_fixed=%s"
          % ("PASS" if ok else "FAIL", multiple_docs_packed, causal_leaks_across, blockdiag_no_cross, intra_preserved, boundary_fixed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Packed-sequence attention masking: mask packed sequences block-diagonally by document, not with a bare causal mask, because packing puts unrelated documents in one sequence and a causal mask lets a later document attend into an earlier one -- teaching cross-document dependencies that never occur at inference; requiring same-segment attention confines each document to itself.")
    p.add_argument("--masks", action="store_true")
    p.add_argument("--leak", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tokens=%s  segment=%s  file=%s  (the packed sequence is a fixture)"
          % (data["tokens"], data["segment"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.masks:
        masks_view(data)
    elif args.leak:
        leak_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
