"""Shrinking an embedding by keeping only its first k dimensions is safe only if the model was trained to front-load its information (a Matryoshka embedding) -- truncate an ordinary embedding, whose signal is spread across all dimensions, and the ranking can flip and return the wrong document, even though at full width both models rank correctly.

Halving a vector store's dimension is a real way to cut cost and memory, and the tempting implementation is to slice every stored vector to its first k dimensions. Whether that is safe is a property of the embedding model, not of the slice.

A Matryoshka-trained model (also called MRL) is optimized so that the leading dimensions carry the most important directions -- a prefix of the vector is itself a usable, lower-dimensional embedding, and cosine ranking over the prefix still works. An ordinary model has no such property: it spreads the discriminating signal across the whole vector, so slicing off the tail can throw away exactly the dimensions that carried the answer, and the truncated ranking flips.

On this fixture both models rank the relevant document above the distractor at full dimension, with identical cosines (0.923 vs 0.588), so at full width you cannot tell them apart. Truncate to the first 3 of 6 dimensions and they diverge: the ordinary model now scores the distractor 1.000 and the relevant document 0.000 -- a flip to the wrong answer -- while the Matryoshka model still ranks the relevant document first, 1.000 to 0.577. Same truncation, opposite outcome, decided entirely by how the model laid out its dimensions.

A second, separate point the same operation raises: truncating a unit-length vector leaves it no longer unit length, so an index that ranks by raw dot product rather than cosine must renormalize after truncation, or every score is silently rescaled by the shortened vector's norm.

  --full    both models at full dimension: each ranks the relevant document first, identically
  --trunc   both models truncated to the first k dimensions: the ordinary model flips to the distractor, the Matryoshka model does not
  --check   at full dim both rank the relevant doc first; truncated, the ordinary model ranks the distractor first while the Matryoshka model still ranks the relevant doc first, and truncation changes a unit vector's norm

dim, k, and the two embedding sets are the fixture; every full and truncated cosine, the induced ranking, and the norm change are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dimtrunc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(a, b):
    """Direction similarity: dot product over the product of norms."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


def truncate(v, k):
    """Keep only the first k dimensions of the vector."""
    return v[:k]


def norm(v):
    """The Euclidean length of the vector."""
    return math.sqrt(sum(x * x for x in v))


def rank(model, k=None):
    """Cosine of the query against each doc (optionally truncated to k dims), and which doc wins."""
    q = model["query"] if k is None else truncate(model["query"], k)
    rel = model["relevant"] if k is None else truncate(model["relevant"], k)
    dist = model["distractor"] if k is None else truncate(model["distractor"], k)
    cr, cd = cosine(q, rel), cosine(q, dist)
    return cr, cd, ("relevant" if cr > cd else "distractor")


# ----------------------------------------------------------------- printing

def full_view(data):
    print("FULL — both models at full dimension %d" % data["dim"])
    print("-" * 64)
    for name in ("ordinary", "matryoshka"):
        cr, cd, w = rank(data[name])
        print("  %-11s relevant=%.3f  distractor=%.3f  -> ranks %s first" % (name, cr, cd, w))
    print("-" * 64)
    print("  identical at full width: both models put the relevant document first")


def trunc_view(data):
    k = data["k"]
    print("TRUNC — both models truncated to the first %d of %d dimensions" % (k, data["dim"]))
    print("-" * 64)
    for name in ("ordinary", "matryoshka"):
        cr, cd, w = rank(data[name], k)
        flag = "   <- FLIPPED to the wrong doc" if w == "distractor" else ""
        print("  %-11s relevant=%.3f  distractor=%.3f  -> ranks %s first%s" % (name, cr, cd, w, flag))
    print("-" * 64)
    print("  the ordinary embedding's signal was in the dropped dimensions; the Matryoshka's was not")


def check(data):
    print("SELF-TEST — at full dim both rank the relevant doc first; truncated, the ordinary model ranks the distractor first while the Matryoshka model still ranks the relevant doc first, and truncation changes a unit vector's norm")
    print("-" * 112)
    ordn, mat = data["ordinary"], data["matryoshka"]

    _, _, ord_full = rank(ordn)
    _, _, mat_full = rank(mat)
    full_both_correct = ord_full == "relevant" and mat_full == "relevant"
    print("  at full dimension both models rank the relevant doc first = %s (ordinary=%s, matryoshka=%s)" % (full_both_correct, ord_full, mat_full))

    ocr, ocd, ord_trunc = rank(ordn, data["k"])
    trunc_breaks_ordinary = ord_trunc == "distractor"
    print("  truncated, the ordinary model ranks the DISTRACTOR first = %s (relevant=%.3f, distractor=%.3f)" % (trunc_breaks_ordinary, ocr, ocd))

    mcr, mcd, mat_trunc = rank(mat, data["k"])
    trunc_keeps_matryoshka = mat_trunc == "relevant"
    print("  truncated, the Matryoshka model still ranks the relevant doc first = %s (relevant=%.3f, distractor=%.3f)" % (trunc_keeps_matryoshka, mcr, mcd))

    full_norm = norm(ordn["query"])
    trunc_norm = norm(truncate(ordn["query"], data["k"]))
    norm_changes = abs(full_norm - trunc_norm) > 1e-9
    print("  truncating changes the vector's norm (dot-product indexes must renormalize) = %s (%.3f -> %.3f)" % (norm_changes, full_norm, trunc_norm))

    ok = (full_both_correct and trunc_breaks_ordinary and trunc_keeps_matryoshka and norm_changes)
    print("-" * 112)
    print("SELF-TEST %s  full_both_correct=%s  trunc_breaks_ordinary=%s  trunc_keeps_matryoshka=%s  norm_changes=%s"
          % ("PASS" if ok else "FAIL", full_both_correct, trunc_breaks_ordinary, trunc_keeps_matryoshka, norm_changes))
    return ok


def main():
    p = argparse.ArgumentParser(description="Embedding dimension truncation: keeping only the first k dimensions of an embedding shrinks the index, but it preserves ranking only for a Matryoshka-trained model that front-loads its information -- truncating an ordinary embedding, whose signal is spread across all dimensions, can flip the ranking and return the wrong document, even though both models rank correctly at full width; and truncating a unit vector changes its norm, so dot-product indexes must renormalize.")
    p.add_argument("--full", action="store_true")
    p.add_argument("--trunc", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("dim=%d  k=%d  file=%s" % (data["dim"], data["k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.full:
        full_view(data)
    elif args.trunc:
        trunc_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
