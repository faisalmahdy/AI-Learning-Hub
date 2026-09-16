"""Cut chunks at topic boundaries, not at a fixed length -- or a short topic is diluted and split across two chunks.

A retriever indexes chunks, and each chunk is embedded as one vector -- roughly the average of its sentences. Chop a
document into fixed-length chunks and that average is only meaningful when a chunk holds one topic. It rarely does: real
documents change subject at moments that have nothing to do with your chunk size, so a fixed cut lands in the middle of
a topic and a fixed chunk straddles a boundary, mixing two subjects into one vector that points between them and
matches neither well. The damage is worst for a SHORT topic -- a two-sentence aside, a single definition -- which a
fixed grid can slice so that its sentences fall into different chunks, each dominated by the surrounding topic, so no
chunk represents the short topic and a query about it retrieves a diluted average instead.

Semantic chunking cuts where the document actually changes subject. Walk the sentences in order, measure the cosine
similarity between each adjacent pair, and start a new chunk wherever that similarity drops below a threshold -- a drop
means the next sentence is about something else. Now every chunk is internally coherent: one topic, one clean centroid,
and the short topic gets its own chunk instead of being smeared across two. The retriever is unchanged; only the chunk
boundaries moved, from a fixed grid to the document's own seams. A query about the short topic now finds a chunk whose
vector actually points at it.

On this fixture the document is topic A (3 sentences), a short topic B (2 sentences), then A again (3). Fixed chunks of
4 put B's two sentences into two different A-heavy chunks, whose centroids sit at [0.75, 0.25] and match a B query at
only 0.32. Semantic chunking splits at the two similarity drops, giving a pure B chunk whose centroid is [0, 1] and
matches the B query at 1.00. This computes both.

  --chunk     the fixed-size chunks and the semantic chunks, with each chunk's topic makeup and whether it is pure
  --retrieve  a query about the short topic B, and the best chunk cosine it gets under fixed vs semantic chunking
  --check     fixed chunking mixes topics and buries B; semantic chunking cuts at the drops and gives B a pure chunk

The sentences, chunk size, threshold, and query are the fixture; every cosine and centroid is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "semchunk.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cosine(u, v):
    """Cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    return dot / (nu * nv) if nu and nv else 0.0


def centroid(vecs):
    """The mean vector of a chunk -- what the retriever embeds and indexes for it."""
    dim = len(vecs[0])
    return [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]


def fixed_chunks(sentences, size):
    """Group sentences into consecutive chunks of `size`, ignoring meaning."""
    return [list(range(i, min(i + size, len(sentences)))) for i in range(0, len(sentences), size)]


def semantic_chunks(sentences, threshold):
    """Start a new chunk wherever adjacent-sentence similarity drops below `threshold` (a topic boundary)."""
    chunks, cur = [], [0]
    for i in range(1, len(sentences)):
        if cosine(sentences[i - 1]["vec"], sentences[i]["vec"]) < threshold:
            chunks.append(cur)
            cur = [i]
        else:
            cur.append(i)
    chunks.append(cur)
    return chunks


def chunk_topics(chunk, sentences):
    """The multiset of topics in a chunk, for judging purity."""
    return [sentences[i]["topic"] for i in chunk]


def best_chunk_score(chunks, sentences, query_vec):
    """The highest cosine between the query and any chunk's centroid -- what the retriever would return."""
    return max(cosine(query_vec, centroid([sentences[i]["vec"] for i in c])) for c in chunks)


# ----------------------------------------------------------------- printing

def chunk_view(data):
    s = data["sentences"]
    print("CHUNK — fixed-size grid vs cutting at similarity drops")
    print("-" * 60)
    print("  adjacent cosine:  %s" % ["%.2f" % cosine(s[i - 1]["vec"], s[i]["vec"]) for i in range(1, len(s))])
    print("")
    for name, chunks in (("fixed", fixed_chunks(s, data["fixed_size"])), ("semantic", semantic_chunks(s, data["split_threshold"]))):
        print("  %-9s chunks:" % name)
        for c in chunks:
            topics = chunk_topics(c, s)
            pure = "pure" if len(set(topics)) == 1 else "MIXED"
            print("    idx %-10s topics %-12s %s" % (str(c), "".join(topics), pure))
    print("-" * 60)
    print("  the fixed grid slices the short B topic across two A-heavy chunks; semantic keeps B whole.")


def retrieve_view(data):
    s = data["sentences"]
    q = data["query"]
    fixed = fixed_chunks(s, data["fixed_size"])
    sem = semantic_chunks(s, data["split_threshold"])
    print("RETRIEVE — a query about topic %s, best chunk cosine under each chunking" % q["about"])
    print("-" * 60)
    print("  fixed chunking:    best chunk cosine = %.2f" % best_chunk_score(fixed, s, q["vec"]))
    print("  semantic chunking: best chunk cosine = %.2f" % best_chunk_score(sem, s, q["vec"]))
    print("-" * 60)
    print("  fixed returns a diluted A+B average; semantic returns a chunk whose vector actually points at B.")


def check(data):
    print("SELF-TEST — fixed chunking mixes topics and buries B; semantic chunking cuts at the drops and gives B a pure chunk")
    print("-" * 116)
    s, q = data["sentences"], data["query"]
    fixed = fixed_chunks(s, data["fixed_size"])
    sem = semantic_chunks(s, data["split_threshold"])

    fixed_has_mixed = any(len(set(chunk_topics(c, s))) > 1 for c in fixed)
    print("  fixed chunking produces at least one mixed-topic chunk = %s" % fixed_has_mixed)

    semantic_all_pure = all(len(set(chunk_topics(c, s))) == 1 for c in sem)
    print("  semantic chunking produces only pure chunks = %s (%s)" % (semantic_all_pure, ["".join(chunk_topics(c, s)) for c in sem]))

    b_indices = [i for i, sent in enumerate(s) if sent["topic"] == q["about"]]
    b_split_in_fixed = len({next(k for k, c in enumerate(fixed) if i in c) for i in b_indices}) > 1
    print("  the short %s topic is split across chunks by fixed chunking = %s" % (q["about"], b_split_in_fixed))

    b_whole_in_semantic = any(set(b_indices) == set(c) for c in sem)
    print("  semantic chunking puts the whole %s topic in one chunk = %s" % (q["about"], b_whole_in_semantic))

    fx, sx = best_chunk_score(fixed, s, q["vec"]), best_chunk_score(sem, s, q["vec"])
    semantic_retrieves_better = sx > fx
    print("  the %s query matches a chunk better under semantic chunking = %s (%.2f > %.2f)" % (q["about"], semantic_retrieves_better, sx, fx))

    ok = fixed_has_mixed and semantic_all_pure and b_split_in_fixed and b_whole_in_semantic and semantic_retrieves_better
    print("-" * 116)
    print("SELF-TEST %s  fixed_has_mixed=%s  semantic_all_pure=%s  b_split_in_fixed=%s  b_whole_in_semantic=%s  semantic_retrieves_better=%s"
          % ("PASS" if ok else "FAIL", fixed_has_mixed, semantic_all_pure, b_split_in_fixed, b_whole_in_semantic, semantic_retrieves_better))
    return ok


def main():
    p = argparse.ArgumentParser(description="Semantic chunking: cut chunks where adjacent-sentence similarity drops (topic boundaries), not at a fixed length, so a short topic is not diluted and split across chunks.")
    p.add_argument("--chunk", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("sentences=%d  fixed_size=%d  split_threshold=%.2f  query_about=%s  file=%s  (the document is a fixture)"
          % (len(data["sentences"]), data["fixed_size"], data["split_threshold"], data["query"]["about"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.chunk:
        chunk_view(data)
    elif args.retrieve:
        retrieve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
