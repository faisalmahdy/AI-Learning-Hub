"""Majority-vote (self-consistency) accuracy over k samples is a different number from single-sample accuracy, usually higher, so reporting one while deploying the other misstates the system -- and voting rescues a question only when the correct answer is the plurality, never one the model is systematically wrong about.

For a task with a verifiable answer, sampling the model once returns an answer that is right with some probability. Sampling it k times and keeping the answer that appears most often is self-consistency, and it changes the score. When the model's probability concentrates on the correct answer while its mistakes scatter across many different wrong answers, the correct answer is the plurality even on questions where a single draw is more often wrong than right -- so majority vote lands above single-sample accuracy.

The two numbers measure different systems. Single-sample accuracy is what one call gives you; majority-vote accuracy is what k calls plus a vote give you. They are both legitimate, but they are not interchangeable: reporting the majority-vote number for a product that makes one call per request overstates it, and reporting single-sample accuracy for a pipeline that votes understates it. The gap between them is real capability that the wrong number hides or invents.

Voting has a hard limit, and it is worth stating because it bounds the technique. Majority vote can only surface an answer the samples actually contain as their plurality. When the model is systematically wrong -- most of its samples give the same incorrect answer -- the plurality is that wrong answer, and voting confidently returns it. Self-consistency amplifies a model that is right on average; it cannot repair one that is wrong on average about a question.

On this fixture four questions each have five sampled answers and gold answer A. The mean single-sample accuracy is 0.45 and the majority-vote accuracy is 0.75. One question is rescued by voting although only 40% of its individual samples are correct, and one has a wrong majority (three of five samples agree on B) that voting cannot fix. This computes both.

  --single     the per-question single-sample accuracy and its mean across questions
  --majority   the majority answer per question and the majority-vote accuracy
  --check      majority-vote accuracy exceeds single-sample accuracy, voting rescues a question whose single-sample accuracy is below half, and it cannot fix a question with a wrong majority

the gold answers and sampled answers are the fixture; the single-sample accuracies, the majority answers, and both aggregate accuracies are computed. Stdlib only.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "selfconsist.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def single_accuracy(q):
    """The chance one random sample is correct: the fraction of this question's samples that match the gold."""
    return sum(1 for s in q["samples"] if s == q["gold"]) / len(q["samples"])


def majority_answer(q):
    """The answer that appears most often among the samples -- what self-consistency returns."""
    return Counter(q["samples"]).most_common(1)[0][0]


def majority_correct(q):
    """Whether the majority answer is the gold answer."""
    return majority_answer(q) == q["gold"]


def mean_single(questions):
    """Mean single-sample accuracy across questions: the expected accuracy of one call per question."""
    return sum(single_accuracy(q) for q in questions) / len(questions)


def majority_accuracy(questions):
    """Majority-vote accuracy across questions: the fraction whose plurality answer is correct."""
    return sum(1 for q in questions if majority_correct(q)) / len(questions)


# ----------------------------------------------------------------- printing

def single_view(d):
    qs = d["questions"]
    print("SINGLE — one sample per question (gold in parentheses)")
    print("-" * 64)
    for i, q in enumerate(qs, start=1):
        print("  q%d (%s): %s  single-sample acc %.1f" % (i, q["gold"], q["samples"], single_accuracy(q)))
    print("  mean single-sample accuracy = %.2f" % mean_single(qs))
    print("-" * 64)
    print("  this is what one call per question scores on average")


def majority_view(d):
    qs = d["questions"]
    print("MAJORITY — take the most common of the 5 samples per question")
    print("-" * 64)
    for i, q in enumerate(qs, start=1):
        mark = "" if majority_correct(q) else "   <- wrong majority (systematic error)"
        print("  q%d (%s): majority %s  correct? %s%s" % (i, q["gold"], majority_answer(q), majority_correct(q), mark))
    print("  majority-vote accuracy = %.2f" % majority_accuracy(qs))
    print("-" * 64)
    print("  voting lifts the score where the correct answer is the plurality")


def check(d):
    print("SELF-TEST — majority-vote accuracy exceeds single-sample accuracy, voting rescues a below-half question, and it cannot fix a wrong-majority question")
    print("-" * 112)
    qs = d["questions"]

    ms, mv = mean_single(qs), majority_accuracy(qs)
    majority_beats_single = mv > ms
    print("  majority-vote accuracy beats single-sample = %s (%.2f > %.2f, gap %.2f)" % (majority_beats_single, mv, ms, mv - ms))

    rescued = [i + 1 for i, q in enumerate(qs) if majority_correct(q) and single_accuracy(q) < 0.5]
    majority_rescues = len(rescued) > 0
    print("  voting rescues a question whose single-sample accuracy is below half = %s (questions %s)" % (majority_rescues, rescued))

    systematic = [i + 1 for i, q in enumerate(qs) if not majority_correct(q)]
    cannot_fix_systematic = len(systematic) > 0
    print("  a wrong-majority question exists that voting cannot fix = %s (questions %s)" % (cannot_fix_systematic, systematic))

    gap_is_real = abs((mv - ms) - 0.30) < 1e-9
    print("  the report-vs-deploy gap is 0.30 = %s" % gap_is_real)

    ok = (majority_beats_single and majority_rescues and cannot_fix_systematic and gap_is_real)
    print("-" * 112)
    print("SELF-TEST %s  majority_beats_single=%s  majority_rescues=%s  cannot_fix_systematic=%s  gap_is_real=%s"
          % ("PASS" if ok else "FAIL", majority_beats_single, majority_rescues, cannot_fix_systematic, gap_is_real))
    return ok


def main():
    p = argparse.ArgumentParser(description="Self-consistency: majority-vote accuracy over k samples is a distinct, usually higher number than single-sample accuracy, so reporting one while deploying the other misstates the system; voting lifts the score where the correct answer is the plurality (even when a single sample is more often wrong than right) but cannot fix a question the model is systematically wrong about, where the plurality itself is a wrong answer.")
    p.add_argument("--single", action="store_true")
    p.add_argument("--majority", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("questions=%d  samples_each=%d  file=%s" % (len(d["questions"]), len(d["questions"][0]["samples"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.single:
        single_view(d)
    elif args.majority:
        majority_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
