"""Prepend each chunk's document context before embedding, or a chunk that lost its subject won't match the query.

Chunking splits a document into pieces small enough to retrieve, but a piece torn from its document loses
the context that named its subject. A chunk that says 'revenue rose 20 percent in the quarter' never
repeats which company or which year -- the surrounding document said that. So a query naming the company
and the year barely matches the chunk on its own words, and a different chunk that happens to mention the
company and year, even about something irrelevant, outscores it. The right chunk is there; the retriever
just can't see it is the right one, because the words that would connect it to the query were left behind
in the document.

Contextual augmentation fixes it: before embedding each chunk, prepend a short blurb describing its source
-- the document title, the subject, the date. Now the chunk carries the entity and year terms it was
relying on the document for, and the query matches it. The blurb is added to every chunk fairly, so the
comparison is honest; it just restores to each chunk the context it lost when it was cut out.

On this fixture a query for 'acme 2023 revenue' meets two chunks. Bare, the right chunk (about revenue but
not naming acme or 2023) scores 0.218 while a wrong chunk (acme opened an office in 2023) scores 0.436, so
bare retrieval returns the wrong one. Augment every chunk with its document context and the right chunk
rises to 0.500, above the wrong chunk's 0.480 -- the retrieval flips to the correct answer. This computes
both.

  --chunks     the query, each chunk's bare text, and its document context
  --retrieve   the similarity of each chunk to the query, bare vs context-augmented, and the top result
  --check      bare retrieval returns the wrong chunk; augmenting with context returns the right one

The query, chunks, and contexts are the fixture; every similarity is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "chunks.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def vec(text):
    """Bag-of-words term vector -- a stand-in for an embedding, so the matching is visible."""
    d = {}
    for w in text.lower().split():
        d[w] = d.get(w, 0) + 1
    return d


def cosine(a, b):
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return round(dot / (na * nb), 4) if na and nb else 0.0


def bare_sim(query, chunk):
    """Similarity of the query to the chunk's bare text alone."""
    return cosine(vec(query), vec(chunk["bare"]))


def augmented_sim(query, chunk):
    """Similarity of the query to the chunk with its document context prepended."""
    return cosine(vec(query), vec(chunk["context"] + " " + chunk["bare"]))


def top(query, chunks, sim):
    """The id of the highest-scoring chunk under the given similarity function."""
    return max(chunks, key=lambda cid: sim(query, chunks[cid]))


def answer_id(chunks):
    return next(cid for cid, c in chunks.items() if c["answer"])


# ----------------------------------------------------------------- printing

def chunks_view(data):
    print("CHUNKS — query: %r" % data["query"])
    print("-" * 58)
    for cid, c in data["chunks"].items():
        tag = " (the true answer)" if c["answer"] else ""
        print("  %s%s" % (cid, tag))
        print("    bare:    %s" % c["bare"])
        print("    context: %s" % c["context"])
    print("-" * 58)
    print("  the answer chunk never names acme or 2023 in its bare text.")


def retrieve_view(data):
    q, chunks = data["query"], data["chunks"]
    print("RETRIEVE — similarity to the query, bare vs context-augmented")
    print("-" * 58)
    print("  chunk    bare     augmented")
    for cid, c in chunks.items():
        print("  %-6s   %.3f    %.3f" % (cid, bare_sim(q, c), augmented_sim(q, c)))
    print("-" * 58)
    print("  bare top: %s   augmented top: %s   (answer: %s)"
          % (top(q, chunks, bare_sim), top(q, chunks, augmented_sim), answer_id(chunks)))


def check(data):
    print("SELF-TEST — bare retrieval returns the wrong chunk; augmenting with context returns the right one")
    print("-" * 90)
    q, chunks = data["query"], data["chunks"]
    ans = answer_id(chunks)

    bare_wrong = top(q, chunks, bare_sim) != ans
    print("  bare retrieval's top chunk is NOT the answer = %s (top %s, answer %s)"
          % (bare_wrong, top(q, chunks, bare_sim), ans))

    augmented_right = top(q, chunks, augmented_sim) == ans
    print("  augmented retrieval's top chunk IS the answer = %s (top %s)" % (augmented_right, top(q, chunks, augmented_sim)))

    augment_lifts_answer = augmented_sim(q, chunks[ans]) > bare_sim(q, chunks[ans])
    print("  augmentation lifts the answer chunk's score = %s (%.3f -> %.3f)"
          % (augment_lifts_answer, bare_sim(q, chunks[ans]), augmented_sim(q, chunks[ans])))

    # the answer chunk's bare text is missing query terms that its context supplies
    q_terms = set(vec(q))
    missing = q_terms - set(vec(chunks[ans]["bare"]))
    supplied = missing & set(vec(chunks[ans]["context"]))
    context_supplies_terms = len(supplied) > 0
    print("  the context supplies query terms the bare chunk lacked = %s (%s)" % (context_supplies_terms, sorted(supplied)))

    ok = bare_wrong and augmented_right and augment_lifts_answer and context_supplies_terms
    print("-" * 90)
    print("SELF-TEST %s  bare_wrong=%s  augmented_right=%s  augment_lifts_answer=%s  context_supplies_terms=%s"
          % ("PASS" if ok else "FAIL", bare_wrong, augmented_right, augment_lifts_answer, context_supplies_terms))
    return ok


def main():
    p = argparse.ArgumentParser(description="Prepend each chunk's document context before embedding.")
    p.add_argument("--chunks", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%r  chunks=%d  file=%s  (the chunks are a fixture)"
          % (data["query"], len(data["chunks"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.chunks:
        chunks_view(data)
    elif args.retrieve:
        retrieve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
