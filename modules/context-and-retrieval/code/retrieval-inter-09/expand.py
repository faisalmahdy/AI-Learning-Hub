"""Expand a vague query before you embed it -- a short query lands far from the answer.

Dense retrieval matches a query's embedding against document embeddings. But a real user query
is short and underspecified -- a few keywords, not the full language of the answer -- so its
embedding sits in a thin, generic region of the space, close to anything sharing its one
keyword and not especially close to the document that actually answers it. A single-word query
about 'attention' is as near a document about paying attention in class as one about the
attention mechanism.

Query expansion fixes the input, not the index. Before embedding, grow the query into the
fuller language the answer would use -- add the concepts a real answer would contain, or (the
HyDE trick) generate a hypothetical answer and embed that. The expanded query lands in the
specific region of the space where the relevant document lives, so it retrieves what the raw
query missed. On this fixture the raw query ranks an off-topic distractor above the relevant
document (cosine 0.77 vs 0.52) and misses it at rank 1, while the expanded query puts the
relevant document first (1.00 vs 0.33). Same documents, same index, same scorer -- only the
query representation changed. This computes both retrievals and shows the miss become a hit.

  --query     the raw vs expanded query vectors and their similarity to each document
  --rank      the retrieval ranking under the raw query vs the expanded query
  --check     the raw query misses the relevant doc; expansion retrieves it first

The query and document vectors are the fixture; every similarity and rank is computed. Stdlib.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "vectors.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- cosine similarity

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cosine(a, b):
    na, nb = math.sqrt(dot(a, a)), math.sqrt(dot(b, b))
    return dot(a, b) / (na * nb) if na and nb else 0.0


# ------------------------------------------------------------- ranking

def ranked(query, docs):
    """Docs best-first by cosine similarity to the query."""
    scored = [(d["id"], round(cosine(query, d["vec"]), 4)) for d in docs]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored


def rank_of(query, docs, target):
    order = [i for i, _ in ranked(query, docs)]
    return order.index(target) + 1


# ----------------------------------------------------------------- printing

def query_view(data):
    docs, rel = data["docs"], data["relevant"]
    print("QUERY — cosine of the raw vs expanded query to each document (relevant = %s)" % rel)
    print("-" * 60)
    print("  doc      relevant?  raw q    expanded q")
    for d in docs:
        print("  %-8s %-10s %-8.4f %.4f"
              % (d["id"], d["id"] == rel, cosine(data["raw"], d["vec"]), cosine(data["expanded"], d["vec"])))
    print("-" * 60)
    print("  the raw query is vague, so it scores the off-topic distractor as high as the answer.")


def rank_view(data):
    docs = data["docs"]
    print("RANK — retrieval order under the raw query vs the expanded query")
    print("-" * 60)
    print("  raw query:      %s" % [("%s%s" % (i, "*" if i == data["relevant"] else "")) for i, _ in ranked(data["raw"], docs)])
    print("  expanded query: %s" % [("%s%s" % (i, "*" if i == data["relevant"] else "")) for i, _ in ranked(data["expanded"], docs)])
    print("-" * 60)
    print("  (* = relevant)  expansion moves the relevant doc from missed to rank 1.")


def check(data):
    print("SELF-TEST — the raw query misses the relevant doc; expansion retrieves it first")
    print("-" * 62)
    docs, rel = data["docs"], data["relevant"]

    raw_rank = rank_of(data["raw"], docs, rel)
    raw_misses = raw_rank > 1
    print("  the raw query ranks the relevant doc below rank 1 (a miss) = %s (rank %d)" % (raw_misses, raw_rank))

    exp_rank = rank_of(data["expanded"], docs, rel)
    expanded_finds = exp_rank == 1
    print("  the expanded query ranks the relevant doc first = %s (rank %d)" % (expanded_finds, exp_rank))

    rel_vec = next(d["vec"] for d in docs if d["id"] == rel)
    raises = cosine(data["expanded"], rel_vec) > cosine(data["raw"], rel_vec)
    print("  expansion raises similarity to the relevant doc = %s (%.4f -> %.4f)"
          % (raises, cosine(data["raw"], rel_vec), cosine(data["expanded"], rel_vec)))

    # the raw query is fooled: a distractor outscores the relevant doc; expansion reverses that gap
    best_distractor = max((cosine(data["raw"], d["vec"]) for d in docs if d["id"] != rel))
    raw_gap = cosine(data["raw"], rel_vec) - best_distractor
    exp_best_distractor = max((cosine(data["expanded"], d["vec"]) for d in docs if d["id"] != rel))
    exp_gap = cosine(data["expanded"], rel_vec) - exp_best_distractor
    discriminates = raw_gap < 0 < exp_gap
    print("  expansion turns a negative relevance gap positive = %s (raw %.3f, expanded %.3f)"
          % (discriminates, raw_gap, exp_gap))

    ok = raw_misses and expanded_finds and raises and discriminates
    print("-" * 62)
    print("SELF-TEST %s  raw_misses=%s  expanded_finds=%s  raises=%s  discriminates=%s"
          % ("PASS" if ok else "FAIL", raw_misses, expanded_finds, raises, discriminates))
    return ok


def main():
    p = argparse.ArgumentParser(description="Expand a vague query before embedding it.")
    p.add_argument("--query", action="store_true")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  dim=%d  relevant=%s  file=%s  (query and doc vectors are a fixture)"
          % (len(data["docs"]), len(data["raw"]), data["relevant"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.query:
        query_view(data)
    elif args.rank:
        rank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
