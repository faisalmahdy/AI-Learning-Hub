"""Size chunks to fit the embedding model's maximum token length -- a chunk longer than the limit is silently truncated, so its tail is never embedded and cannot be retrieved.

Every embedding model has a maximum input length, measured in tokens: many sentence-transformer models cap at 512, some at 256, newer long-context ones at several thousand. The number is a hard limit of the model, and the important thing about it is what happens when you exceed it. The model does not raise an error and it does not embed the whole input at reduced fidelity. It truncates: it keeps the first max_len tokens, discards everything after, and embeds only what remains.

For a chunk longer than the limit, this means the embedding represents only the chunk's beginning. Any fact that lives past the cutoff -- the specific answer buried two-thirds of the way through a long passage -- contributes nothing to the vector, because the tokens carrying it were dropped before the model ever saw them. A query that should match that fact finds no signal for it in the chunk's embedding, so the chunk is not retrieved, even though the text is sitting right there in the stored chunk, perfectly readable. The retrieval fails not because the content is missing from the corpus but because it is missing from the vector.

What makes this dangerous is that it is completely silent. No exception, no warning; the embedding is produced and looks normal, the pipeline runs, and the tail of every over-long chunk is simply invisible to search. It can pass every test that happens to query content near the start of chunks and fail only on queries about their ends. The fix is to chunk so each piece fits under the model's max length, and to measure that length in the model's own tokens -- not characters or words, which undercount, since a "word" can be several tokens and a 500-word chunk can blow past a 512-token limit. Where long chunks are genuinely needed, use a long-context embedding model whose limit is large enough.

The rule: size chunks to the embedding model's maximum token length, because the model silently truncates longer input and embeds only the first max_len tokens -- so content in a longer chunk's tail is absent from the vector and unretrievable; split to fit, measuring length in the model's tokens.

On this fixture the chunk is 9 tokens but the model's limit is 5, so truncation keeps only the first 5 and drops the tail that contains the query term 'answer'; the long chunk's embedding cannot match the query, while splitting into max_len-sized chunks puts 'answer' inside a chunk's limit and restores retrieval. This computes both.

  --embed    the terms the truncated embedding of the long chunk actually contains
  --retrieve  whether the query term is retrievable from the long chunk vs from max_len-sized splits
  --check     truncation drops the long chunk's tail so the query misses; splitting to fit recovers it

chunk, max_len, and query_term are the fixture; the truncated terms and retrieval outcomes are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "embtrunc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def embed(tokens, max_len):
    """The model truncates to its max length: only the first max_len tokens are embedded."""
    return set(tokens[:max_len])


def split_to_fit(tokens, max_len):
    """Chunk so each piece is at most max_len tokens."""
    return [tokens[i:i + max_len] for i in range(0, len(tokens), max_len)]


def retrievable(term, chunks, max_len):
    """The term is retrievable if it survives in some chunk's truncated embedding."""
    return any(term in embed(c, max_len) for c in chunks)


# ----------------------------------------------------------------- printing

def embed_view(data):
    chunk, max_len = data["chunk"], data["max_len"]
    print("EMBED — what the truncated embedding of the long chunk contains (max_len=%d)" % max_len)
    print("-" * 60)
    print("  chunk tokens (%d): %s" % (len(chunk), chunk))
    print("  embedded (first %d): %s" % (max_len, chunk[:max_len]))
    print("  dropped tail:       %s" % chunk[max_len:])
    print("-" * 60)
    print("  the tail past token %d is discarded before the model embeds anything" % max_len)


def retrieve_view(data):
    chunk, max_len, term = data["chunk"], data["max_len"], data["query_term"]
    long_ok = retrievable(term, [chunk], max_len)
    split_ok = retrievable(term, split_to_fit(chunk, max_len), max_len)
    print("RETRIEVE — is the query term %r retrievable?" % term)
    print("-" * 56)
    print("  from the long (truncated) chunk = %s" % long_ok)
    print("  from max_len-sized splits       = %s (%s)" % (split_ok, split_to_fit(chunk, max_len)))
    print("-" * 56)
    print("  the term is in the chunk's text but not in its embedding until the chunk fits")


def check(data):
    print("SELF-TEST — truncation drops the long chunk's tail so the query misses; splitting to fit recovers it")
    print("-" * 114)
    chunk, max_len, term = data["chunk"], data["max_len"], data["query_term"]
    splits = split_to_fit(chunk, max_len)

    chunk_exceeds_maxlen = len(chunk) > max_len
    print("  the chunk is longer than the model's max length = %s (%d > %d)" % (chunk_exceeds_maxlen, len(chunk), max_len))

    term_in_text = term in chunk
    print("  the query term is present in the chunk's text = %s" % term_in_text)

    term_in_dropped_tail = term in chunk[max_len:]
    print("  the query term is in the dropped tail (past max_len) = %s" % term_in_dropped_tail)

    long_chunk_misses = not retrievable(term, [chunk], max_len)
    print("  the term is NOT retrievable from the truncated long chunk = %s" % long_chunk_misses)

    splitting_recovers = retrievable(term, splits, max_len)
    print("  splitting into max_len-sized chunks makes it retrievable = %s" % splitting_recovers)

    ok = (chunk_exceeds_maxlen and term_in_text and term_in_dropped_tail
          and long_chunk_misses and splitting_recovers)
    print("-" * 114)
    print("SELF-TEST %s  chunk_exceeds_maxlen=%s  term_in_text=%s  term_in_dropped_tail=%s  long_chunk_misses=%s  splitting_recovers=%s"
          % ("PASS" if ok else "FAIL", chunk_exceeds_maxlen, term_in_text, term_in_dropped_tail, long_chunk_misses, splitting_recovers))
    return ok


def main():
    p = argparse.ArgumentParser(description="Embedding truncation: size chunks to the embedding model's maximum token length, because the model silently truncates longer input and embeds only the first max_len tokens -- so content in a longer chunk's tail is absent from the vector and unretrievable; split to fit, measuring length in the model's tokens.")
    p.add_argument("--embed", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("chunk=%d tokens  max_len=%d  query_term=%r  file=%s  (all fixture)"
          % (len(data["chunk"]), data["max_len"], data["query_term"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.embed:
        embed_view(data)
    elif args.retrieve:
        retrieve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
