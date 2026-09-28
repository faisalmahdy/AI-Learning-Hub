"""Clip the gradient's global norm, or one bad batch blows up the update and corrupts every weight.

Training is mostly small, well-behaved gradient steps -- until it isn't. A rare batch (a corrupted example,
an unlucky loss spike, a numerical edge) produces a gradient with an enormous norm, and a plain SGD step
scales the update by that norm: the weights lurch a huge distance in one step, undoing thousands of good
updates and often sending the loss to NaN. You cannot lower the learning rate enough to survive the spike
without making every normal step uselessly tiny. The problem is not the average gradient; it is the tail.

Gradient clipping by global norm caps the tail without touching the body. Compute the norm of the whole
gradient vector; if it exceeds a threshold c, rescale the entire vector by c / norm so its norm becomes
exactly c. Every component is scaled by the same factor, so the direction is preserved perfectly -- you
still step the way the gradient pointed, just no farther than c. Normal steps (norm below c) pass through
untouched. One line turns a training run that dies on the first bad batch into one that shrugs it off.

The tempting shortcut -- clip each component to [-c, c] independently (elementwise) -- is wrong, because
it changes the direction. Clamping the biggest components more than the small ones tilts the update vector
away from the true gradient, so you take a step that is not even downhill. Global-norm clipping scales
uniformly and keeps the direction; elementwise clamping distorts it.

On this fixture normal batches have gradient norm 0.5 and one spike batch has norm 100, with a clip
threshold of 1.0 and learning rate 0.1. Unclipped, the spike step moves the weights by 10.0 -- 200 times a
normal step -- and leaves them at norm 10.20. Global-norm clipping caps that step at 0.1 and keeps the
direction (cosine 1.000); elementwise clamping distorts it (cosine 0.990) and does not even respect the
threshold. This computes all three.

  --steps      the per-step update size and running weight norm, unclipped vs global-norm clipped
  --direction  the spike gradient under global-norm vs elementwise clipping: norm and direction kept?
  --check      unclipped blows up on the spike; global-norm clipping caps the step and preserves direction

The gradients, threshold, and learning rate are the fixture; every update is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "grads.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def scale(v, f):
    return [x * f for x in v]


def clip_global(g, c):
    """Rescale the whole vector so its norm is at most c -- same direction, capped length."""
    n = norm(g)
    return scale(g, c / n) if n > c else list(g)


def clip_elementwise(g, c):
    """Clamp each component to [-c, c] independently -- changes the direction (the wrong way)."""
    return [max(-c, min(c, x)) for x in g]


def cosine(a, b):
    na, nb = norm(a), norm(b)
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def run(grads, lr, c, clipper):
    """SGD trajectory: return the per-step update norms and the final weight vector."""
    w = [0.0, 0.0]
    steps = []
    for g in grads:
        gc = clipper(g, c) if clipper else g
        update = scale(gc, lr)
        w = [wi - ui for wi, ui in zip(w, update)]
        steps.append({"grad_norm": norm(g), "step": norm(update), "w_norm": norm(w)})
    return steps, w


# ----------------------------------------------------------------- printing

def steps_view(data):
    grads, lr, c = data["gradients"], data["lr"], data["clip"]
    print("STEPS — per-step update size and running weight norm (lr %.2f, clip %.1f)" % (lr, c))
    print("-" * 62)
    for name, clipper in (("UNCLIPPED", None), ("GLOBAL-NORM CLIP", clip_global)):
        steps, w = run(grads, lr, c, clipper)
        print("  %s" % name)
        for i, s in enumerate(steps):
            tag = "  <-- spike batch" if s["grad_norm"] > c else ""
            print("    batch %d  grad_norm %7.2f  update %6.3f  |w| %6.3f%s"
                  % (i, s["grad_norm"], s["step"], s["w_norm"], tag))
        print("    final |w| = %.3f" % norm(w))
        print("")


def direction_view(data):
    grads, c = data["gradients"], data["clip"]
    spike = max(grads, key=norm)
    g_glob = clip_global(spike, c)
    g_elem = clip_elementwise(spike, c)
    print("DIRECTION — the spike gradient %s under each clip (threshold %.1f)" % (spike, c))
    print("-" * 62)
    print("  global-norm:  %s   norm %.3f   cosine-to-original %.3f" % ([round(x, 3) for x in g_glob], norm(g_glob), cosine(g_glob, spike)))
    print("  elementwise:  %s   norm %.3f   cosine-to-original %.3f" % ([round(x, 3) for x in g_elem], norm(g_elem), cosine(g_elem, spike)))
    print("-" * 62)
    print("  global-norm caps the norm at the threshold and keeps the direction; elementwise does neither.")


def check(data):
    print("SELF-TEST — unclipped blows up on the spike; global-norm clipping caps the step and preserves direction")
    print("-" * 104)
    grads, lr, c = data["gradients"], data["lr"], data["clip"]
    spike = max(grads, key=norm)
    normal = min(norm(g) for g in grads)

    unclipped_steps, w_unclipped = run(grads, lr, c, None)
    clipped_steps, w_clipped = run(grads, lr, c, clip_global)
    max_unclipped = max(s["step"] for s in unclipped_steps)
    max_clipped = max(s["step"] for s in clipped_steps)

    unclipped_blows_up = max_unclipped > 100 * (normal * lr)
    print("  unclipped's biggest step dwarfs a normal step = %s (%.3f vs %.3f)" % (unclipped_blows_up, max_unclipped, normal * lr))

    clip_caps_step = max_clipped <= c * lr + 1e-9
    print("  global-norm clip caps every step at threshold*lr = %s (max %.3f <= %.3f)" % (clip_caps_step, max_clipped, c * lr))

    clip_bounds_weights = norm(w_clipped) < norm(w_unclipped) / 10
    print("  clipped weights stay bounded, unclipped do not = %s (|w| %.3f vs %.3f)" % (clip_bounds_weights, norm(w_clipped), norm(w_unclipped)))

    global_keeps_direction = abs(cosine(clip_global(spike, c), spike) - 1.0) < 1e-9
    print("  global-norm clip preserves the gradient direction = %s (cosine %.4f)" % (global_keeps_direction, cosine(clip_global(spike, c), spike)))

    elementwise_distorts = cosine(clip_elementwise(spike, c), spike) < 1.0 - 1e-6
    print("  elementwise clamp distorts the direction = %s (cosine %.4f)" % (elementwise_distorts, cosine(clip_elementwise(spike, c), spike)))

    ok = unclipped_blows_up and clip_caps_step and clip_bounds_weights and global_keeps_direction and elementwise_distorts
    print("-" * 104)
    print("SELF-TEST %s  unclipped_blows_up=%s  clip_caps_step=%s  clip_bounds_weights=%s  global_keeps_direction=%s  elementwise_distorts=%s"
          % ("PASS" if ok else "FAIL", unclipped_blows_up, clip_caps_step, clip_bounds_weights, global_keeps_direction, elementwise_distorts))
    return ok


def main():
    p = argparse.ArgumentParser(description="Clip the gradient's global norm to survive a rare exploding-gradient batch.")
    p.add_argument("--steps", action="store_true")
    p.add_argument("--direction", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("batches=%d  lr=%.2f  clip=%.1f  file=%s  (the gradients, lr, and threshold are a fixture)"
          % (len(data["gradients"]), data["lr"], data["clip"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.steps:
        steps_view(data)
    elif args.direction:
        direction_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
