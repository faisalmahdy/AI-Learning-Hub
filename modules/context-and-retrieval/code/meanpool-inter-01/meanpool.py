"""Mask the padding out of a mean-pooled sentence embedding -- averaging the padding tokens' vectors in drags the embedding off direction and misranks retrieval.

A standard way to turn a document into one vector for dense retrieval is to embed each token and average the token embeddings -- mean pooling. It is simple and it works, with one condition that is easy to drop: the average must be taken over the REAL tokens only. Documents in a batch are padded to a common length so they fit in a rectangular tensor, and those padding positions carry embeddings like any other token id -- the pad id maps to some vector. If you mean-pool over the whole padded tensor, you average those padding vectors into the sentence embedding, pulling it toward the padding direction and away from what the document actually says.

The distortion is not uniform. A padded batch gives short documents more padding and long documents less, so the padding pulls a short document's embedding harder than a long one's. That is exactly the wrong bias: a short, highly relevant document is diluted more than a long, mediocre one, so the mediocre document's similarity to the query can end up higher and the ranking flips. The retriever returns the wrong document, and nothing looks broken -- the embeddings have the right shape, the cosine is a real number, the pipeline runs. The bug lives entirely in whether the mean skipped the padding.

The fix is masked mean pooling: use the attention mask to sum only the real-token embeddings and divide by the count of real tokens, so padding never enters the average. The sentence embedding then depends only on the document's actual content, and its length -- how much padding it happened to get in its batch -- no longer moves its direction.

The rule: mask padding out of a mean-pooled embedding, summing only real-token vectors over the real-token count, because padding tokens carry embeddings and averaging them in pulls the sentence vector toward the padding direction -- diluting short documents most and flipping the retrieval ranking; masked pooling makes the embedding depend on content alone.

On this fixture the query aligns perfectly with document A, but A is short and padded while document B is longer and unpadded. Masked pooling ranks A first (cosine 1.00 vs 0.80); naive pooling dilutes A to 0.71 with its padding and wrongly ranks B first. This computes both.

  --pool     each document's masked vs naive mean-pooled embedding
  --rank     the cosine similarity to the query and the ranking under each pooling
  --check    naive pooling drags the padded document off direction and flips the ranking; masked pooling ranks the relevant document first

query and the token embeddings are the fixture; the pooled embeddings, cosines, and rankings are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "meanpool.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(vectors):
    n = len(vectors)
    return [sum(comp) / n for comp in zip(*vectors)]


def masked_pool(doc):
    """Mean over the real tokens only -- padding is masked out."""
    return mean(doc["real_tokens"])


def naive_pool(doc):
    """Mean over real AND padding tokens -- the padding leaks in."""
    return mean(doc["real_tokens"] + doc["pad_tokens"])


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


def rank(query, docs, pool):
    scored = [(d["id"], cosine(query, pool(d))) for d in docs]
    return sorted(scored, key=lambda kv: kv[1], reverse=True)


# ----------------------------------------------------------------- printing

def pool_view(data):
    docs = data["documents"]
    print("POOL — masked (real tokens only) vs naive (real + padding) mean pooling")
    print("-" * 66)
    for d in docs:
        m, n = masked_pool(d), naive_pool(d)
        pads = len(d["pad_tokens"])
        print("  doc %s (%d real, %d pad)  masked=%s  naive=%s" % (d["id"], len(d["real_tokens"]), pads, [round(x, 2) for x in m], [round(x, 2) for x in n]))
    print("-" * 66)
    print("  padding pulls the naive embedding toward the padding direction; masked pooling ignores it")


def rank_view(data):
    q, docs = data["query"], data["documents"]
    print("RANK — cosine to the query and ranking under each pooling")
    print("-" * 60)
    print("  doc  relevant  masked cos   naive cos")
    for d in docs:
        print("  %-3s  %-8s  %.2f         %.2f" % (d["id"], d["relevant"], cosine(q, masked_pool(d)), cosine(q, naive_pool(d))))
    masked_order = [i for i, _ in rank(q, docs, masked_pool)]
    naive_order = [i for i, _ in rank(q, docs, naive_pool)]
    print("-" * 60)
    print("  masked ranking: %s   naive ranking: %s" % (masked_order, naive_order))
    print("  naive pooling flips the top result to the less relevant document")


def check(data):
    print("SELF-TEST — naive pooling drags the padded document off direction and flips the ranking; masked pooling ranks the relevant document first")
    print("-" * 134)
    q, docs = data["query"], data["documents"]
    relevant = next(d for d in docs if d["relevant"])
    masked_order = [i for i, _ in rank(q, docs, masked_pool)]
    naive_order = [i for i, _ in rank(q, docs, naive_pool)]

    doc_has_padding = len(relevant["pad_tokens"]) > 0
    print("  the relevant document is padded = %s (%d pad tokens)" % (doc_has_padding, len(relevant["pad_tokens"])))

    padding_pulls_embedding = masked_pool(relevant) != naive_pool(relevant)
    print("  padding changes the relevant doc's pooled embedding = %s (%s -> %s)"
          % (padding_pulls_embedding, [round(x, 2) for x in masked_pool(relevant)], [round(x, 2) for x in naive_pool(relevant)]))

    naive_dilutes = cosine(q, naive_pool(relevant)) < cosine(q, masked_pool(relevant))
    print("  naive pooling lowers the relevant doc's cosine = %s (%.2f < %.2f)"
          % (naive_dilutes, cosine(q, naive_pool(relevant)), cosine(q, masked_pool(relevant))))

    masked_ranks_relevant_first = masked_order[0] == relevant["id"]
    print("  masked pooling ranks the relevant document first = %s (%s)" % (masked_ranks_relevant_first, masked_order))

    naive_ranks_wrong_first = naive_order[0] != relevant["id"]
    print("  naive pooling ranks the WRONG document first = %s (%s)" % (naive_ranks_wrong_first, naive_order))

    ok = (doc_has_padding and padding_pulls_embedding and naive_dilutes
          and masked_ranks_relevant_first and naive_ranks_wrong_first)
    print("-" * 134)
    print("SELF-TEST %s  doc_has_padding=%s  padding_pulls_embedding=%s  naive_dilutes=%s  masked_ranks_relevant_first=%s  naive_ranks_wrong_first=%s"
          % ("PASS" if ok else "FAIL", doc_has_padding, padding_pulls_embedding, naive_dilutes, masked_ranks_relevant_first, naive_ranks_wrong_first))
    return ok


def main():
    p = argparse.ArgumentParser(description="Masked mean pooling: mask padding out of a mean-pooled embedding, summing only real-token vectors over the real-token count, because padding tokens carry embeddings and averaging them in pulls the sentence vector toward the padding direction -- diluting short documents most and flipping the retrieval ranking; masked pooling makes the embedding depend on content alone.")
    p.add_argument("--pool", action="store_true")
    p.add_argument("--rank", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  documents=%d  file=%s  (the query and token embeddings are a fixture)"
          % (data["query"], len(data["documents"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pool:
        pool_view(data)
    elif args.rank:
        rank_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
