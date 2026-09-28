"""Self-attention with no positional information is permutation-equivariant: reorder the input tokens and the outputs come out the same, merely reordered the same way -- so the model cannot tell 'dog bites man' from 'man bites dog', which is the entire reason positional encodings exist.

Self-attention computes each token's output as a softmax-weighted average of every token's value vector, and the weights come from dot products between tokens. Read the formula and notice what is missing: nothing refers to where a token sits, only to which tokens are present and how they relate. Position is simply not an input.

The consequence is exact. Permute the input rows by any permutation pi and every output row comes out permuted by the same pi, otherwise unchanged: attn(permute(X)) equals permute(attn(X)). The attention operation commutes with reordering. So the set of output vectors for a sentence and for any anagram of that sentence is identical -- the same vectors in a different order -- and any order-blind readout collapses the difference entirely. Mean-pool the outputs and 'dog bites man' and 'man bites dog' return the byte-identical vector, because pooling averages the same three vectors either way.

That is a model that cannot represent word order at all, and word order is most of syntax. The fix is to inject position before attention: add a per-position vector p_i to whatever token lands at position i. Now position 0 always contributes p_0, so when you permute the tokens the augmented input is no longer a permutation of the original -- the token that moves to position 0 picks up p_0, not the vector it carried before -- and the outputs genuinely differ. The two word orders become distinguishable, which is what every positional scheme (learned embeddings, RoPE, ALiBi) exists to accomplish.

On this fixture the tokens are orthonormal one-hot vectors, the sequence 'dog bites man' is permuted by reversing it to 'man bites dog', and fixed position vectors are available. The code runs attention with and without positions and checks equivariance and pooled invariance both ways.

  --nopos    attention without positions: the reversed sequence gives the reversed outputs, and mean pooling is identical
  --withpos  attention after adding position vectors: the reversed sequence gives different outputs and a different pooled vector
  --check    without positions attention is permutation-equivariant and the pooled readout is order-invariant, while adding positions breaks both -- the outputs and the pooled vector now depend on order

the tokens, the sequence, the permutation, and the position vectors are the fixture; every attention output, pooled vector, and equivariance comparison is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "permequiv.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def softmax(xs):
    hi = max(xs)
    exps = [math.exp(x - hi) for x in xs]
    tot = sum(exps)
    return [e / tot for e in exps]


def attention(X):
    """Scaled dot-product self-attention with query=key=value=X (no positional term anywhere)."""
    d = len(X[0])
    scale = math.sqrt(d)
    out = []
    for xi in X:
        scores = [dot(xi, xj) / scale for xj in X]
        w = softmax(scores)
        out.append([sum(w[j] * X[j][k] for j in range(len(X))) for k in range(d)])
    return out


def permute(rows, perm):
    """Reorder the rows: new row i is old row perm[i]."""
    return [rows[p] for p in perm]


def add_positions(X, P):
    """Add the position vector P[i] to whatever token sits at position i."""
    return [[x + p for x, p in zip(X[i], P[i])] for i in range(len(X))]


def mean_pool(Y):
    """Average the output vectors -- an order-blind readout."""
    d = len(Y[0])
    return [sum(row[k] for row in Y) / len(Y) for k in range(d)]


def rows_close(A, B, tol=1e-9):
    return all(abs(a - b) < tol for ra, rb in zip(A, B) for a, b in zip(ra, rb))


# ----------------------------------------------------------------- printing

def _seq_rows(data, seq):
    return [data["tokens"][t] for t in seq]


def _fmt(v):
    return "[" + ", ".join("%.3f" % x for x in v) + "]"


def nopos_view(data):
    seq = data["sequence"]
    perm = data["permutation"]
    rseq = [seq[p] for p in perm]
    X = _seq_rows(data, seq)
    Xr = _seq_rows(data, rseq)
    out, outr = attention(X), attention(Xr)
    print("NO-POS — attention on %s vs its reversal %s" % (seq, rseq))
    print("-" * 72)
    for t, o in zip(seq, out):
        print("  out[%-6s] = %s" % (t, _fmt(o)))
    print("  reversed sequence outputs equal the reversed original outputs? %s" % rows_close(outr, permute(out, perm)))
    print("  mean pool (original) = %s" % _fmt(mean_pool(out)))
    print("  mean pool (reversed) = %s" % _fmt(mean_pool(outr)))
    print("-" * 72)
    print("  no position enters attention, so reordering only reorders the outputs -- the pool is identical")


def withpos_view(data):
    seq = data["sequence"]
    perm = data["permutation"]
    rseq = [seq[p] for p in perm]
    P = data["position_vectors"]
    X = add_positions(_seq_rows(data, seq), P)
    Xr = add_positions(_seq_rows(data, rseq), P)
    out, outr = attention(X), attention(Xr)
    print("WITH-POS — add position vectors, then attention on %s vs %s" % (seq, rseq))
    print("-" * 72)
    print("  mean pool (original) = %s" % _fmt(mean_pool(out)))
    print("  mean pool (reversed) = %s" % _fmt(mean_pool(outr)))
    print("  reversed outputs still equal the reversed original outputs? %s" % rows_close(outr, permute(out, perm)))
    print("-" * 72)
    print("  position 0 always adds p_0, so reordering changes the augmented input -- the orders now differ")


def check(data):
    print("SELF-TEST — without positions attention is permutation-equivariant and the pooled readout is order-invariant, while adding positions breaks both")
    print("-" * 112)
    seq = data["sequence"]
    perm = data["permutation"]
    rseq = [seq[p] for p in perm]
    P = data["position_vectors"]

    X = _seq_rows(data, seq)
    Xr = _seq_rows(data, rseq)
    out, outr = attention(X), attention(Xr)

    equivariant = rows_close(outr, permute(out, perm))
    print("  no-pos: attn(reverse(X)) == reverse(attn(X)) (permutation-equivariant) = %s" % equivariant)

    pooled_invariant = rows_close([mean_pool(out)], [mean_pool(outr)])
    print("  no-pos: mean pool is identical for both orders (order-invariant) = %s" % pooled_invariant)

    Xp = add_positions(X, P)
    Xrp = add_positions(Xr, P)
    outp, outrp = attention(Xp), attention(Xrp)

    equivariance_broken = not rows_close(outrp, permute(outp, perm))
    print("  with-pos: attn(reverse) != reverse(attn) (equivariance broken) = %s" % equivariance_broken)

    pooled_differs = not rows_close([mean_pool(outp)], [mean_pool(outrp)])
    print("  with-pos: mean pool differs between the two orders (order now matters) = %s" % pooled_differs)

    ok = (equivariant and pooled_invariant and equivariance_broken and pooled_differs)
    print("-" * 112)
    print("SELF-TEST %s  equivariant=%s  pooled_invariant=%s  equivariance_broken=%s  pooled_differs=%s"
          % ("PASS" if ok else "FAIL", equivariant, pooled_invariant, equivariance_broken, pooled_differs))
    return ok


def main():
    p = argparse.ArgumentParser(description="Permutation equivariance of self-attention: with no positional information, attention commutes with reordering the tokens -- attn(permute(X)) = permute(attn(X)) -- so a sentence and any anagram of it produce the same output vectors and an order-blind readout cannot tell them apart, which is precisely why positional encodings are added; injecting a per-position vector before attention breaks the symmetry and makes word order representable.")
    p.add_argument("--nopos", action="store_true")
    p.add_argument("--withpos", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("sequence=%s  permutation=%s  d=%d  file=%s"
          % (data["sequence"], data["permutation"], len(next(iter(data["tokens"].values()))), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.nopos:
        nopos_view(data)
    elif args.withpos:
        withpos_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
