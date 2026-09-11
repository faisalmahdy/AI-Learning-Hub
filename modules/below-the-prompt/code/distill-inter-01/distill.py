"""Distill from soft targets, not hard labels -- the teacher's wrong-class probabilities are the lesson.

A big teacher model, shown an image of a cat, does not just output 'cat'. It outputs a whole
distribution: cat 0.70, dog 0.25, car 0.03, ship 0.02. The hard label -- the single argmax,
'cat' -- throws away everything but the winner. But the rest of that distribution is
information: it says a cat looks a lot like a dog and nothing like a ship, and that this
particular image was a somewhat uncertain cat. Geoffrey Hinton called this the teacher's 'dark
knowledge', and distillation works by training the student on the full soft distribution rather
than the one-hot hard label, because the soft target teaches the similarity structure the hard
label deletes.

The loss is exact and easy to see. Hard labels collapse every example that shares an argmax into
the same one-hot target, so a confident cat and a barely-a-cat become identical training
signals, and the second-choice class -- the model's read on what the image is confusable with --
is erased. Soft targets keep all of it. On this fixture three examples all hard-label 'cat' but
carry distinct soft distributions and different runner-up classes; hard labels collapse the
three to one signal and drop 0.30, 0.10, and 0.50 of non-top probability mass, while soft
targets preserve each example's uncertainty and its confusable class. This computes the dark
knowledge hard labels discard and the distinctions they collapse.

  --targets   each example's soft distribution, hard label, runner-up, dark-knowledge mass, entropy
  --loss      what hard labels collapse and erase that soft targets keep
  --check     hard labels collapse same-argmax examples and drop the dark knowledge soft targets keep

The teacher's soft distributions are the fixture; every quantity is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "targets.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- reading a soft target

def hard_label(dist, classes):
    """The one-hot target: the single most probable class (all a hard label keeps)."""
    return classes[max(range(len(dist)), key=lambda i: dist[i])]


def runner_up(dist, classes):
    """The teacher's second choice -- the confusable class, dark knowledge a hard label erases."""
    order = sorted(range(len(dist)), key=lambda i: -dist[i])
    return classes[order[1]]


def dark_knowledge(dist):
    """Probability mass on the NON-top classes -- exactly what the hard label zeros out."""
    return round(1 - max(dist), 4)


def entropy(dist):
    """Uncertainty in the soft target (bits); a hard label always reports 0."""
    return round(-sum(p * math.log2(p) for p in dist if p > 0), 4)


# ------------------------------------------------------------- what hard labels collapse

def collapsed_groups(examples, classes):
    """Groups of examples that share a hard label but have DIFFERENT soft targets -- collapsed to one signal."""
    groups = {}
    for e in examples:
        groups.setdefault(hard_label(e["soft"], classes), []).append(e)
    return {label: es for label, es in groups.items()
            if len(es) > 1 and len({tuple(e["soft"]) for e in es}) > 1}


# ----------------------------------------------------------------- printing

def targets_view(data):
    classes = data["classes"]
    print("TARGETS — soft distribution vs the hard label it collapses to")
    print("-" * 70)
    print("  id    soft distribution %-18s hard    runner-up  dark   entropy" % ("(" + ",".join(classes) + ")"))
    for e in data["examples"]:
        d = e["soft"]
        print("  %-5s %-30s %-7s %-10s %-6s %s"
              % (e["id"], str(d), hard_label(d, classes), runner_up(d, classes),
                 dark_knowledge(d), entropy(d)))
    print("-" * 70)
    print("  the hard label keeps only the argmax; everything else is the teacher's dark knowledge.")


def loss_view(data):
    classes = data["classes"]
    groups = collapsed_groups(data["examples"], classes)
    print("LOSS — what hard labels throw away")
    print("-" * 70)
    for label, es in groups.items():
        ids = [e["id"] for e in es]
        print("  hard label %-6s collapses %s into ONE identical target" % (label, ids))
        for e in es:
            print("     %-5s soft %s  (dark knowledge %.2f, runner-up %s)"
                  % (e["id"], e["soft"], dark_knowledge(e["soft"]), runner_up(e["soft"], classes)))
    print("-" * 70)
    print("  same hard label, different soft targets -- distinctions the student never sees from hard labels.")


def check(data):
    print("SELF-TEST — hard labels collapse same-argmax examples and drop the dark knowledge soft targets keep")
    print("-" * 74)
    classes = data["classes"]
    examples = data["examples"]

    groups = collapsed_groups(examples, classes)
    collapses = len(groups) > 0 and any(len(es) >= 2 for es in groups.values())
    total_collapsed = sum(len(es) for es in groups.values())
    print("  hard labels collapse distinct examples sharing an argmax = %s (%d examples into %d labels)"
          % (collapses, total_collapsed, len(groups)))

    has_dark = all(dark_knowledge(e["soft"]) > 0 for e in examples)
    print("  every soft target carries dark knowledge (non-top mass > 0) = %s" % has_dark)

    # the runner-up (confusable class) is recoverable from soft, but a hard label gives only the argmax
    soft_recovers_runnerup = all(runner_up(e["soft"], classes) != hard_label(e["soft"], classes) for e in examples)
    print("  the confusable runner-up class is recoverable from soft, not hard = %s" % soft_recovers_runnerup)

    # soft targets preserve uncertainty (entropy), hard labels report 0 uncertainty always
    soft_has_entropy = all(entropy(e["soft"]) > 0 for e in examples)
    print("  soft targets preserve uncertainty (entropy > 0) where hard labels report 0 = %s" % soft_has_entropy)

    ok = collapses and has_dark and soft_recovers_runnerup and soft_has_entropy
    print("-" * 74)
    print("SELF-TEST %s  collapses=%s  has_dark=%s  soft_recovers_runnerup=%s  soft_has_entropy=%s"
          % ("PASS" if ok else "FAIL", collapses, has_dark, soft_recovers_runnerup, soft_has_entropy))
    return ok


def main():
    p = argparse.ArgumentParser(description="Distill from soft targets, not hard labels.")
    p.add_argument("--targets", action="store_true")
    p.add_argument("--loss", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("examples=%d  classes=%s  file=%s  (the teacher's soft distributions are a fixture)"
          % (len(data["examples"]), data["classes"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.targets:
        targets_view(data)
    elif args.loss:
        loss_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
