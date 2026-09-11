"""Apply weight decay directly to the weights (AdamW), not as an L2 term in the loss -- or Adam's per-parameter scaling divides the decay by each weight's gradient RMS and under-regularizes the high-gradient parameters.

Adam adapts the step size per parameter. It keeps a running average of each parameter's squared gradients -- the second moment v -- and divides the update by sqrt(v), so a parameter whose gradients are consistently large takes proportionally smaller steps, and a parameter with small gradients takes larger ones. That adaptivity is the whole point of Adam.

Weight decay wants the opposite of adaptivity: pull every weight toward zero by the same fraction each step, a uniform regularization that does not care how big a parameter's gradients are. The trouble comes from how weight decay is implemented. The tempting way is to add an L2 penalty to the loss, because mathematically the gradient of (wd/2)*w^2 is wd*w, so adding L2 to the loss adds wd*w to the gradient. But now that decay term is part of the gradient, and Adam divides the whole gradient by sqrt(v). The decay a weight actually receives becomes (lr * wd * w) / sqrt(v): inversely scaled by the parameter's gradient RMS. High-gradient parameters -- exactly the ones a big model has many of -- get their decay shrunk, while low-gradient parameters get more. The uniform regularization you asked for arrives wildly non-uniform.

AdamW decouples the decay from the gradient. It runs the Adam update on the raw loss gradient (no L2 term), and separately subtracts lr * wd * w from each weight. That decay is outside the adaptive scaling, so every weight decays by the same fraction lr*wd regardless of its gradient history -- the uniform regularization restored. The fix is a one-line change in where the decay is applied, and it is why AdamW, not Adam-with-L2, is the default optimizer for training modern models.

The rule: decouple weight decay from the gradient (AdamW: w -= lr*wd*w applied directly), rather than adding L2 to the loss, because coupling it makes Adam divide the decay by each parameter's gradient RMS -- under-regularizing high-gradient parameters and over-regularizing low-gradient ones instead of decaying every weight uniformly.

On this fixture two parameters start at the same weight; 'steep' has 16x the second moment of 'flat' (4x the gradient RMS). Coupled L2 decays steep by 0.0025 and flat by 0.01 -- four times less for steep; AdamW decays both by 0.01. This computes both.

  --decay     each parameter's gradient RMS and the decay it receives under Adam+L2 vs AdamW
  --uniform   whether the decay is uniform across parameters, each method
  --check     coupled L2 makes decay depend on the gradient RMS (uneven); AdamW decays every weight by the same fraction

lr, wd, and the parameters are the fixture; the decay under each method is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "adamw.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rms(param):
    return math.sqrt(param["v"])


def coupled_decay(param, lr, wd):
    """L2-in-loss: the decay term wd*w flows through Adam's 1/sqrt(v) scaling."""
    return lr * wd * param["w"] / rms(param)


def decoupled_decay(param, lr, wd):
    """AdamW: decay applied directly to the weight, outside the adaptive scaling."""
    return lr * wd * param["w"]


# ----------------------------------------------------------------- printing

def decay_view(data):
    lr, wd = data["lr"], data["wd"]
    print("DECAY — the decay each parameter receives (lr=%.2f, wd=%.2f)" % (lr, wd))
    print("-" * 62)
    print("  param   weight   grad RMS   Adam+L2 decay   AdamW decay")
    for name, p in data["params"].items():
        print("  %-6s  %.2f     %.2f       %.4f          %.4f"
              % (name, p["w"], rms(p), coupled_decay(p, lr, wd), decoupled_decay(p, lr, wd)))
    print("-" * 62)
    print("  Adam+L2 shrinks the steep parameter's decay by its gradient RMS; AdamW does not")


def uniform_view(data):
    lr, wd = data["lr"], data["wd"]
    ps = list(data["params"].values())
    c = [coupled_decay(p, lr, wd) for p in ps]
    d = [decoupled_decay(p, lr, wd) for p in ps]
    print("UNIFORM — is the decay the same across parameters (same weight)?")
    print("-" * 60)
    print("  Adam+L2 decays: %s   ratio %.1fx" % ([round(x, 4) for x in c], max(c) / min(c)))
    print("  AdamW decays:   %s   ratio %.1fx" % ([round(x, 4) for x in d], max(d) / min(d)))
    print("-" * 60)
    print("  AdamW's decay is uniform; Adam+L2's varies with the gradient RMS")


def check(data):
    print("SELF-TEST — coupled L2 makes decay depend on the gradient RMS (uneven); AdamW decays every weight by the same fraction")
    print("-" * 120)
    lr, wd = data["lr"], data["wd"]
    steep, flat = data["params"]["steep"], data["params"]["flat"]

    steep_has_bigger_gradients = rms(steep) > rms(flat)
    print("  the steep parameter has a larger gradient RMS = %s (%.1f vs %.1f)" % (steep_has_bigger_gradients, rms(steep), rms(flat)))

    coupled_uneven = abs(coupled_decay(steep, lr, wd) - coupled_decay(flat, lr, wd)) > 1e-9
    print("  Adam+L2 decays the two parameters unequally = %s (%.4f vs %.4f)"
          % (coupled_uneven, coupled_decay(steep, lr, wd), coupled_decay(flat, lr, wd)))

    coupled_underdecays_steep = coupled_decay(steep, lr, wd) < coupled_decay(flat, lr, wd)
    print("  Adam+L2 gives the high-gradient parameter LESS decay = %s" % coupled_underdecays_steep)

    adamw_uniform = abs(decoupled_decay(steep, lr, wd) - decoupled_decay(flat, lr, wd)) < 1e-9
    print("  AdamW decays both equally (same weight) = %s (%.4f == %.4f)"
          % (adamw_uniform, decoupled_decay(steep, lr, wd), decoupled_decay(flat, lr, wd)))

    steep_underregularized = coupled_decay(steep, lr, wd) < decoupled_decay(steep, lr, wd)
    print("  under Adam+L2 the steep parameter is under-regularized vs AdamW = %s (%.4f < %.4f)"
          % (steep_underregularized, coupled_decay(steep, lr, wd), decoupled_decay(steep, lr, wd)))

    ok = (steep_has_bigger_gradients and coupled_uneven and coupled_underdecays_steep
          and adamw_uniform and steep_underregularized)
    print("-" * 120)
    print("SELF-TEST %s  steep_has_bigger_gradients=%s  coupled_uneven=%s  coupled_underdecays_steep=%s  adamw_uniform=%s  steep_underregularized=%s"
          % ("PASS" if ok else "FAIL", steep_has_bigger_gradients, coupled_uneven, coupled_underdecays_steep, adamw_uniform, steep_underregularized))
    return ok


def main():
    p = argparse.ArgumentParser(description="Decoupled weight decay (AdamW): apply weight decay directly to the weights (w -= lr*wd*w), not as an L2 term in the loss, because coupling it makes Adam divide the decay by each parameter's gradient RMS -- under-regularizing high-gradient parameters and over-regularizing low-gradient ones instead of decaying every weight uniformly.")
    p.add_argument("--decay", action="store_true")
    p.add_argument("--uniform", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("lr=%.2f  wd=%.2f  params=%s  file=%s  (the parameters are a fixture)"
          % (data["lr"], data["wd"], {k: (v["w"], v["v"]) for k, v in data["params"].items()}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.decay:
        decay_view(data)
    elif args.uniform:
        uniform_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
