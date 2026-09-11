"""Teacher forcing hides a model's real error rate -- feeding its own predictions at inference lets one mistake cascade.

An autoregressive model predicts the next token from the tokens before it, and it is trained by TEACHER FORCING: at every
position the model is shown the GROUND-TRUTH previous tokens and asked only to predict the next one, and its loss is scored
against the true next token. Teacher forcing is efficient and stable -- every position gets a correct context, all
positions can be trained in parallel, and the gradient at each step is clean. But it trains the model in a world it never
inhabits at inference. At generation time there is no ground truth to feed: the model must consume its OWN previous
predictions, so if it emits a wrong token, that wrong token becomes the context for the next step, and the next, and the
next.

This mismatch is called EXPOSURE BIAS. During training the model is only ever exposed to correct prefixes, so it never
learns what to do after a mistake -- how to recover when the context contains one of its own errors. At inference a single
early error puts the model into a state it was never trained on (a prefix that ends in a wrong token), and from there it
can compound: the error shifts everything downstream, and the model, having only seen clean contexts, has no idea it has
gone off the rails. The measured training error rate -- errors per position under teacher forcing -- therefore systematically
UNDERSTATES the generation error rate, because teacher forcing resets the context to the truth after every step and so
never lets an error propagate. A model can look nearly perfect on teacher-forced validation and generate badly.

The mechanism is stark in a toy. Suppose a model has learned the rule 'next = current + 1' perfectly except at one token,
where it predicts 5 instead of 4. Under teacher forcing, that is exactly one wrong prediction out of many, because the very
next step is fed the true 4 and continues correctly -- the error is local. Under free-running generation, the moment the
model emits 5 (instead of 4), it then predicts from 5, gets 6, then 7, then 8 -- every remaining token is wrong, not
because the model made new mistakes but because the single early mistake shifted the whole trajectory. Same model, same
weights: one error under teacher forcing, a cascade under generation.

The rule: teacher-forced (training) error rate understates generation error, because teacher forcing always feeds the true
previous token while inference feeds the model's own prediction, so a single early mistake -- which teacher forcing keeps
local by resetting the context to the truth -- cascades under free-running generation; evaluate a sequence model by
generating, not only by teacher-forced loss, and train it to recover from its own errors (scheduled sampling, sequence-level
objectives).

On this fixture the true sequence is 0..7 (rule next=current+1) and the model errs only at token 3 (predicts 5, not 4).
Teacher forcing makes exactly 1 error out of 7 predictions; free-running generation from the same model produces
0,1,2,3,5,6,7,8 -- wrong at 4 of the 7 positions after the start, all from that one mistake. This computes both.

  --teacher   each teacher-forced prediction (fed the true previous token) vs the true next token, and the error count
  --generate  the free-running sequence (fed its own predictions) vs the truth, and how the one error at token 3 cascades
  --check     teacher forcing makes one local error; free-running generation cascades it into many -- exposure bias

true_sequence and model_transition are the fixture; every prediction, error, and cascade is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "exposure.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def predict(model, token):
    """The model's learned next-token prediction given the current token."""
    return model[str(token)]


def teacher_forced(true_seq, model):
    """Feed the TRUE previous token at every step; compare each prediction to the true next token."""
    preds = []
    for i in range(len(true_seq) - 1):
        p = predict(model, true_seq[i])          # context is always the ground truth
        preds.append((true_seq[i], p, true_seq[i + 1], p == true_seq[i + 1]))
    return preds


def free_run(true_seq, model):
    """Feed the model's OWN previous prediction at every step, starting from the true first token."""
    out = [true_seq[0]]
    for _ in range(len(true_seq) - 1):
        out.append(predict(model, out[-1]))      # context is the model's own last output
    return out


# ----------------------------------------------------------------- printing

def teacher_view(data):
    true_seq, model = data["true_sequence"], data["model_transition"]
    preds = teacher_forced(true_seq, model)
    print("TEACHER FORCING — fed the true previous token at every step")
    print("-" * 62)
    print("  step  context(true)  predicts  true next  ok?")
    for i, (ctx, p, truth, ok) in enumerate(preds):
        print("  %-4d  %-13d  %-8d  %-9d  %s" % (i, ctx, p, truth, "ok" if ok else "WRONG"))
    errors = sum(1 for _, _, _, ok in preds if not ok)
    print("-" * 62)
    print("  errors: %d of %d predictions -- the mistake at token 3 stays local." % (errors, len(preds)))


def generate_view(data):
    true_seq, model = data["true_sequence"], data["model_transition"]
    gen = free_run(true_seq, model)
    print("GENERATE — fed the model's own previous prediction at every step")
    print("-" * 60)
    print("  position  generated  true   ok?")
    for i in range(len(true_seq)):
        ok = gen[i] == true_seq[i]
        print("  %-8d  %-9d  %-5d  %s" % (i, gen[i], true_seq[i], "ok" if ok else "WRONG"))
    errors = sum(1 for i in range(len(true_seq)) if gen[i] != true_seq[i])
    print("-" * 60)
    print("  generated %s vs true %s" % (gen, true_seq))
    print("  errors: %d of %d positions -- one mistake at token 3 shifted every token after it." % (errors, len(true_seq)))


def check(data):
    print("SELF-TEST — teacher forcing makes one local error; free-running generation cascades it into many (exposure bias)")
    print("-" * 112)
    true_seq, model = data["true_sequence"], data["model_transition"]
    preds = teacher_forced(true_seq, model)
    gen = free_run(true_seq, model)

    tf_errors = sum(1 for _, _, _, ok in preds if not ok)
    teacher_one_error = tf_errors == 1
    print("  teacher-forced errors = %d -> exactly one = %s" % (tf_errors, teacher_one_error))

    gen_errors = sum(1 for i in range(len(true_seq)) if gen[i] != true_seq[i])
    generation_cascades = gen_errors > tf_errors
    print("  free-running generation errors = %d -> more than teacher forcing = %s" % (gen_errors, generation_cascades))

    first_div = next(i for i in range(len(true_seq)) if gen[i] != true_seq[i])
    cascade_from_one_root = all(gen[i] != true_seq[i] for i in range(first_div, len(true_seq)))
    print("  every position from the first divergence (pos %d) onward is wrong = %s" % (first_div, cascade_from_one_root))

    single_learned_error = sum(1 for k, v in model.items() if v != int(k) + 1) == 1
    print("  the model has exactly one learned error (at token 3) = %s" % single_learned_error)

    tf_rate = tf_errors / len(preds)
    gen_rate = gen_errors / len(true_seq)
    training_understates = tf_rate < gen_rate
    print("  teacher-forced error RATE understates generation error rate = %s (%.3f vs %.3f)" % (training_understates, tf_rate, gen_rate))

    ok = teacher_one_error and generation_cascades and cascade_from_one_root and single_learned_error and training_understates
    print("-" * 112)
    print("SELF-TEST %s  teacher_one_error=%s  generation_cascades=%s  cascade_from_one_root=%s  single_learned_error=%s  training_understates=%s"
          % ("PASS" if ok else "FAIL", teacher_one_error, generation_cascades, cascade_from_one_root, single_learned_error, training_understates))
    return ok


def main():
    p = argparse.ArgumentParser(description="Teacher forcing and exposure bias: the teacher-forced (training) error rate understates generation error, because teacher forcing always feeds the true previous token while inference feeds the model's own prediction, so a single early mistake -- kept local by teacher forcing resetting the context to the truth -- cascades under free-running generation; evaluate a sequence model by generating, not only by teacher-forced loss.")
    p.add_argument("--teacher", action="store_true")
    p.add_argument("--generate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("true_sequence=%s  model_transition=%s  file=%s  (the true sequence and learned map are a fixture)"
          % (data["true_sequence"], data["model_transition"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.teacher:
        teacher_view(data)
    elif args.generate:
        generate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
