"""Verify each claim in the answer against the retrieved passages -- a model can add a claim no passage supports even when retrieval succeeded, and shipping it unchecked turns good retrieval into a confident, sourced-looking hallucination.

It is tempting to think retrieval-augmented generation is safe once the retriever returns relevant passages: the facts are in the context, so the answer must come from them. But the generation step is still a language model. Handed the right passages, it will answer from them -- and then, just as fluently, add a statement that was not in any of them: a fact it remembers, a plausible-sounding average, a smooth continuation. That extra statement arrives with the same confidence as the supported ones and, because the system is 'grounded in retrieval', with an implicit citation it does not deserve.

Crucially, this is not a retrieval failure. The retriever can do everything right -- surface passages that support most of the answer -- and the answer can still contain a claim none of them supports. So a groundedness check is a separate step from anything the retriever does; a relevance floor or a better ranker cannot catch a claim the model invented out of good context.

The check decomposes the answer into atomic claims and verifies each against the retrieved passages, keeping the supported claims and flagging the unsupported one for dropping, re-answering, or human review. Support is modeled here as a claim appearing among the passages' facts -- a stylized stand-in for a real entailment/NLI check, but faithful to the rule: a grounded answer says only what the sources say.

On this fixture the passages support two of the answer's three claims (the nausea side effect and the 200mg dose); the third -- 'drug_x is safe during pregnancy' -- appears in no passage and is a hallucination. The naive path ships all three; the grounded path keeps the two supported and flags the third. This computes both.

  --answer    the candidate answer's claims, each marked supported or not by the retrieved passages
  --grounded  the grounded answer: the supported claims kept, the unsupported claim flagged
  --check     the answer contains an unsupported claim though retrieval succeeded, the naive path ships it, and the grounded check flags it while keeping the supported claims

passages and answer_claims are the fixture; which claims are supported and the two answers are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "grounded.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def supported_facts(passages):
    """The set of facts actually stated by the retrieved passages -- the only things an answer may assert."""
    facts = set()
    for passage in passages.values():
        facts.update(passage)
    return facts


def is_supported(claim, passages):
    """A claim is grounded iff some retrieved passage states it (stylized entailment: exact-fact membership)."""
    return claim in supported_facts(passages)


def grounded_answer(claims, passages):
    """Keep only the claims the passages support -- the answer that says only what the sources say."""
    return [c for c in claims if is_supported(c, passages)]


def unsupported_claims(claims, passages):
    """The claims no passage supports -- hallucinations to flag, drop, or send back for a re-answer."""
    return [c for c in claims if not is_supported(c, passages)]


# ----------------------------------------------------------------- printing

def answer_view(data):
    claims, passages = data["answer_claims"], data["passages"]
    print("ANSWER — the candidate answer's claims against the retrieved passages")
    print("-" * 68)
    for c in claims:
        print("  [%s] %s" % ("supported" if is_supported(c, passages) else "UNSUPPORTED", c))
    print("-" * 68)
    print("  the naive path ships every claim, including the one no passage supports")


def grounded_view(data):
    claims, passages = data["answer_claims"], data["passages"]
    kept = grounded_answer(claims, passages)
    flagged = unsupported_claims(claims, passages)
    print("GROUNDED — keep the supported claims, flag the unsupported ones")
    print("-" * 68)
    print("  kept (grounded answer):")
    for c in kept:
        print("    - %s" % c)
    print("  flagged as ungrounded: %s" % flagged)
    print("-" * 68)
    print("  the answer now asserts only what the retrieved passages actually say")


def check(data):
    print("SELF-TEST — the answer contains an unsupported claim though retrieval succeeded, the naive path ships it, and the grounded check flags it while keeping the supported claims")
    print("-" * 112)
    claims, passages = data["answer_claims"], data["passages"]
    flagged = unsupported_claims(claims, passages)
    kept = grounded_answer(claims, passages)

    has_unsupported_claim = len(flagged) > 0
    print("  the answer contains an unsupported claim = %s (%s)" % (has_unsupported_claim, flagged))

    retrieval_succeeded = len(kept) > 0
    print("  retrieval succeeded -- passages support other claims = %s (%d of %d supported)" % (retrieval_succeeded, len(kept), len(claims)))

    naive_ships_unsupported = any(c in claims for c in flagged)
    print("  the naive (unchecked) answer ships the unsupported claim = %s" % naive_ships_unsupported)

    grounded_drops_unsupported = all(c not in kept for c in flagged)
    print("  the grounded answer drops every unsupported claim = %s" % grounded_drops_unsupported)

    grounded_keeps_supported = all(is_supported(c, passages) for c in kept) and len(kept) == len(claims) - len(flagged)
    print("  the grounded answer keeps every supported claim = %s (%d kept)" % (grounded_keeps_supported, len(kept)))

    ok = (has_unsupported_claim and retrieval_succeeded and naive_ships_unsupported
          and grounded_drops_unsupported and grounded_keeps_supported)
    print("-" * 112)
    print("SELF-TEST %s  has_unsupported_claim=%s  retrieval_succeeded=%s  naive_ships_unsupported=%s  grounded_drops_unsupported=%s  grounded_keeps_supported=%s"
          % ("PASS" if ok else "FAIL", has_unsupported_claim, retrieval_succeeded, naive_ships_unsupported,
             grounded_drops_unsupported, grounded_keeps_supported))
    return ok


def main():
    p = argparse.ArgumentParser(description="Groundedness: verify each claim in a retrieval-augmented answer against the retrieved passages, because the generation step can add a claim no passage supports even when retrieval succeeded -- a hallucination that arrives sourced-looking and confident unless a groundedness check flags it.")
    p.add_argument("--answer", action="store_true")
    p.add_argument("--grounded", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("passages=%s  claims=%d  file=%s  (these are a fixture)"
          % (list(data["passages"].keys()), len(data["answer_claims"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.answer:
        answer_view(data)
    elif args.grounded:
        grounded_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
