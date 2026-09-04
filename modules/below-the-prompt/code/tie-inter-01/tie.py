"""Tie the output projection to the input embedding, or you pay twice for the same token vectors.

A language model touches its vocabulary at both ends. At the input it looks up each token's embedding -- a
row of the embedding matrix E, one vector per vocabulary word. At the output it turns the final hidden
state into a logit per word, by multiplying it against an unembedding matrix U -- again one vector per
word. Left independent, E and U are two separate matrices of the same shape (vocab x model-dim), so the
token vectors cost twice: in a large model the embedding and unembedding together can be a huge share of
the parameters, and the two are learned separately with nothing forcing them to agree.

Weight tying sets U equal to E. The same matrix that embeds a token on the way in scores it on the way out,
so the logit for token t is just the dot product of the hidden state with token t's own embedding. This
halves the vocabulary parameters (one matrix instead of two) and, more deeply, puts a token's input
representation and its output representation in the same space -- a hidden state that has moved toward a
token's embedding automatically assigns that token a high logit. Empirically tying does not hurt and often
improves perplexity, which is why most language models tie these weights.

On this fixture a tiny model has 4 tokens and a 3-dim hidden state. Untied, the embedding and unembedding
are two 4x3 matrices -- 24 parameters -- and because the unembedding is unrelated to the embedding, a
hidden state equal to a token's embedding can be scored highest for a DIFFERENT token. Tied, there is one
4x3 matrix -- 12 parameters -- and a hidden state equal to token t's embedding always scores token t
highest. This computes both.

  --params     the parameter count of the tied vs untied vocabulary matrices
  --score      for a hidden state equal to each token's embedding, which token each model scores highest
  --check      tying halves the parameters and makes input and output representations consistent

The embeddings and the untied unembedding are the fixture; every logit is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "model.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def logits(hidden, matrix):
    """One logit per token: the hidden state dotted with each token vector (row of the matrix)."""
    return [dot(hidden, row) for row in matrix]


def argmax(xs):
    return max(range(len(xs)), key=lambda i: xs[i])


def n_params(matrix):
    return len(matrix) * len(matrix[0])


def tied_matrix(embed):
    """Tied: the unembedding IS the embedding."""
    return embed


# ----------------------------------------------------------------- printing

def params_view(data):
    embed, unembed = data["embed"], data["unembed"]
    print("PARAMS — vocabulary matrix parameters, untied vs tied")
    print("-" * 52)
    print("  untied: embed %d + unembed %d = %d" % (n_params(embed), n_params(unembed), n_params(embed) + n_params(unembed)))
    print("  tied:   one shared matrix       = %d" % n_params(embed))
    print("-" * 52)
    print("  tying halves the vocabulary parameters.")


def score_view(data):
    embed, unembed = data["embed"], data["unembed"]
    print("SCORE — for hidden = each token's embedding, the top-scoring token")
    print("-" * 58)
    print("  hidden = E[t]   untied top    tied top   (want t)")
    for t in range(len(embed)):
        h = embed[t]
        print("  t=%d             %d             %d          %s"
              % (t, argmax(logits(h, unembed)), argmax(logits(h, tied_matrix(embed))), "ok" if argmax(logits(h, embed)) == t else "MISS"))
    print("-" * 58)
    print("  tied always recovers t; untied need not.")


def check(data):
    print("SELF-TEST — tying halves the parameters and makes input and output representations consistent")
    print("-" * 96)
    embed, unembed = data["embed"], data["unembed"]

    tied_halves_params = n_params(embed) == (n_params(embed) + n_params(unembed)) // 2
    print("  tied uses half the vocabulary parameters = %s (%d vs %d)"
          % (tied_halves_params, n_params(embed), n_params(embed) + n_params(unembed)))

    tied_self_consistent = all(argmax(logits(embed[t], tied_matrix(embed))) == t for t in range(len(embed)))
    print("  tied: hidden = E[t] always scores token t highest = %s" % tied_self_consistent)

    untied_can_disagree = any(argmax(logits(embed[t], unembed)) != t for t in range(len(embed)))
    print("  untied: hidden = E[t] can score a different token highest = %s" % untied_can_disagree)

    tied_reuses_embedding = tied_matrix(embed) is embed
    print("  tied: the unembedding is literally the embedding = %s" % tied_reuses_embedding)

    tied_fewer_params = n_params(embed) < n_params(embed) + n_params(unembed)
    print("  tied has fewer parameters than untied = %s (%d < %d)" % (tied_fewer_params, n_params(embed), n_params(embed) + n_params(unembed)))

    ok = tied_halves_params and tied_self_consistent and untied_can_disagree and tied_reuses_embedding and tied_fewer_params
    print("-" * 96)
    print("SELF-TEST %s  tied_halves_params=%s  tied_self_consistent=%s  untied_can_disagree=%s  tied_reuses_embedding=%s  tied_fewer_params=%s"
          % ("PASS" if ok else "FAIL", tied_halves_params, tied_self_consistent, untied_can_disagree, tied_reuses_embedding, tied_fewer_params))
    return ok


def main():
    p = argparse.ArgumentParser(description="Tie the output projection to the input embedding.")
    p.add_argument("--params", action="store_true")
    p.add_argument("--score", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("vocab=%d  dim=%d  file=%s  (the embeddings and untied unembedding are a fixture)"
          % (len(data["embed"]), len(data["embed"][0]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.params:
        params_view(data)
    elif args.score:
        score_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
