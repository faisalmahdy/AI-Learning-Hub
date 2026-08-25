#!/usr/bin/env python3
"""Relevance, recency, importance: the three-signal memory ranker, and its scale bug.

A memory that changes over time cannot rank on relevance alone: an old note and
the note that superseded it match a query equally, so relevance serves the stale
one. The labs' wiki ranker blends three signals -- relevance (cosine), recency
(exponential decay on age), importance (backlinks, normalised by the busiest
page) -- weighted 0.6 / 0.2 / 0.2. Each signal fixes a failure the others cause,
and one line decides whether the blend works: importance MUST be normalised, or a
hub page that everything links to drowns every query in the index page.

  --signals Q   the three raw signals for each doc on one query
  --rank Q      four rankers on one query: relevance-only, +recency, +raw-imp, +norm-imp
  --measure     fresh-answer accuracy for all four rankers over the eval set
  --check       relevance is stale; recency fixes it; raw importance breaks it; norm fixes it

Mirrors faisalmahdy/agent memory/retrieval.py: recency = 0.5**(age/half_life),
importance = backlinks / max_back, score = wr*rel + wc*rec + wi*imp. Stdlib only
(math). No network, no model. The corpus (text, age, backlinks) is a fixture.
"""
import argparse
import json
import re
import sys
from math import sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "memory.json"

HALF_LIFE = 30.0                 # days; recency halves every 30 days of age
W_REL, W_REC, W_IMP = 0.6, 0.2, 0.2      # the labs' default blend weights


def load():
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    return data["docs"], data["queries"]


def toks(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def tf(text):
    v = {}
    for t in toks(text):
        v[t] = v.get(t, 0) + 1
    return v


def cosine(a, b):
    va, vb = tf(a), tf(b)
    dot = sum(w * vb.get(t, 0) for t, w in va.items())
    na = sqrt(sum(w * w for w in va.values()))
    nb = sqrt(sum(w * w for w in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


# ------------------------------------------------------------------ the signals

def relevance(query, doc):
    return cosine(query, doc["text"])


def recency(doc):
    """Exponential decay on age: a doc edited today scores 1, one a half-life old
    scores 0.5. Fresh memory outweighs stale, smoothly."""
    return 0.5 ** (doc["age_days"] / HALF_LIFE)


def importance_norm(doc, max_back):
    """Backlinks normalised by the busiest page -> [0,1]. A hub is important but
    cannot outweigh everything."""
    return doc["backlinks"] / max_back if max_back else 0.0


def importance_raw(doc, _max_back):
    """THE BUG: raw backlink count, unnormalised. A hub with 20 links contributes
    20 to a sum whose other terms are at most 1."""
    return float(doc["backlinks"])


# ------------------------------------------------------------------ the rankers

def score_doc(query, doc, max_back, use_recency, use_importance, imp_fn):
    s = W_REL * relevance(query, doc) if (use_recency or use_importance) else relevance(query, doc)
    if use_recency:
        s += W_REC * recency(doc)
    if use_importance:
        s += W_IMP * imp_fn(doc, max_back)
    return s


def rank(docs, query, use_recency, use_importance, imp_fn=importance_norm):
    max_back = max((d["backlinks"] for d in docs.values()), default=1) or 1
    scored = [(did, score_doc(query, d, max_back, use_recency, use_importance, imp_fn))
              for did, d in docs.items()]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


RANKERS = [
    ("relevance only", dict(use_recency=False, use_importance=False)),
    ("+ recency", dict(use_recency=True, use_importance=False)),
    ("+ raw importance (bug)", dict(use_recency=True, use_importance=True, imp_fn=importance_raw)),
    ("+ norm importance (fix)", dict(use_recency=True, use_importance=True, imp_fn=importance_norm)),
]


# ---------------------------------------------------------------- measurement

def fresh_accuracy(docs, queries, kw):
    hits = 0
    for item in queries:
        top = rank(docs, item["q"], **kw)[0][0]
        hits += 1 if top == item["gold_fresh"] else 0
    return hits


# ------------------------------------------------------------------- printing

def signals_view(docs, queries, q):
    item = next(i for i in queries if i["q"] == q)
    max_back = max(d["backlinks"] for d in docs.values())
    print("SIGNALS — %r   (gold fresh answer = %s)" % (q, item["gold_fresh"]))
    print("-" * 70)
    print("  doc            relevance  recency  imp(norm)  age(d)  backlinks")
    for did, d in sorted(docs.items(), key=lambda x: -relevance(item["q"], x[1])):
        print("  %-13s  %.3f      %.3f    %.3f      %4d    %d"
              % (did, relevance(item["q"], d), recency(d), importance_norm(d, max_back),
                 d["age_days"], d["backlinks"]))
    print("-" * 70)
    print("  relevance can't split the old note from the fresh one; recency can.")


def rank_view(docs, queries, q):
    item = next(i for i in queries if i["q"] == q)
    print("RANKERS — %r   (gold fresh = %s)" % (q, item["gold_fresh"]))
    print("-" * 70)
    for label, kw in RANKERS:
        top = rank(docs, item["q"], **kw)[0][0]
        mark = "  ok" if top == item["gold_fresh"] else "  <-- wrong"
        print("  %-26s top = %-13s%s" % (label, top, mark))
    print("-" * 70)


def measure(docs, queries):
    n = len(queries)
    print("FRESH-ANSWER ACCURACY — top result is the current, correct note")
    print("-" * 70)
    for label, kw in RANKERS:
        print("  %-26s %d/%d" % (label, fresh_accuracy(docs, queries, kw), n))
    print("-" * 70)
    print("  relevance alone serves stale notes; recency fixes that; raw importance")
    print("  lets the hub page win everything; normalised importance is the real blend.")


def check(docs, queries):
    print("SELF-TEST — each signal fixes what the previous one breaks")
    print("-" * 70)
    n = len(queries)
    rel = fresh_accuracy(docs, queries, RANKERS[0][1])
    rec = fresh_accuracy(docs, queries, RANKERS[1][1])
    raw = fresh_accuracy(docs, queries, RANKERS[2][1])
    norm = fresh_accuracy(docs, queries, RANKERS[3][1])
    print("  accuracy  relevance=%d/%d  +recency=%d/%d  +raw-imp=%d/%d  +norm-imp=%d/%d"
          % (rel, n, rec, n, raw, n, norm, n))

    stale = rel < n
    print("  relevance alone serves at least one stale note = %s (%d < %d)" % (stale, rel, n))
    recency_helps = rec > rel
    print("  adding recency recovers the fresh note = %s (%d > %d)" % (recency_helps, rec, rel))
    raw_breaks = raw < rec
    print("  raw (unnormalised) importance breaks it = %s (%d < %d)" % (raw_breaks, raw, rec))
    norm_fixes = norm >= rec and norm == n
    print("  normalised importance restores full accuracy = %s (%d/%d)" % (norm_fixes, norm, n))

    # the mechanism: under raw importance the hub outranks a fresh, relevant note.
    hub = max(docs, key=lambda d: docs[d]["backlinks"])
    q0 = queries[0]["q"]
    raw_top = rank(docs, q0, use_recency=True, use_importance=True, imp_fn=importance_raw)[0][0]
    hub_wins = raw_top == hub
    print("  under raw importance the hub %r wins query 1 = %s" % (hub, hub_wins))

    det = rank(docs, q0, use_recency=True, use_importance=True) == \
        rank(docs, q0, use_recency=True, use_importance=True)
    ok = stale and recency_helps and raw_breaks and norm_fixes and hub_wins and det
    print("-" * 70)
    print("SELF-TEST %s  stale=%s  recency=%s  raw_breaks=%s  norm_fixes=%s  hub_wins=%s"
          % ("PASS" if ok else "FAIL", stale, recency_helps, raw_breaks, norm_fixes, hub_wins))
    return ok


def main():
    p = argparse.ArgumentParser(description="Blend relevance, recency, and importance.")
    p.add_argument("--signals", metavar="Q")
    p.add_argument("--rank", metavar="Q")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    docs, queries = load()
    print("docs=%d  queries=%d  half_life=%.0fd  weights=%.1f/%.1f/%.1f  file=%s  (fixture)"
          % (len(docs), len(queries), HALF_LIFE, W_REL, W_REC, W_IMP, CORPUS.name))
    print("")

    if args.check:
        return 0 if check(docs, queries) else 1
    if args.signals:
        signals_view(docs, queries, args.signals)
    elif args.rank:
        rank_view(docs, queries, args.rank)
    elif args.measure:
        measure(docs, queries)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
