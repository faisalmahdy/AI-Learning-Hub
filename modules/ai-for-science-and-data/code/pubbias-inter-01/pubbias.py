"""Average all the studies, not just the published ones -- publication bias manufactures an effect from pure noise.

A meta-analysis pools the studies on a question to estimate the true effect, and it can only pool the studies it can SEE.
That is the trap, because which studies become visible is not random: journals, reviewers, and authors all prefer a
positive, statistically significant result to a null one. A study that finds 'no effect' is harder to publish, less likely
to be written up at all, and sits in the researcher's file drawer -- the FILE-DRAWER PROBLEM. On top of that, among the
significant results, the ones pointing in the hoped-for (positive) direction get published and cited far more than the
significant results pointing the other way -- POSITIVE-OUTCOME BIAS. The consequence is that the published literature is a
BIASED SAMPLE of all the studies actually run, skewed toward large, positive, significant effects, and a meta-analysis of
that literature estimates the effect from the skewed sample and gets it wrong.

The failure is at its starkest when the true effect is ZERO. If a treatment does nothing, studies of it still produce
noisy estimates scattered around zero -- some positive, some negative, most small, a few large by chance. Publish only the
significant, positive ones and the visible literature is entirely made of the upper tail: a run of studies all showing a
sizeable positive effect, none showing the negatives or the nulls that would cancel them. A meta-analyst pooling those
published studies computes a confident positive effect, complete with a tight confidence interval, for a treatment that
does nothing at all. The effect is not in the treatment; it is an artifact of the selection filter on the way to
publication. The signal was manufactured by hiding the studies that disagreed.

This is why the honest estimate requires the studies that were NOT published -- the null and negative results -- and why
techniques to detect and correct publication bias (funnel plots and their asymmetry, trim-and-fill, registered reports and
pre-registration that guarantee a study is reported regardless of outcome) exist: the file drawer is where the truth is
hiding, and a mean over only the visible studies is a mean over the tail.

The rule: estimate an effect from ALL the studies run, not only the published ones, because publication favors significant
and positive results, so the visible literature is a biased upper-tail sample -- and pooling only it manufactures a
confident effect even when the true effect is zero and the full set of studies averages to nothing.

On this fixture eight studies of a treatment with no real effect report effects that average to exactly 0. Only the
significant, positive studies (effects 2 and 4) get published; their mean is 3. A meta-analysis of the published
literature reports an effect of 3 for a treatment whose true effect is 0. This computes both.

  --studies   each study's effect, whether it is significant, and whether it gets published under the bias
  --bias      the mean over all studies (0, the truth) vs the mean over the published studies (3, the phantom), and the file-drawer count
  --check     all studies average to zero; the published subset averages to a positive phantom effect -- publication bias

effects and threshold are the fixture; every significance flag, publication decision, and mean is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pubbias.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def is_significant(effect, threshold):
    return abs(effect) >= threshold


def is_published(effect, threshold):
    """Published if significant AND positive (file-drawer + positive-outcome bias)."""
    return is_significant(effect, threshold) and effect > 0


def mean(xs):
    return sum(xs) / len(xs)


def published(effects, threshold):
    return [e for e in effects if is_published(e, threshold)]


# ----------------------------------------------------------------- printing

def studies_view(data):
    effects, thr = data["effects"], data["threshold"]
    print("STUDIES — effect, significance (|effect| >= %d), and publication under the bias" % thr)
    print("-" * 60)
    print("  effect   significant?   published?")
    for e in effects:
        sig = "yes" if is_significant(e, thr) else "no"
        pub = "PUBLISHED" if is_published(e, thr) else "file drawer"
        print("  %-8d %-14s %s" % (e, sig, pub))
    print("-" * 60)
    print("  published: %s   (the rest are hidden)" % published(effects, thr))


def bias_view(data):
    effects, thr = data["effects"], data["threshold"]
    pub = published(effects, thr)
    print("BIAS — the mean over all studies vs the mean over only the published ones")
    print("-" * 62)
    print("  all %d studies:        %s   mean = %.1f   <- the truth (no effect)" % (len(effects), effects, mean(effects)))
    print("  published %d studies:   %s              mean = %.1f   <- the phantom" % (len(pub), pub, mean(pub)))
    print("-" * 62)
    print("  %d of %d studies are in the file drawer; the meta-analysis sees only the upper tail."
          % (len(effects) - len(pub), len(effects)))


def check(data):
    print("SELF-TEST — all studies average to zero; the published subset averages to a positive phantom effect")
    print("-" * 100)
    effects, thr = data["effects"], data["threshold"]
    pub = published(effects, thr)

    true_effect_zero = mean(effects) == 0
    print("  all studies average to zero (the true effect) = %s (mean %.1f)" % (true_effect_zero, mean(effects)))

    published_shows_effect = mean(pub) > 0
    print("  the published studies show a positive effect = %s (mean %.1f)" % (published_shows_effect, mean(pub)))

    publication_inflates = mean(pub) > mean(effects)
    print("  publication bias inflates the estimate = %s (%.1f vs %.1f)" % (publication_inflates, mean(pub), mean(effects)))

    most_in_drawer = (len(effects) - len(pub)) > len(pub)
    print("  most studies are hidden in the file drawer = %s (%d hidden, %d published)"
          % (most_in_drawer, len(effects) - len(pub), len(pub)))

    nulls_all_hidden = all(not is_published(e, thr) for e in effects if not is_significant(e, thr))
    print("  every non-significant study is unpublished = %s" % nulls_all_hidden)

    ok = true_effect_zero and published_shows_effect and publication_inflates and most_in_drawer and nulls_all_hidden
    print("-" * 100)
    print("SELF-TEST %s  true_effect_zero=%s  published_shows_effect=%s  publication_inflates=%s  most_in_drawer=%s  nulls_all_hidden=%s"
          % ("PASS" if ok else "FAIL", true_effect_zero, published_shows_effect, publication_inflates, most_in_drawer, nulls_all_hidden))
    return ok


def main():
    p = argparse.ArgumentParser(description="Publication bias: estimate an effect from all the studies run, not only the published ones, because publication favors significant and positive results, so the visible literature is a biased upper-tail sample -- and pooling only it manufactures a confident effect even when the true effect is zero and the full set of studies averages to nothing.")
    p.add_argument("--studies", action="store_true")
    p.add_argument("--bias", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("effects=%s  threshold=%d  file=%s  (the study effects and threshold are a fixture)"
          % (data["effects"], data["threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.studies:
        studies_view(data)
    elif args.bias:
        bias_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
