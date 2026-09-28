"""Scale token embeddings by sqrt(d_model) before adding positional encodings -- otherwise the position signal drowns out which token it is.

The input to a Transformer's first layer is a sum: the token embedding (which token this is) plus the positional encoding (where in the sequence it sits). For that sum to carry both pieces of information, the two addends have to be of COMPARABLE magnitude -- if one is much larger than the other, it dominates the vector and the smaller one becomes a rounding error the model can barely read. And by default they are not comparable. Token embeddings are initialized small: with the common scheme each component has magnitude around 1/sqrt(d_model), so the whole embedding vector has a norm of about 1, regardless of dimension. Sinusoidal positional encodings, by contrast, have components that swing across [-1, 1], so their vector norm grows with the dimension. The bigger the model, the more the positional encoding out-sizes the token embedding.

Add them as-is and the result is dominated by position: the sum points almost entirely in the positional encoding's direction, and the token identity is a faint perturbation on top. The model receives 'position 5, and (barely) some token' when it needed 'this token, at position 5' with both legible. The information about WHICH token this is -- the thing the whole model is built to process -- arrives attenuated relative to where it is.

The fix in the original Transformer is a single multiply: scale the token embedding by sqrt(d_model) before adding the positional encoding. That raises the embedding's norm from about 1 to about sqrt(d_model), which is the same order as the positional encoding's norm, so the two contribute on equal footing and the sum carries token and position with comparable weight. It is a small, easily-overlooked line -- one factor of sqrt(d_model) -- and leaving it out quietly degrades the model by drowning token identity in positional signal.

The rule: multiply token embeddings by sqrt(d_model) before adding positional encodings, because embeddings are initialized to a norm of about 1 while positional encodings have a norm that grows with dimension -- so without the scale the position signal dominates the sum and token identity is attenuated, while scaling makes the two comparable.

On this fixture the embedding has norm 1.0 and the positional encoding has norm 2.0, so unscaled the embedding is only half the positional magnitude (ratio 0.5). Multiplying by sqrt(d_model)=2 raises the embedding norm to 2.0, equal to the positional norm (ratio 1.0). This computes both.

  --norms     the embedding and positional norms, unscaled vs scaled by sqrt(d_model)
  --sum       the input sum without and with scaling, and how much of it is token vs position
  --check     unscaled, the embedding is swamped by the positional signal; scaling by sqrt(d_model) makes them comparable

d_model, embedding, and positional are the fixture; the scale, scaled embedding, and every norm and ratio are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "embscale.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def norm(vec):
    return math.sqrt(sum(x * x for x in vec))


def scale_factor(d_model):
    return math.sqrt(d_model)


def scaled_embedding(embedding, d_model):
    s = scale_factor(d_model)
    return [x * s for x in embedding]


def add(a, b):
    return [x + y for x, y in zip(a, b)]


# ----------------------------------------------------------------- printing

def norms_view(data):
    emb, pos, d = data["embedding"], data["positional"], data["d_model"]
    se = scaled_embedding(emb, d)
    print("NORMS — embedding vs positional magnitude (d_model=%d, scale=%.1f)" % (d, scale_factor(d)))
    print("-" * 62)
    print("  positional norm            = %.2f" % norm(pos))
    print("  embedding norm (unscaled)  = %.2f   (ratio to positional %.2f)" % (norm(emb), norm(emb) / norm(pos)))
    print("  embedding norm (x sqrt d)  = %.2f   (ratio to positional %.2f)" % (norm(se), norm(se) / norm(pos)))
    print("-" * 62)
    print("  scaling raises the embedding to the positional encoding's magnitude")


def sum_view(data):
    emb, pos, d = data["embedding"], data["positional"], data["d_model"]
    se = scaled_embedding(emb, d)
    unscaled_sum = add(emb, pos)
    scaled_sum = add(se, pos)
    print("SUM — the first-layer input (embedding + positional)")
    print("-" * 60)
    print("  unscaled: %s   token share of norm = %.0f%%" % (unscaled_sum, 100 * norm(emb) / (norm(emb) + norm(pos))))
    print("  scaled:   %s   token share of norm = %.0f%%" % (scaled_sum, 100 * norm(se) / (norm(se) + norm(pos))))
    print("-" * 60)
    print("  unscaled the token is the minority of the signal; scaled it is an equal half")


def check(data):
    print("SELF-TEST — unscaled, the embedding is swamped by the positional signal; scaling by sqrt(d_model) makes them comparable")
    print("-" * 122)
    emb, pos, d = data["embedding"], data["positional"], data["d_model"]
    se = scaled_embedding(emb, d)
    unscaled_ratio = norm(emb) / norm(pos)
    scaled_ratio = norm(se) / norm(pos)

    scale_is_sqrt_d = abs(scale_factor(d) - math.sqrt(d)) < 1e-9
    print("  the scale factor is sqrt(d_model) = %s (%.2f)" % (scale_is_sqrt_d, scale_factor(d)))

    embedding_underweighted = norm(emb) < norm(pos)
    print("  unscaled, the embedding norm is below the positional norm = %s (%.2f < %.2f)" % (embedding_underweighted, norm(emb), norm(pos)))

    positional_dominates_unscaled = unscaled_ratio < 0.75
    print("  unscaled, the positional signal dominates the sum = %s (embedding is %.0f%% of positional)" % (positional_dominates_unscaled, 100 * unscaled_ratio))

    scaling_raises_embedding = norm(se) > norm(emb)
    print("  scaling raises the embedding norm = %s (%.2f -> %.2f)" % (scaling_raises_embedding, norm(emb), norm(se)))

    comparable_after_scaling = 0.75 <= scaled_ratio <= 1.33
    print("  scaled, the embedding and positional norms are comparable = %s (ratio %.2f)" % (comparable_after_scaling, scaled_ratio))

    ratio_moves_toward_one = abs(scaled_ratio - 1) < abs(unscaled_ratio - 1)
    print("  scaling moves the ratio toward 1 (equal footing) = %s (%.2f -> %.2f)" % (ratio_moves_toward_one, unscaled_ratio, scaled_ratio))

    ok = (scale_is_sqrt_d and embedding_underweighted and positional_dominates_unscaled and scaling_raises_embedding
          and comparable_after_scaling and ratio_moves_toward_one)
    print("-" * 122)
    print("SELF-TEST %s  scale_is_sqrt_d=%s  embedding_underweighted=%s  positional_dominates_unscaled=%s  scaling_raises_embedding=%s  comparable_after_scaling=%s  ratio_moves_toward_one=%s"
          % ("PASS" if ok else "FAIL", scale_is_sqrt_d, embedding_underweighted, positional_dominates_unscaled, scaling_raises_embedding, comparable_after_scaling, ratio_moves_toward_one))
    return ok


def main():
    p = argparse.ArgumentParser(description="Embedding scaling: multiply token embeddings by sqrt(d_model) before adding positional encodings, because embeddings are initialized to a norm of about 1 while positional encodings have a norm that grows with dimension -- so without the scale the position signal dominates the sum and token identity is attenuated, while scaling makes the two comparable.")
    p.add_argument("--norms", action="store_true")
    p.add_argument("--sum", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("d_model=%d  embedding=%s  positional=%s  file=%s  (the vectors are a fixture)"
          % (data["d_model"], data["embedding"], data["positional"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.norms:
        norms_view(data)
    elif args.sum:
        sum_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
