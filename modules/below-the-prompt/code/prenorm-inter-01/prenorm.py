"""Put the LayerNorm inside the residual branch (pre-norm), not on the residual stream (post-norm) -- pre-norm leaves a clean identity path so gradients survive depth, while post-norm attenuates them at every layer and destabilizes deep training.

A transformer layer has three pieces: a sublayer (attention or MLP), a residual connection, and a normalization. The residual connection is the highway that lets gradients reach early layers -- an identity path that adds the sublayer's output to the input rather than replacing it. Where you put the normalization relative to that highway is the whole question, and the original Transformer put it in the wrong place for depth.

Post-norm, the original design, computes x = LayerNorm(x + sublayer(x)). The normalization sits on the main residual stream, so on the backward pass every gradient flowing toward earlier layers must pass through the norm's Jacobian, once per layer. That Jacobian scales the gradient by a factor that is typically below one, so the gradient reaching the first layers is multiplied by that factor once for each layer above them -- and a number below one raised to the depth shrinks toward zero. Deep post-norm transformers therefore suffer vanishing gradients at the bottom, train unstably, and need a carefully tuned learning-rate warmup to converge at all.

Pre-norm moves the norm inside the branch: x = x + sublayer(LayerNorm(x)). Now the residual stream from input to output is a pure identity path -- nothing on it scales the gradient -- and the normalization only affects the sublayer's own input, off to the side. The gradient flows back along the identity highway undiminished, its multiplier on the residual path exactly one regardless of depth, so a deep pre-norm transformer trains stably without the delicate warmup post-norm demands. This is why essentially every modern large transformer uses pre-norm.

The rule: place the normalization inside the residual branch (pre-norm: x + sublayer(norm(x))), not on the residual stream (post-norm: norm(x + sublayer(x))), because post-norm's norm sits on the identity path and multiplies the backward gradient by a sub-unit factor at every layer -- vanishing it with depth -- while pre-norm leaves the identity path clean so the gradient survives to the first layer.

On this fixture the post-norm residual path attenuates the gradient by 0.85 per layer while pre-norm keeps it at 1.0. At depth 6 the post-norm input gradient is already 0.38; by depth 24 it is 0.02, below the vanish threshold; pre-norm stays at 1.0 at every depth. This computes both. (The 0.85 is a stylized per-layer attenuation standing in for the norm's Jacobian; the identity-vs-attenuated contrast is the real mechanism.)

  --depth     the input-gradient magnitude of each variant at each depth
  --vanish    the depth at which each variant's gradient falls below the vanish threshold
  --check     post-norm's gradient vanishes with depth while pre-norm's stays constant

the multipliers, depths, and threshold are the fixture; the depth-wise gradient magnitudes are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "prenorm.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def input_gradient(multiplier, depth):
    """Gradient magnitude reaching the first layer: the per-layer residual multiplier raised to the depth."""
    return multiplier ** depth


def vanish_depth(multiplier, threshold, max_depth=512):
    """Smallest depth at which the input gradient falls below the threshold (None if it never does)."""
    if multiplier >= 1.0:
        return None
    d = 1
    while d <= max_depth:
        if input_gradient(multiplier, d) < threshold:
            return d
        d += 1
    return None


# ----------------------------------------------------------------- printing

def depth_view(data):
    mult = data["residual_multiplier"]
    print("DEPTH — input-gradient magnitude by depth (pre-norm mult %.2f, post-norm mult %.2f)"
          % (mult["pre_norm"], mult["post_norm"]))
    print("-" * 56)
    print("  depth   pre-norm   post-norm")
    for d in data["depths"]:
        print("  %-5d   %-8.4f   %.4f" % (d, input_gradient(mult["pre_norm"], d), input_gradient(mult["post_norm"], d)))
    print("-" * 56)
    print("  pre-norm's identity path keeps the gradient at 1.0; post-norm's decays with depth")


def vanish_view(data):
    mult, thr = data["residual_multiplier"], data["vanish_threshold"]
    print("VANISH — depth at which the input gradient drops below %.2f" % thr)
    print("-" * 56)
    for name in ("pre_norm", "post_norm"):
        vd = vanish_depth(mult[name], thr)
        print("  %-10s  vanishes at depth %s" % (name, vd if vd is not None else "never"))
    print("-" * 56)
    print("  post-norm hits the vanishing regime at moderate depth; pre-norm never does")


def check(data):
    print("SELF-TEST — post-norm's gradient vanishes with depth while pre-norm's stays constant")
    print("-" * 116)
    mult, thr = data["residual_multiplier"], data["vanish_threshold"]
    depths = data["depths"]
    pre, post = mult["pre_norm"], mult["post_norm"]

    prenorm_identity_path = pre == 1.0
    print("  pre-norm's residual path is a pure identity (multiplier 1.0) = %s" % prenorm_identity_path)

    postnorm_attenuates = post < 1.0
    print("  post-norm's residual path attenuates the gradient (multiplier < 1) = %s (%.2f)" % (postnorm_attenuates, post))

    prenorm_gradient_stable = all(abs(input_gradient(pre, d) - 1.0) < 1e-9 for d in depths)
    print("  pre-norm's input gradient stays 1.0 at every depth = %s" % prenorm_gradient_stable)

    postnorm_gradient_decays = input_gradient(post, depths[-1]) < input_gradient(post, depths[0])
    print("  post-norm's input gradient shrinks with depth = %s (%.4f -> %.4f)"
          % (postnorm_gradient_decays, input_gradient(post, depths[0]), input_gradient(post, depths[-1])))

    postnorm_vanishes = input_gradient(post, depths[-1]) < thr
    print("  post-norm's gradient falls below the vanish threshold at the deepest network = %s (%.4f < %.2f)"
          % (postnorm_vanishes, input_gradient(post, depths[-1]), thr))

    prenorm_survives_where_post_vanishes = input_gradient(pre, depths[-1]) >= thr and postnorm_vanishes
    print("  pre-norm survives at a depth where post-norm has vanished = %s" % prenorm_survives_where_post_vanishes)

    ok = (prenorm_identity_path and postnorm_attenuates and prenorm_gradient_stable
          and postnorm_gradient_decays and postnorm_vanishes and prenorm_survives_where_post_vanishes)
    print("-" * 116)
    print("SELF-TEST %s  prenorm_identity_path=%s  postnorm_attenuates=%s  prenorm_gradient_stable=%s  postnorm_gradient_decays=%s  postnorm_vanishes=%s  prenorm_survives_where_post_vanishes=%s"
          % ("PASS" if ok else "FAIL", prenorm_identity_path, postnorm_attenuates, prenorm_gradient_stable, postnorm_gradient_decays, postnorm_vanishes, prenorm_survives_where_post_vanishes))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pre-norm vs post-norm: place the normalization inside the residual branch (pre-norm: x + sublayer(norm(x))), not on the residual stream (post-norm: norm(x + sublayer(x))), because post-norm's norm sits on the identity path and multiplies the backward gradient by a sub-unit factor at every layer -- vanishing it with depth -- while pre-norm leaves the identity path clean so the gradient survives to the first layer.")
    p.add_argument("--depth", action="store_true")
    p.add_argument("--vanish", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("residual_multiplier=%s  depths=%s  vanish_threshold=%.2f  file=%s  (all fixture)"
          % (data["residual_multiplier"], data["depths"], data["vanish_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.depth:
        depth_view(data)
    elif args.vanish:
        vanish_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
