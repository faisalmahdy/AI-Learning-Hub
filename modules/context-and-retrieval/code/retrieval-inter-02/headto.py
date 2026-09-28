#!/usr/bin/env python3
"""Wiki vs RAG vs hybrid: the head-to-head the opinion needs.

The labs hold an untested opinion that a compiled wiki (exact, curated lookup)
beats dense RAG (embedding similarity). This runs both on one shared eval set and
settles it with numbers. Two retrievers: LEXICAL, which matches surface words
exactly (a wiki/BM25-style lookup that nails rare tokens like "14c" but is blind
to paraphrase), and DENSE, which maps words to shared concepts (an embedding
stand-in that catches "commute" ~ "drive to work" but is silent on rare tokens it
has no concept for). Neither wins alone. The fix is fusion -- but only if a
retriever with no signal ABSTAINS instead of casting its arbitrary tie-broken
order as real votes, which is the bug that makes a naive fuse worse than either.

  --methods     hit@1 for lexical, dense, the shipped-champion, naive fuse, abstaining fuse
  --split       lexical vs dense by query type (exact-token vs paraphrase)
  --fuse Q      one query, each method's ranking, so you see abstention matter
  --check       neither pure method wins; naive fusion is worse; abstaining fusion wins

The DENSE embedding is a hand-built concept map, a fixture standing in for a
learned model -- the mechanism (surface words -> shared concepts) is what a real
embedding does continuously. Stdlib only (math.sqrt). No network. Deterministic.
"""
import argparse
import json
import re
import sys
from math import sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus.json"

RRF_K = 60      # the textbook reciprocal-rank-fusion constant

STOP = {"the", "a", "an", "to", "of", "on", "in", "is", "are", "my", "i", "do",
        "how", "when", "where", "which", "what", "for", "by", "at", "with", "and",
        "from", "me", "every", "before", "this", "that", "it", "its", "was", "were"}


def load():
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return data["docs"], data["concepts"], data["queries"]


def toks(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def content(text):
    return [t for t in toks(text) if t not in STOP]


# ------------------------------------------------------- the two base retrievers

def lexical_score(query, doc, _concepts):
    """Wiki/BM25-style: how many distinct content words (stopwords removed) the
    query shares with the doc. Nails rare tokens (14c, b4); blind to synonyms."""
    return len(set(content(query)) & set(content(doc)))


def concept_vec(text, concepts):
    """Map surface words to shared concepts; words with no concept are dropped --
    exactly how a rare token becomes invisible to an embedding."""
    v = {}
    for t in toks(text):
        c = concepts.get(t)
        if c:
            v[c] = v.get(c, 0) + 1
    return v


def dense_score(query, doc, concepts):
    """Embedding stand-in: cosine over concept vectors. Catches paraphrase (shared
    concept); scores 0 for every doc when the query is only rare tokens."""
    q, d = concept_vec(query, concepts), concept_vec(doc, concepts)
    dot = sum(w * d.get(c, 0) for c, w in q.items())
    nq = sqrt(sum(w * w for w in q.values()))
    nd = sqrt(sum(w * w for w in d.values()))
    return dot / (nq * nd) if nq and nd else 0.0


def rank(docs, query, score, concepts):
    scored = [(did, score(query, text, concepts)) for did, text in docs.items()]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


def silent(scored):
    """A retriever has no signal on this query when its best score is 0 -- its
    order is then just the alphabetical tie-break, not evidence."""
    return scored[0][1] == 0


def top_if_confident(scored):
    """The top doc, or None if the retriever is silent (all scores 0)."""
    return None if silent(scored) else scored[0][0]


# ------------------------------------------------------------------- the fusions

BASE = [lexical_score, dense_score]


def fuse(docs, query, concepts, abstain):
    """Reciprocal-rank fusion. If abstain is True, a retriever with no signal sits
    the query out; if False (the bug), it votes its arbitrary tie-broken order."""
    fused = {did: 0.0 for did in docs}
    for score in BASE:
        ranked = rank(docs, query, score, concepts)
        if abstain and silent(ranked):
            continue
        for r, (did, _) in enumerate(ranked, 1):
            fused[did] += 1.0 / (RRF_K + r)
    ordered = sorted(fused.items(), key=lambda x: (-x[1], x[0]))
    return ordered


# ---------------------------------------------------------------- the measurement

def overall(docs, queries, concepts, score):
    """hit@1 for one base retriever; a silent retriever misses (no free tie-break)."""
    h = 0
    for item in queries:
        if top_if_confident(rank(docs, item["q"], score, concepts)) == item["gold_doc"]:
            h += 1
    return h


def overall_fused(docs, queries, concepts, abstain):
    h = 0
    for item in queries:
        if fuse(docs, item["q"], concepts, abstain)[0][0] == item["gold_doc"]:
            h += 1
    return h


def by_type(docs, queries, concepts, score, qtype):
    h = n = 0
    for item in queries:
        if item["type"] != qtype:
            continue
        n += 1
        if top_if_confident(rank(docs, item["q"], score, concepts)) == item["gold_doc"]:
            h += 1
    return h, n


def champion_hits(docs, queries, concepts):
    """Ship the single best method for every query -- the 'pick a winner' baseline."""
    return max(overall(docs, queries, concepts, lexical_score),
               overall(docs, queries, concepts, dense_score))


# ------------------------------------------------------------------- printing

def methods_view(docs, concepts, queries):
    n = len(queries)
    print("HEAD-TO-HEAD — hit@1 over the whole eval set")
    print("-" * 62)
    print("  lexical (wiki)          %d/%d" % (overall(docs, queries, concepts, lexical_score), n))
    print("  dense (RAG)             %d/%d" % (overall(docs, queries, concepts, dense_score), n))
    print("  ship the champion       %d/%d  (pick the better single method)" % (champion_hits(docs, queries, concepts), n))
    print("  fuse, no abstention     %d/%d  (the bug: silent method still votes)" % (overall_fused(docs, queries, concepts, False), n))
    print("  fuse, with abstention   %d/%d  (the fix)" % (overall_fused(docs, queries, concepts, True), n))
    print("-" * 62)
    print("  no single method wins; a naive fuse is WORSE than either; only the")
    print("  fuse that lets a silent retriever step aside answers everything.")


def split_view(docs, concepts, queries):
    types = sorted({q["type"] for q in queries})
    print("BY QUERY TYPE — where each pure method actually wins")
    print("-" * 62)
    print("  %-16s %s" % ("method", "  ".join("%-11s" % t for t in types)))
    for label, score in (("lexical (wiki)", lexical_score), ("dense (RAG)", dense_score)):
        cells = ["%d/%d" % by_type(docs, queries, concepts, score, t) for t in types]
        print("  %-16s %s" % (label, "  ".join("%-11s" % c for c in cells)))
    print("-" * 62)
    print("  lexical owns exact tokens, dense owns paraphrase; neither owns both.")
    print("  'wiki beats RAG' is revised: the winner is whatever the query mix is.")


def fuse_view(docs, concepts, query):
    print("ONE QUERY — %r" % query)
    print("-" * 62)
    lex, den = rank(docs, query, lexical_score, concepts), rank(docs, query, dense_score, concepts)
    print("  lexical top      %s%s" % (lex[0], "  (SILENT — all scores 0)" if silent(lex) else ""))
    print("  dense   top      %s%s" % (den[0], "  (SILENT — all scores 0)" if silent(den) else ""))
    print("  fuse no-abstain  -> %s" % fuse(docs, query, concepts, False)[0][0])
    print("  fuse abstain     -> %s" % fuse(docs, query, concepts, True)[0][0])
    print("-" * 62)
    print("  when one retriever is silent, letting it vote drags the fuse to its")
    print("  alphabetical tie-break; abstention hands the query to the one that knows.")


def check(docs, concepts, queries):
    print("SELF-TEST — neither pure method wins; naive fuse is worse; abstaining fuse wins")
    print("-" * 62)
    n = len(queries)
    lex = overall(docs, queries, concepts, lexical_score)
    den = overall(docs, queries, concepts, dense_score)
    champ = champion_hits(docs, queries, concepts)
    naive = overall_fused(docs, queries, concepts, False)
    good = overall_fused(docs, queries, concepts, True)
    print("  hit@1  lexical=%d dense=%d champion=%d naive-fuse=%d abstain-fuse=%d  (of %d)"
          % (lex, den, champ, naive, good, n))

    neither = lex < n and den < n
    print("  neither pure method answers everything = %s" % neither)
    champ_capped = champ == max(lex, den) and champ < n
    print("  the champion is just the best single method, still short of all = %s" % champ_capped)
    naive_worse = naive < champ
    print("  naive fusion is WORSE than shipping the champion = %s (%d < %d)" % (naive_worse, naive, champ))
    fix_wins = good == n and good > naive
    print("  abstaining fusion answers every query = %s (%d/%d)" % (fix_wins, good, n))

    lex_ex, _ = by_type(docs, queries, concepts, lexical_score, "exact")
    den_par, _ = by_type(docs, queries, concepts, dense_score, "paraphrase")
    complementary = lex_ex == 3 and den_par == 3
    print("  lexical wins exact (%d/3), dense wins paraphrase (%d/3) = %s" % (lex_ex, den_par, complementary))

    det = fuse(docs, queries[0]["q"], concepts, True) == fuse(docs, queries[0]["q"], concepts, True)
    ok = neither and champ_capped and naive_worse and fix_wins and complementary and det
    print("-" * 62)
    print("SELF-TEST %s  neither=%s  champ_capped=%s  naive_worse=%s  fix_wins=%s  complementary=%s"
          % ("PASS" if ok else "FAIL", neither, champ_capped, naive_worse, fix_wins, complementary))
    return ok


def main():
    p = argparse.ArgumentParser(description="Wiki vs RAG vs hybrid, measured.")
    p.add_argument("--methods", action="store_true")
    p.add_argument("--split", action="store_true")
    p.add_argument("--fuse", metavar="Q")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    docs, concepts, queries = load()
    print("docs=%d  concepts=%d  queries=%d  file=%s  (corpus + concept map are a fixture)"
          % (len(docs), len(set(concepts.values())), len(queries), CORPUS.name))
    print("")

    if args.check:
        return 0 if check(docs, concepts, queries) else 1
    if args.methods:
        methods_view(docs, concepts, queries)
    elif args.split:
        split_view(docs, concepts, queries)
    elif args.fuse:
        fuse_view(docs, concepts, args.fuse)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
