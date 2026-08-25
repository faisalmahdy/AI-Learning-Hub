#!/usr/bin/env python3
"""Chunk size trades recall for precision -- and no-overlap chunking throws recall away.

Retrieval indexes *units*. Index whole documents and the right answer is a needle
in a long unit you must inject whole; index tiny windows and a single fact gets
split across a boundary so no unit contains it. This chunks the same corpus four
ways, retrieves the single best chunk per query with length-fair cosine, and
measures two things at once: answer recall@1 (did the top chunk contain the whole
gold fact?) and the tokens that chunk injects (the cost). The sweet spot is a
middle chunk size WITH overlap; the trap is a small chunk size with none.

  --index SIZE STRIDE   show how one chunker splits the corpus (SIZE tokens, STRIDE step)
  --ablate              recall@1 and injected tokens for whole / big / small-noverlap / small-overlap
  --miss                the two queries a no-overlap chunker splits, and where the boundary falls
  --check               overlap recovers every split the no-overlap chunker drops; seeds

Reuses the cosine retriever from retrieval-basic-01 (length normalisation matters
here too). Stdlib only (math.sqrt). No network, no model. The corpus is a fixture.
"""
import argparse
import json
import re
import sys
from math import sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "docs.json"


def load():
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return data["docs"], data["queries"]


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def tf(toks):
    v = {}
    for t in toks:
        v[t] = v.get(t, 0) + 1
    return v


def cosine(q_vec, d_vec):
    dot = sum(w * d_vec.get(t, 0) for t, w in q_vec.items())
    nq = sqrt(sum(w * w for w in q_vec.values()))
    nd = sqrt(sum(w * w for w in d_vec.values()))
    return dot / (nq * nd) if nq and nd else 0.0


# --------------------------------------------------------------- the chunkers

def chunks_of(text, size, stride):
    """Windows of `size` tokens stepping by `stride`. stride==size means no
    overlap (windows abut); stride<size means the windows overlap by size-stride.
    size==0 is the whole document as a single chunk."""
    toks = tokens(text)
    if size == 0 or size >= len(toks):
        return [toks]
    out = []
    i = 0
    while i < len(toks):
        out.append(toks[i:i + size])
        if i + size >= len(toks):
            break
        i += stride
    return out


def build_index(docs, size, stride):
    """One flat list of (doc_id, chunk_index, chunk_tokens) across the corpus."""
    idx = []
    for did, text in docs.items():
        for ci, ch in enumerate(chunks_of(text, size, stride)):
            idx.append((did, ci, ch))
    return idx


def top_chunk(index, query):
    q_vec = tf(tokens(query))
    scored = [((did, ci, ch), cosine(q_vec, tf(ch))) for (did, ci, ch) in index]
    scored.sort(key=lambda x: (-x[1], x[0][0], x[0][1]))
    return scored[0][0]        # (doc_id, chunk_index, chunk_tokens)


# ---------------------------------------------------------------- the metrics

def covers(chunk_toks, gold_toks):
    """A chunk answers the query only if it holds every token of the gold fact."""
    s = set(chunk_toks)
    return all(t in s for t in gold_toks)


def evaluate(docs, queries, size, stride):
    hits = 0
    injected = []
    for item in queries:
        did, ci, ch = top_chunk(build_index(docs, size, stride), item["q"])
        injected.append(len(ch))
        if did == item["gold_doc"] and covers(ch, item["gold"]):
            hits += 1
    return hits, sum(injected) / len(injected)


# ------------------------------------------------------------------- printing

CONFIGS = [
    ("whole document", 0, 0),
    ("24-token, overlap 6", 24, 18),
    ("12-token, no overlap", 12, 12),
    ("12-token, overlap 6", 12, 6),
]


def ablate(docs, queries):
    n = len(queries)
    print("CHUNK ABLATION — recall@1 (top chunk holds the whole fact) and cost")
    print("-" * 68)
    print("  chunker                recall@1   avg tokens injected")
    for label, size, stride in CONFIGS:
        hits, avg = evaluate(docs, queries, size, stride)
        print("  %-22s  %d/%d        %5.1f" % (label, hits, n, avg))
    print("-" * 68)
    print("  whole-doc recall is high but injects a whole document; the 12-token")
    print("  no-overlap chunker is cheap but SPLITS facts; 12-token overlap 6 buys")
    print("  the recall back at the same cost. Size trades recall for precision.")


def index_view(docs, size, stride):
    idx = build_index(docs, size, stride)
    print("INDEX — %d-token chunks, stride %d (%s)"
          % (size, stride, "no overlap" if stride == size else "overlap %d" % (size - stride)))
    print("-" * 68)
    for did in docs:
        chs = chunks_of(docs[did], size, stride)
        print("  %s -> %d chunk(s)" % (did, len(chs)))
    print("-" * 68)
    print("  %d chunks total across %d docs." % (len(idx), len(docs)))


def miss(docs, queries):
    print("THE SPLIT — where a 12-token no-overlap boundary cuts a fact in half")
    print("-" * 68)
    for item in queries:
        did, ci, ch = top_chunk(build_index(docs, 12, 12), item["q"])
        ok = did == item["gold_doc"] and covers(ch, item["gold"])
        if not ok:
            gold_doc_toks = tokens(docs[item["gold_doc"]])
            pos = [i for i, t in enumerate(gold_doc_toks) if t in item["gold"]]
            print("  %-34s gold %s at token positions %s"
                  % (item["q"][:34], item["gold"], pos))
            print("       -> a boundary at 12/24/... falls between them; no 12-token")
            print("          window holds both, so the top chunk cannot answer.")
    print("-" * 68)
    print("  the fact was in the corpus the whole time; the chunker hid it.")


def check(docs, queries):
    print("SELF-TEST — overlap recovers every split; recall is monotone in the fix")
    print("-" * 68)

    whole_hits, _ = evaluate(docs, queries, 0, 0)
    noov_hits, _ = evaluate(docs, queries, 12, 12)
    ov_hits, ov_cost = evaluate(docs, queries, 12, 6)
    big_hits, _ = evaluate(docs, queries, 24, 18)
    n = len(queries)
    print("  recall@1: whole=%d/%d  12-noverlap=%d/%d  12-overlap=%d/%d  24-overlap=%d/%d"
          % (whole_hits, n, noov_hits, n, ov_hits, n, big_hits, n))

    # the bug: the no-overlap chunker drops recall the overlap chunker keeps.
    split_shows = noov_hits < ov_hits
    print("  no-overlap loses recall the overlap chunker keeps = %s (%d < %d)"
          % (split_shows, noov_hits, ov_hits))

    # overlap matches-or-beats whole-doc recall at a fraction of the injected tokens.
    _, whole_cost = evaluate(docs, queries, 0, 0)
    recovers = ov_hits >= whole_hits
    cheaper = ov_cost < whole_cost
    print("  12-overlap recall >= whole-doc recall = %s (%d >= %d), and cheaper = %s (%.1f < %.1f tok)"
          % (recovers, ov_hits, whole_hits, cheaper, ov_cost, whole_cost))

    # every gold fact exists inside some 12-overlap chunk (recall ceiling is real).
    reachable = 0
    for item in queries:
        idx = build_index(docs, 12, 6)
        if any(c[0] == item["gold_doc"] and covers(c[2], item["gold"]) for c in idx):
            reachable += 1
    all_reachable = reachable == n
    print("  every gold fact lives whole inside some 12-overlap chunk = %s (%d/%d)"
          % (all_reachable, reachable, n))

    det = top_chunk(build_index(docs, 12, 6), queries[0]["q"]) == \
        top_chunk(build_index(docs, 12, 6), queries[0]["q"])

    ok = split_shows and recovers and cheaper and all_reachable and det
    print("-" * 68)
    print("SELF-TEST %s  split_shows=%s  recovers=%s  cheaper=%s  reachable=%s  det=%s"
          % ("PASS" if ok else "FAIL", split_shows, recovers, cheaper, all_reachable, det))
    return ok


def main():
    p = argparse.ArgumentParser(description="Ablate chunk size against recall and cost.")
    p.add_argument("--index", nargs=2, type=int, metavar=("SIZE", "STRIDE"))
    p.add_argument("--ablate", action="store_true")
    p.add_argument("--miss", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    docs, queries = load()
    print("docs=%d  queries=%d  file=%s  (corpus is a fixture)" % (len(docs), len(queries), CORPUS.name))
    print("")

    if args.check:
        return 0 if check(docs, queries) else 1
    if args.index:
        index_view(docs, args.index[0], args.index[1])
    elif args.ablate:
        ablate(docs, queries)
    elif args.miss:
        miss(docs, queries)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
