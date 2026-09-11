"""Retrieve in hops for a bridge question, or one-shot retrieval never reaches the answer document.

Some questions cannot be answered by a single retrieval, because the answer document does not share enough
words with the question. Take 'who directed the film that won bestpicture1994?' The document that actually
holds the answer says 'forrestgump was directed by robertzemeckis' -- and it contains none of the
question's distinctive terms (bestpicture1994, won, film). The question and the answer are connected only
through a bridge entity, forrestgump, that neither states: the question knows the award, the answer knows
the director, and the film links them. Retrieve once on the question and you land on the document about the
award, not the one with the director, because that is the document the question's words match. The answer
document is effectively invisible to one-shot retrieval.

Multi-hop retrieval solves it by retrieving more than once and feeding each result back into the next query.
Hop one retrieves the bridge document (the award-to-film fact), which supplies the missing entity. Append
that document to the query and hop two now carries the film's name, so it matches and retrieves the answer
document (the film-to-director fact). The chain of two retrievals follows the chain of two facts the
question spans. One hop stops at the bridge; two hops reach the answer.

On this fixture the question is about a 1994 award and the answer is a director. One-shot retrieval's top
document is the bridge (similarity 0.571) while the true answer scores only 0.169 to the raw question,
below two other documents -- unreachable. After hop one supplies the film name and the query is
reformulated, the second hop retrieves the answer document as its top result (0.447). This computes both.

  --corpus     the question and each document, with the answer marked
  --retrieve   one-shot similarity vs the second-hop similarity after feeding back the bridge
  --check      one-shot lands on the bridge and misses the answer; a second hop reaches it

The question and documents are the fixture; every similarity is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "corpus.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


STOPWORDS = {"the", "was", "by", "a", "an", "of", "to", "that", "who", "is", "are"}


def vec(text):
    d = {}
    for w in text.lower().split():
        d[w] = d.get(w, 0) + 1
    return d


def cosine(a, b):
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return round(dot / (na * nb), 3) if na and nb else 0.0


def sims(query, docs):
    """Similarity of the query to every document."""
    qv = vec(query)
    return {d: cosine(qv, vec(docs[d]["text"])) for d in docs}


def top(query, docs):
    s = sims(query, docs)
    return max(s, key=s.get)


def answer_id(docs):
    return next(d for d in docs if docs[d]["answer"])


def bridge_id(docs):
    return next(d for d in docs if docs[d].get("bridge"))


def bridge_entity(query, doc_text):
    """The new content terms a document adds beyond the query -- the bridge it supplies."""
    novel = [w for w in doc_text.lower().split() if w not in vec(query) and w not in STOPWORDS]
    return " ".join(novel)


def second_hop_query(query, docs):
    """Reformulate: drop the sub-question the bridge already answered, carry its entity forward."""
    bridge_text = docs[top(query, docs)]["text"]
    resolved = vec(bridge_text)                                  # terms the bridge doc satisfied
    residual = [w for w in query.split() if w.lower() not in resolved]
    return " ".join(residual) + " " + bridge_entity(query, bridge_text)


def remaining(docs, exclude):
    """Documents still in play after a hop already retrieved `exclude`."""
    return {d: docs[d] for d in docs if d != exclude}


# ----------------------------------------------------------------- printing

def corpus_view(data):
    print("CORPUS — question and documents (answer needs a bridge entity)")
    print("-" * 62)
    print("  question: %s" % data["question"])
    for d, doc in data["docs"].items():
        tag = "  (ANSWER)" if doc["answer"] else ("  (bridge)" if doc.get("bridge") else "")
        print("  %s%s: %s" % (d, tag, doc["text"]))
    print("-" * 62)
    print("  the answer doc shares no distinctive term with the question.")


def retrieve_view(data):
    q, docs = data["question"], data["docs"]
    print("RETRIEVE — one-shot similarity, then second hop after feedback")
    print("-" * 62)
    s1 = sims(q, docs)
    print("  hop 1 (raw question):")
    for d in docs:
        print("    %-8s %.3f" % (d, s1[d]))
    print("  hop 1 top: %s   answer: %s" % (top(q, docs), answer_id(docs)))
    q2 = second_hop_query(q, docs)
    rem = remaining(docs, top(q, docs))
    s2 = sims(q2, rem)
    print("  hop 2 (reformulated with '%s', excluding %s):" % (bridge_entity(q, docs[top(q, docs)]["text"]), top(q, docs)))
    for d in rem:
        print("    %-8s %.3f" % (d, s2[d]))
    print("  hop 2 top: %s   answer: %s" % (top(q2, rem), answer_id(docs)))


def check(data):
    print("SELF-TEST — one-shot lands on the bridge and misses the answer; a second hop reaches it")
    print("-" * 90)
    q, docs = data["question"], data["docs"]
    ans, bridge = answer_id(docs), bridge_id(docs)
    s1 = sims(q, docs)
    q2 = second_hop_query(q, docs)
    rem = remaining(docs, top(q, docs))
    s2 = sims(q2, rem)

    onehop_misses = top(q, docs) != ans
    print("  one-shot retrieval's top is NOT the answer = %s (top %s)" % (onehop_misses, top(q, docs)))

    answer_unreachable = s1[ans] < s1[top(q, docs)]
    print("  the answer scores below the one-shot top, so it is unreachable = %s (%.3f < %.3f)"
          % (answer_unreachable, s1[ans], s1[top(q, docs)]))

    onehop_lands_bridge = top(q, docs) == bridge
    print("  one-shot lands on the bridge document = %s (%s)" % (onehop_lands_bridge, top(q, docs)))

    twohop_finds = top(q2, rem) == ans
    print("  the second hop retrieves the answer = %s (top %s)" % (twohop_finds, top(q2, rem)))

    feedback_lifts_answer = s2[ans] > s1[ans]
    print("  feeding back the bridge lifts the answer's score = %s (%.3f -> %.3f)" % (feedback_lifts_answer, s1[ans], s2[ans]))

    ok = onehop_misses and answer_unreachable and onehop_lands_bridge and twohop_finds and feedback_lifts_answer
    print("-" * 90)
    print("SELF-TEST %s  onehop_misses=%s  answer_unreachable=%s  onehop_lands_bridge=%s  twohop_finds=%s  feedback_lifts_answer=%s"
          % ("PASS" if ok else "FAIL", onehop_misses, answer_unreachable, onehop_lands_bridge, twohop_finds, feedback_lifts_answer))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retrieve in hops for a bridge question so the answer document is reachable.")
    p.add_argument("--corpus", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  file=%s  (the question and documents are a fixture)" % (len(data["docs"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.corpus:
        corpus_view(data)
    elif args.retrieve:
        retrieve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
