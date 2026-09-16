"""Sample logs by outcome, not uniformly at the head -- or you throw away almost all of the errors you keep logs for.

At high volume you cannot store every log line or every trace, so you keep a sample -- say five percent. The obvious
way is uniform head sampling: for each request, before you know how it turns out, flip a weighted coin and keep it with
probability r. That keeps a representative five percent of the traffic, which is fine for measuring throughput or
latency distributions. But it is a disaster for debugging, because the whole reason you keep logs is the rare bad
request, and uniform sampling keeps only five percent of THOSE too. Errors are a small fraction of traffic; sample them
at the same rate as successes and you discard ninety-five percent of the exact lines an on-call engineer will come
looking for. The sample is representative and nearly useless.

Priority sampling -- deciding after the outcome is known -- fixes this. Keep every error unconditionally, and keep only
the sampling rate of the successes. Now you capture one hundred percent of the failures, the lines that matter, while
still shrinking the flood of routine successes to the budget. Because errors are rare, keeping all of them barely moves
the total volume: the stored sample is a little larger than the uniform one but overwhelmingly more useful. This is the
idea behind tail-based trace sampling, which buffers a trace until it completes and then keeps it if it errored or was
slow -- the sampling decision belongs after the outcome, not before it.

On this fixture 10000 requests error at two percent (200 errors) and the budget keeps five percent. Uniform sampling
stores 500 lines but only 10 of the 200 errors -- it captures five percent of the errors and loses 190 of them.
Priority sampling stores 690 lines -- all 200 errors plus 490 sampled successes -- capturing one hundred percent of the
errors for thirty-eight percent more volume. This computes both.

  --sample   lines kept and errors captured under uniform sampling vs priority (keep-all-errors) sampling
  --budget   the total volume each keeps and the error-capture rate -- priority's small volume cost, huge capture gain
  --check    uniform captures only the sample rate of errors; priority captures all errors for a small volume overhead

The request volume, error rate, and sample rate are the fixture; every count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "logsample.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def counts(total, error_rate):
    """Split the traffic into errors and successes."""
    errors = round(total * error_rate)
    return errors, total - errors


def uniform_sample(errors, successes, rate):
    """Head sampling: keep `rate` of every line, deciding before the outcome is known."""
    return {"errors_kept": round(errors * rate), "success_kept": round(successes * rate)}


def priority_sample(errors, successes, rate):
    """Outcome sampling: keep every error, and `rate` of the successes."""
    return {"errors_kept": errors, "success_kept": round(successes * rate)}


def total_kept(sample):
    """Total lines stored under a sampling scheme."""
    return sample["errors_kept"] + sample["success_kept"]


def error_capture(sample, errors):
    """Fraction of the errors that survived into the stored sample."""
    return sample["errors_kept"] / errors if errors else 0.0


# ----------------------------------------------------------------- printing

def sample_view(data):
    total, er, sr = data["total_requests"], data["error_rate"], data["sample_rate"]
    errors, successes = counts(total, er)
    u = uniform_sample(errors, successes, sr)
    pr = priority_sample(errors, successes, sr)
    print("SAMPLE — %d requests, %d errors (%.0f%%), keeping %.0f%%" % (total, errors, er * 100, sr * 100))
    print("-" * 62)
    print("  scheme     errors kept       successes kept   total kept")
    print("  uniform    %-4d of %-4d      %-6d           %d" % (u["errors_kept"], errors, u["success_kept"], total_kept(u)))
    print("  priority   %-4d of %-4d      %-6d           %d" % (pr["errors_kept"], errors, pr["success_kept"], total_kept(pr)))
    print("-" * 62)
    print("  uniform keeps a representative 5% of everything -- including only 5% of the errors.")


def budget_view(data):
    total, er, sr = data["total_requests"], data["error_rate"], data["sample_rate"]
    errors, successes = counts(total, er)
    u = uniform_sample(errors, successes, sr)
    pr = priority_sample(errors, successes, sr)
    print("BUDGET — volume cost vs error-capture gain")
    print("-" * 60)
    print("  uniform:   %d lines, error capture %.0f%%" % (total_kept(u), error_capture(u, errors) * 100))
    print("  priority:  %d lines, error capture %.0f%%" % (total_kept(pr), error_capture(pr, errors) * 100))
    print("  extra volume for priority: +%d lines (+%.0f%%)"
          % (total_kept(pr) - total_kept(u), 100 * (total_kept(pr) - total_kept(u)) / total_kept(u)))
    print("-" * 60)
    print("  a %.0f%% volume increase buys going from %.0f%% to 100%% of the errors captured."
          % (100 * (total_kept(pr) - total_kept(u)) / total_kept(u), error_capture(u, errors) * 100))


def check(data):
    print("SELF-TEST — uniform captures only the sample rate of errors; priority captures all errors for a small overhead")
    print("-" * 110)
    total, er, sr = data["total_requests"], data["error_rate"], data["sample_rate"]
    errors, successes = counts(total, er)
    u = uniform_sample(errors, successes, sr)
    pr = priority_sample(errors, successes, sr)

    uniform_captures_rate = abs(error_capture(u, errors) - sr) < 0.01
    print("  uniform captures about the sample rate of errors = %s (%.0f%%)" % (uniform_captures_rate, error_capture(u, errors) * 100))

    uniform_loses_most = error_capture(u, errors) < 0.5
    print("  uniform loses most of the errors = %s (%d of %d kept)" % (uniform_loses_most, u["errors_kept"], errors))

    priority_captures_all = error_capture(pr, errors) == 1.0
    print("  priority captures every error = %s (%d of %d)" % (priority_captures_all, pr["errors_kept"], errors))

    small_overhead = total_kept(pr) <= 2 * total_kept(u)
    print("  priority's total volume is within a small factor of uniform's = %s (%d vs %d)" % (small_overhead, total_kept(pr), total_kept(u)))

    priority_beats_uniform = error_capture(pr, errors) > error_capture(u, errors)
    print("  priority captures far more errors than uniform = %s (100%% vs %.0f%%)" % (priority_beats_uniform, error_capture(u, errors) * 100))

    ok = uniform_captures_rate and uniform_loses_most and priority_captures_all and small_overhead and priority_beats_uniform
    print("-" * 110)
    print("SELF-TEST %s  uniform_captures_rate=%s  uniform_loses_most=%s  priority_captures_all=%s  small_overhead=%s  priority_beats_uniform=%s"
          % ("PASS" if ok else "FAIL", uniform_captures_rate, uniform_loses_most, priority_captures_all, small_overhead, priority_beats_uniform))
    return ok


def main():
    p = argparse.ArgumentParser(description="Priority (outcome/tail) log and trace sampling: keep every error and only a fraction of the successes, so you capture the rare failures a uniform head sample would mostly discard.")
    p.add_argument("--sample", action="store_true")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("total_requests=%d  error_rate=%.2f  sample_rate=%.2f  file=%s  (the volumes are a fixture)"
          % (data["total_requests"], data["error_rate"], data["sample_rate"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.sample:
        sample_view(data)
    elif args.budget:
        budget_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
