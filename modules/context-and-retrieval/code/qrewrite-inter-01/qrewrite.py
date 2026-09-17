"""Rewrite a follow-up into a self-contained query before retrieving -- a pronoun like 'it' has no entity to match.

Retrieval in a conversation has a problem that retrieval on a single question does not: the query is often not
self-contained. A user asks 'Tell me about the Falcon 9 rocket,' and then follows up with 'How much does it cost per
launch?' To a human the second question obviously means the Falcon 9, but the words of that question, taken alone, do not
say so -- the entity is carried only by the pronoun 'it.' A retriever embeds or keyword-matches the text it is given, and
the text it is given is 'How much does it cost per launch?', which contains the content terms 'cost' and 'launch' and no
mention of the Falcon 9 at all. So the retriever cannot distinguish a Falcon-9-specific cost document from a generic
rocket-cost document -- both match 'cost' and 'launch' equally -- and it may return the wrong one, or a tie it resolves
arbitrarily. The follow-up under-specifies the query, and the retriever has no access to the conversation that would
disambiguate it.

The fix is CONVERSATIONAL QUERY REWRITING (also called query contextualization or de-contextualization resolution): before
retrieving, rewrite the follow-up into a stand-alone query by resolving its references against the conversation history --
replace 'it' with the entity it refers to, carry forward the subject, expand the ellipsis. 'How much does it cost per
launch?' becomes 'How much does the Falcon 9 rocket cost per launch?', which now contains the entity terms the retriever
needs. The retriever, given the self-contained query, matches the Falcon-9 cost document decisively over the generic one,
because the query now carries the disambiguating terms 'falcon' and '9'. The rewrite happens once, before embedding or
keyword search, and turns an ambiguous fragment into a query that means what the user meant.

This is different from query EXPANSION, which broadens an already-self-contained query with synonyms or related terms.
Rewriting fills in what the follow-up left implicit from the dialogue -- it is about reference resolution, not breadth --
and it is essential for any multi-turn RAG or conversational search system, because without it every follow-up after the
first is retrieved on a fragment that has lost its subject.

On this fixture turn 1 established the entity (falcon, 9, rocket) and the follow-up's own terms are only (cost, launch).
Retrieving on the raw follow-up ties the Falcon-9 cost doc with the generic rocket-cost doc (both score 2). Rewriting the
query to include the carried-over entity terms makes the Falcon-9 cost doc win decisively (5 vs 3). This computes both.

  --retrieve   per-document keyword-overlap scores for the raw follow-up vs the rewritten query, and each one's top hit
  --rewrite    how the follow-up is made self-contained: the entity terms from turn 1 are merged into the follow-up terms
  --check      the raw follow-up ties the specific and generic docs; the rewritten query ranks the specific doc first

documents, history_terms, and follow_up_terms are the fixture; every query, score, and ranking is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "qrewrite.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def raw_query(data):
    """The follow-up's own content terms -- no entity, because it was a pronoun."""
    return list(data["follow_up_terms"])


def rewritten_query(data):
    """Resolve the reference: merge the entity terms carried from the conversation into the follow-up."""
    terms = list(data["follow_up_terms"])
    for t in data["history_terms"]:
        if t not in terms:
            terms.append(t)
    return terms


def score(query_terms, doc_terms):
    """Keyword-overlap score: how many query terms the document contains."""
    return sum(1 for t in query_terms if t in doc_terms)


def rank(data, query_terms):
    scored = [(doc, score(query_terms, terms)) for doc, terms in data["documents"].items()]
    return sorted(scored, key=lambda kv: (-kv[1], kv[0]))


# ----------------------------------------------------------------- printing

def retrieve_view(data):
    raw = raw_query(data)
    rew = rewritten_query(data)
    print("RETRIEVE — keyword-overlap scores, raw follow-up vs rewritten query")
    print("-" * 66)
    print("  raw query      = %s" % raw)
    for doc, s in rank(data, raw):
        print("    %-24s %d" % (doc, s))
    print("  rewritten query = %s" % rew)
    for doc, s in rank(data, rew):
        print("    %-24s %d" % (doc, s))
    print("-" * 66)
    print("  raw top: %s ; rewritten top: %s" % (rank(data, raw)[0], rank(data, rew)[0]))


def rewrite_view(data):
    print("REWRITE — making the follow-up self-contained")
    print("-" * 60)
    print("  turn 1 established the entity: %s" % data["history_terms"])
    print("  follow-up 'How much does IT cost per launch?' terms: %s" % data["follow_up_terms"])
    print("  'it' has no entity term -> resolve it from the history:")
    print("  rewritten query terms = follow-up + entity = %s" % rewritten_query(data))
    print("-" * 60)
    print("  the pronoun is replaced by the carried-over entity, so the query now names the Falcon 9.")


def check(data):
    print("SELF-TEST — the raw follow-up ties the specific and generic docs; the rewritten query ranks the specific one first")
    print("-" * 114)
    raw = raw_query(data)
    rew = rewritten_query(data)
    specific = "d1_falcon9_cost"
    generic = "d2_generic_rocket_cost"

    raw_ties = score(raw, data["documents"][specific]) == score(raw, data["documents"][generic])
    print("  raw follow-up ties the specific and generic docs = %s (%d == %d)"
          % (raw_ties, score(raw, data["documents"][specific]), score(raw, data["documents"][generic])))

    rewrite_adds_entity = set(rew) - set(raw) == set(data["history_terms"])
    print("  rewriting adds exactly the entity terms the follow-up lacked = %s (%s)" % (rewrite_adds_entity, sorted(set(rew) - set(raw))))

    rewritten_top = rank(data, rew)[0][0]
    rewrite_ranks_specific = rewritten_top == specific
    print("  the rewritten query ranks the specific doc first = %s (%s)" % (rewrite_ranks_specific, rewritten_top))

    rewrite_breaks_tie = score(rew, data["documents"][specific]) > score(rew, data["documents"][generic])
    print("  the rewritten query beats the generic doc, not ties it = %s (%d > %d)"
          % (rewrite_breaks_tie, score(rew, data["documents"][specific]), score(rew, data["documents"][generic])))

    specific_score_rose = score(rew, data["documents"][specific]) > score(raw, data["documents"][specific])
    print("  the specific doc scores higher after rewriting = %s (%d > %d)"
          % (specific_score_rose, score(rew, data["documents"][specific]), score(raw, data["documents"][specific])))

    ok = raw_ties and rewrite_adds_entity and rewrite_ranks_specific and rewrite_breaks_tie and specific_score_rose
    print("-" * 114)
    print("SELF-TEST %s  raw_ties=%s  rewrite_adds_entity=%s  rewrite_ranks_specific=%s  rewrite_breaks_tie=%s  specific_score_rose=%s"
          % ("PASS" if ok else "FAIL", raw_ties, rewrite_adds_entity, rewrite_ranks_specific, rewrite_breaks_tie, specific_score_rose))
    return ok


def main():
    p = argparse.ArgumentParser(description="Conversational query rewriting: before retrieving in a multi-turn conversation, rewrite a follow-up into a self-contained query by resolving its references against the history (replace 'it' with the entity it refers to), because a retriever matches only the text it is given, and a follow-up whose entity is a pronoun has no term to match, so it cannot distinguish the specific document from a generic one.")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--rewrite", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("history_terms=%s  follow_up_terms=%s  documents=%d  file=%s  (the conversation and docs are a fixture)"
          % (data["history_terms"], data["follow_up_terms"], len(data["documents"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.retrieve:
        retrieve_view(data)
    elif args.rewrite:
        rewrite_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
