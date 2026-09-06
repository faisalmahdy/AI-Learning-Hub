"""Compress a retrieved chunk to its query-relevant sentences, or you spend the budget on filler that answers nothing.

Retrieval returns whole chunks, but a chunk is mostly not about your query. It has an introductory line, an
unrelated aside, a sign-off -- and one or two sentences that actually address the question. Inject the whole
chunk and you pay for all of it: the filler eats context-window budget you could have spent on more chunks, and it
dilutes the model's attention, burying the answer sentence among text that looks superficially on-topic because it
came from a relevant document. The chunk was the right thing to RETRIEVE; it is the wrong thing to INJECT whole.

Contextual compression fixes the mismatch by filtering within the chunk before it enters the prompt. Score each
sentence by how much of the query it contains, and keep only the sentences that clear a threshold; drop the rest.
The answer sentence -- the one carrying the query terms -- survives, and the filler is removed, so the text you
inject is a fraction of the size while still containing the answer. You retrieved at the chunk granularity for
recall and inject at the sentence granularity for density: the search finds the right passage, and the compression
strips it to the part that earns its place in the window.

On this fixture a five-sentence chunk totals 26 tokens, but only two sentences mention the query ('refund',
'time'): one scores 1, the answer sentence scores 2, the other three score 0. Keeping the two that clear the
threshold yields 13 tokens -- half the size -- and both retained sentences carry the answer detail '30'. The
answer is preserved; the filler is gone. This computes both.

  --score      each sentence's query-overlap score and whether compression keeps it
  --compress   the full chunk vs the compressed chunk, their token counts, and the answer's survival
  --check      the answer sentence is kept, the filler is dropped, and the compressed chunk is smaller

The chunk and query are the fixture; every score is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "compress.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def score(sentence, query):
    """A sentence's relevance: how many distinct query terms it contains."""
    return len(set(query) & set(sentence))


def keep(sentences, query, threshold):
    """Indices of the sentences that clear the relevance threshold."""
    return [i for i, s in enumerate(sentences) if score(s, query) >= threshold]


def tokens(sentences, indices=None):
    """Total token count of all sentences, or of the given indices."""
    idx = range(len(sentences)) if indices is None else indices
    return sum(len(sentences[i]) for i in idx)


# ----------------------------------------------------------------- printing

def score_view(data):
    sents, q, thr = data["sentences"], data["query"], data["threshold"]
    kept = keep(sents, q, thr)
    print("SCORE — each sentence's query overlap and whether it is kept (threshold %d)" % thr)
    print("-" * 66)
    for i, s in enumerate(sents):
        mark = "KEEP" if i in kept else "drop"
        print("  s%d  score %d  %s  %s" % (i, score(s, q), mark, " ".join(s)))
    print("-" * 66)
    print("  only the sentences that mention the query survive; the filler is dropped.")


def compress_view(data):
    sents, q, thr, ans = data["sentences"], data["query"], data["threshold"], data["answer_token"]
    kept = keep(sents, q, thr)
    full_ans = any(ans in s for s in sents)
    comp_ans = any(ans in sents[i] for i in kept)
    print("COMPRESS — full chunk vs compressed chunk")
    print("-" * 66)
    print("  full chunk:       %d sentences, %d tokens   answer '%s' present: %s" % (len(sents), tokens(sents), ans, full_ans))
    print("  compressed chunk: %d sentences, %d tokens   answer '%s' present: %s" % (len(kept), tokens(sents, kept), ans, comp_ans))
    print("  budget kept:      %.0f%% of the tokens removed" % (100 * (1 - tokens(sents, kept) / tokens(sents))))
    print("-" * 66)
    print("  half the tokens gone, the answer still there -- density without losing the answer.")


def check(data):
    print("SELF-TEST — the answer sentence is kept, the filler is dropped, and the compressed chunk is smaller")
    print("-" * 104)
    sents, q, thr, ans = data["sentences"], data["query"], data["threshold"], data["answer_token"]
    kept = keep(sents, q, thr)

    answer_in_full = any(ans in s for s in sents)
    print("  the answer token is in the full chunk = %s" % answer_in_full)

    answer_in_compressed = any(ans in sents[i] for i in kept)
    print("  the answer token survives compression = %s" % answer_in_compressed)

    compressed_smaller = tokens(sents, kept) < tokens(sents)
    print("  the compressed chunk is smaller than the full chunk = %s (%d < %d tokens)" % (compressed_smaller, tokens(sents, kept), tokens(sents)))

    top = max(range(len(sents)), key=lambda i: score(sents[i], q))
    top_sentence_kept = top in kept
    print("  the highest-scoring sentence is kept = %s (s%d, score %d)" % (top_sentence_kept, top, score(sents[top], q)))

    filler = [i for i, s in enumerate(sents) if score(s, q) == 0]
    filler_dropped = all(i not in kept for i in filler)
    print("  every zero-overlap filler sentence is dropped = %s (%s)" % (filler_dropped, ["s%d" % i for i in filler]))

    ok = answer_in_full and answer_in_compressed and compressed_smaller and top_sentence_kept and filler_dropped
    print("-" * 104)
    print("SELF-TEST %s  answer_in_full=%s  answer_in_compressed=%s  compressed_smaller=%s  top_sentence_kept=%s  filler_dropped=%s"
          % ("PASS" if ok else "FAIL", answer_in_full, answer_in_compressed, compressed_smaller, top_sentence_kept, filler_dropped))
    return ok


def main():
    p = argparse.ArgumentParser(description="Contextual compression filters a retrieved chunk to its query-relevant sentences before injecting, saving budget without losing the answer.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--compress", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  sentences=%d  full_tokens=%d  file=%s  (the chunk is a fixture)"
          % (data["query"], len(data["sentences"]), tokens(data["sentences"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.compress:
        compress_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
