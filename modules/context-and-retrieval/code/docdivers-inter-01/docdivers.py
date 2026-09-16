"""Diversify the top-k across source documents (cap chunks per document) -- one comprehensive document can fill every slot with distinct high-scoring chunks and starve a multi-document question of the other sources.

Retrieval scores chunks, and the obvious selector takes the top k by score. That works when the answer lives in one place. It fails when a question needs evidence spread across several documents, because scores do not distribute themselves fairly across sources: one thorough, on-topic document can produce the several highest-scoring chunks and take every slot, leaving no room for the second and third documents that hold the rest of the answer.

The crowding chunks are not duplicates. Each is a genuinely different passage covering a different fact, so a novelty or maximal-marginal-relevance filter -- which drops near-duplicate content -- keeps all of them; they are all novel. That is what makes this a separate problem from de-duplication. The chunks are diverse in content and identical in source, and it is the shared source, not repeated content, that starves the other documents.

The fix is to diversify by source: cap how many chunks any one document may contribute to the top-k. Keep the best few from each document and let lower-scoring chunks from other documents into the remaining slots. A single document can no longer monopolize the results, so a multi-document question gets at least one chunk from each relevant source, even if that source's best chunk scored below the dominant document's third or fourth.

There is a cost, stated plainly: the capped selection includes some lower-scoring chunks in place of higher-scoring ones from the dominant document, so if the answer really was all in one document, the cap slightly hurts. The cap is a bet that coverage across sources matters more than squeezing the last chunk from the top document -- true for multi-hop and multi-aspect questions, and the reason to make the cap a tunable, not zero and not infinite.

The rule: cap the number of chunks any one document contributes to the top-k, so the results span sources rather than letting one document's several high-scoring chunks fill every slot -- because a question whose answer is spread across documents needs coverage of those documents, which pure top-by-score does not guarantee even when the chunks are all content-distinct.

On this fixture one document supplies the three top-scoring chunks; pure top-k returns all three and covers one of the three required facts, while a per-document cap spreads the three slots across the three documents and covers all three. This computes both.

  --select    the pure top-k selection vs the per-document-capped selection, with each one's source documents
  --coverage  how many of the question's required facts each selection covers
  --check     one document monopolizes pure top-k; a per-document cap spreads the sources and covers more required facts

chunks, required, top_k, and per_doc_cap are the fixture; the two selections and their coverage are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "docdivers.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def by_score(chunks):
    return sorted(chunks, key=lambda c: -c["score"])


def pure_topk(chunks, k):
    """Take the k highest-scoring chunks, ignoring their source."""
    return by_score(chunks)[:k]


def capped_topk(chunks, k, cap):
    """Take the highest-scoring chunks but at most `cap` from any one document."""
    selected = []
    counts = {}
    for c in by_score(chunks):
        if counts.get(c["doc"], 0) < cap:
            selected.append(c)
            counts[c["doc"]] = counts.get(c["doc"], 0) + 1
        if len(selected) == k:
            break
    return selected


def sources(selection):
    return sorted(set(c["doc"] for c in selection))


def required_covered(selection, required):
    facts = set(c["fact"] for c in selection)
    return [f for f in required if f in facts]


# ----------------------------------------------------------------- printing

def select_view(data):
    chunks, k, cap = data["chunks"], data["top_k"], data["per_doc_cap"]
    pure = pure_topk(chunks, k)
    capped = capped_topk(chunks, k, cap)
    print("SELECT — pure top-%d vs per-document cap of %d" % (k, cap))
    print("-" * 60)
    print("  pure top-k   : %s   sources=%s"
          % ([c["id"] for c in pure], sources(pure)))
    print("  capped top-k : %s   sources=%s"
          % ([c["id"] for c in capped], sources(capped)))
    print("-" * 60)
    print("  pure top-k is monopolized by one document; the cap spreads the sources")


def coverage_view(data):
    chunks, k, cap, req = data["chunks"], data["top_k"], data["per_doc_cap"], data["required"]
    pure = pure_topk(chunks, k)
    capped = capped_topk(chunks, k, cap)
    print("COVERAGE — required facts %s covered by each selection" % req)
    print("-" * 58)
    print("  pure top-k   covers %s  (%d of %d)"
          % (required_covered(pure, req), len(required_covered(pure, req)), len(req)))
    print("  capped top-k covers %s  (%d of %d)"
          % (required_covered(capped, req), len(required_covered(capped, req)), len(req)))
    print("-" * 58)
    print("  the required facts live in different documents, so source spread wins them")


def check(data):
    print("SELF-TEST — one document monopolizes pure top-k; a per-document cap spreads the sources and covers more required facts")
    print("-" * 124)
    chunks, k, cap, req = data["chunks"], data["top_k"], data["per_doc_cap"], data["required"]
    pure = pure_topk(chunks, k)
    capped = capped_topk(chunks, k, cap)

    chunks_content_distinct = len(set(c["fact"] for c in chunks)) == len(chunks)
    print("  every chunk covers a distinct fact (not near-duplicates) = %s" % chunks_content_distinct)

    pure_one_source = len(sources(pure)) == 1
    print("  pure top-k comes from a single document = %s (%s)" % (pure_one_source, sources(pure)))

    capped_multi_source = len(sources(capped)) > len(sources(pure))
    print("  the cap spreads the selection across more documents = %s (%s)" % (capped_multi_source, sources(capped)))

    pure_cov = len(required_covered(pure, req))
    capped_cov = len(required_covered(capped, req))
    capped_covers_more = capped_cov > pure_cov
    print("  the cap covers more of the required facts = %s (%d vs %d)" % (capped_covers_more, capped_cov, pure_cov))

    capped_covers_all = capped_cov == len(req)
    print("  the cap covers every required fact = %s (%d of %d)" % (capped_covers_all, capped_cov, len(req)))

    ok = (chunks_content_distinct and pure_one_source and capped_multi_source
          and capped_covers_more and capped_covers_all)
    print("-" * 124)
    print("SELF-TEST %s  chunks_content_distinct=%s  pure_one_source=%s  capped_multi_source=%s  capped_covers_more=%s  capped_covers_all=%s"
          % ("PASS" if ok else "FAIL", chunks_content_distinct, pure_one_source,
             capped_multi_source, capped_covers_more, capped_covers_all))
    return ok


def main():
    p = argparse.ArgumentParser(description="Source diversity: cap the number of chunks any one document contributes to the top-k, so the results span sources rather than letting one document's several high-scoring chunks fill every slot -- because a question whose answer is spread across documents needs coverage of those documents, which pure top-by-score does not guarantee even when the chunks are all content-distinct.")
    p.add_argument("--select", action="store_true")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("chunks=%d  top_k=%d  per_doc_cap=%d  required=%d  file=%s  (the chunks are a fixture)"
          % (len(data["chunks"]), data["top_k"], data["per_doc_cap"], len(data["required"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.select:
        select_view(data)
    elif args.coverage:
        coverage_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
