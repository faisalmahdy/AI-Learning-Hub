"""Embed the query and the whole corpus with ONE model version -- or a stale vector from another model scores as noise.

A vector index works because similar meanings become nearby vectors, so the query's vector and a relevant document's
vector have high cosine. That guarantee holds only within a single embedding model. Different models -- or two versions
of the same model -- map meaning into different vector spaces, so the SAME text gets a different vector under v1 than
under v2, and a v1 vector and a v2 vector are simply not comparable: their cosine is not a similarity, it is noise. This
is invisible until you upgrade the model. You embed new documents and new queries with v2, but the old documents in the
index are still v1, and now a v2 query is being compared against a mix of v2 vectors (meaningful) and v1 vectors
(meaningless). The relevant old document scores as if it were random, while some irrelevant old document can land close
to the query by pure coordinate coincidence and rank first.

The rule is that an index must be HOMOGENEOUS in embedding version, and the query must be embedded with that same
version. Upgrading the embedding model is therefore not a config flip; it is a re-indexing job -- every document must be
re-embedded with the new model before any v2 query touches the index, and the index should be version-tagged so a
mismatched query is rejected rather than silently scored against the wrong space. A half-migrated index is worse than an
old one, because it returns confident nonsense for exactly the documents that were not migrated.

On this fixture the query truly matches the 'relevant' document (semantic cosine 0.95) and not the 'irrelevant' one
(0.00). But both documents are still embedded by the stale v1 model while the query is v2, so the indexed cosines are
scrambled: the relevant doc scores 0.31 and the irrelevant doc scores 1.00, ranking the wrong document first.
Re-embedding both documents with v2 restores the true similarities and puts the relevant document on top. This computes both.

  --similar   the true semantic cosine vs the indexed cosine under the mixed (query v2, docs v1) versions -- scrambled
  --reindex   re-embed the docs with the query's version; the cosines return to the true similarities and the gold wins
  --check     within-version cosine equals the true cosine; mixed-version cosine does not; re-indexing fixes the ranking

The semantic vectors and model versions are the fixture; every cosine is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "embver.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def embed(semantic, version, angles):
    """A model version embeds meaning by rotating the semantic space by its angle (a stand-in for its own vector space)."""
    a = math.radians(angles[version])
    x, y = semantic
    return [x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)]


def cosine(u, v):
    dot = sum(p * q for p, q in zip(u, v))
    nu = math.sqrt(sum(p * p for p in u))
    nv = math.sqrt(sum(q * q for q in v))
    return dot / (nu * nv) if nu and nv else 0.0


def true_cosine(query_sem, doc_sem):
    """The real semantic similarity, model-independent -- what retrieval is supposed to recover."""
    return cosine(query_sem, doc_sem)


def indexed_cosine(data, doc, doc_version):
    """The cosine the index actually computes: query embedded by its version, doc embedded by doc_version."""
    angles = data["model_angles_deg"]
    qv = embed(data["query_semantic"], data["query_version"], angles)
    dv = embed(doc["semantic"], doc_version, angles)
    return cosine(qv, dv)


def ranking(data, doc_version_of):
    """Rank docs by indexed cosine, using each doc's version from doc_version_of(doc)."""
    scored = [(d["id"], indexed_cosine(data, d, doc_version_of(d))) for d in data["docs"]]
    return sorted(scored, key=lambda kv: kv[1], reverse=True)


# ----------------------------------------------------------------- printing

def similar_view(data):
    print("SIMILAR — true semantic cosine vs the indexed cosine (query v2, docs still v1)")
    print("-" * 72)
    print("  doc           true cosine   indexed cosine (mixed versions)")
    for d in data["docs"]:
        print("  %-12s  %.2f          %.2f%s" % (d["id"], true_cosine(data["query_semantic"], d["semantic"]),
                                                 indexed_cosine(data, d, d["version"]),
                                                 "  <- gold" if d["id"] == data["gold"] else ""))
    print("-" * 72)
    rank = ranking(data, lambda d: d["version"])
    print("  indexed ranking: %s  (top = %s, should be %s)" % ([r[0] for r in rank], rank[0][0], data["gold"]))


def reindex_view(data):
    qv = data["query_version"]
    print("REINDEX — re-embed every doc with the query's version (%s), then re-rank" % qv)
    print("-" * 66)
    print("  doc           cosine before (mixed)   cosine after (all %s)" % qv)
    for d in data["docs"]:
        before = indexed_cosine(data, d, d["version"])
        after = indexed_cosine(data, d, qv)
        print("  %-12s  %.2f                    %.2f" % (d["id"], before, after))
    print("-" * 66)
    after_rank = ranking(data, lambda d: qv)
    print("  ranking after re-indexing: %s  (top = %s)" % ([r[0] for r in after_rank], after_rank[0][0]))


def check(data):
    print("SELF-TEST — within-version cosine equals the true cosine; mixed-version cosine does not; re-indexing fixes the ranking")
    print("-" * 114)
    qv, gold = data["query_version"], data["gold"]
    goldd = next(d for d in data["docs"] if d["id"] == gold)

    within_matches_true = abs(indexed_cosine(data, goldd, qv) - true_cosine(data["query_semantic"], goldd["semantic"])) < 1e-9
    print("  same-version cosine equals the true semantic cosine = %s (%.3f)" % (within_matches_true, indexed_cosine(data, goldd, qv)))

    mixed_wrong = abs(indexed_cosine(data, goldd, goldd["version"]) - true_cosine(data["query_semantic"], goldd["semantic"])) > 0.1
    print("  the mixed-version cosine for the gold doc is wrong = %s (%.3f vs true %.3f)"
          % (mixed_wrong, indexed_cosine(data, goldd, goldd["version"]), true_cosine(data["query_semantic"], goldd["semantic"])))

    mixed_rank = ranking(data, lambda d: d["version"])
    mixed_ranks_wrong = mixed_rank[0][0] != gold
    print("  the mixed index ranks the wrong doc first = %s (top = %s)" % (mixed_ranks_wrong, mixed_rank[0][0]))

    fixed_rank = ranking(data, lambda d: qv)
    reindex_fixes = fixed_rank[0][0] == gold
    print("  re-indexing to the query's version ranks the gold first = %s (top = %s)" % (reindex_fixes, fixed_rank[0][0]))

    stale_beats_gold = indexed_cosine(data, next(d for d in data["docs"] if d["id"] != gold), "v1") > indexed_cosine(data, goldd, goldd["version"])
    print("  a stale irrelevant doc outscores the stale gold doc = %s" % stale_beats_gold)

    ok = within_matches_true and mixed_wrong and mixed_ranks_wrong and reindex_fixes and stale_beats_gold
    print("-" * 114)
    print("SELF-TEST %s  within_matches_true=%s  mixed_wrong=%s  mixed_ranks_wrong=%s  reindex_fixes=%s  stale_beats_gold=%s"
          % ("PASS" if ok else "FAIL", within_matches_true, mixed_wrong, mixed_ranks_wrong, reindex_fixes, stale_beats_gold))
    return ok


def main():
    p = argparse.ArgumentParser(description="Embedding version mismatch: vectors from different model versions live in different spaces and are not comparable, so an index must be homogeneous in version and the query embedded with that version; a partial re-index scores stale docs as noise.")
    p.add_argument("--similar", action="store_true")
    p.add_argument("--reindex", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query_version=%s  docs=%s  gold=%s  file=%s  (the semantics and versions are a fixture)"
          % (data["query_version"], [(d["id"], d["version"]) for d in data["docs"]], data["gold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.similar:
        similar_view(data)
    elif args.reindex:
        reindex_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
