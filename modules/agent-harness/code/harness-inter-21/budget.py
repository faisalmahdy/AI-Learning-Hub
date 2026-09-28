"""Cap the run's token budget, not just its step count, or a few fat steps overrun the bill under the step limit.

An agent loop's iteration bound stops it after so many steps -- the standard guard against a loop that will not
converge. But it counts STEPS, and steps are not equal. Most append a small tool result and cost little; a few
append a huge one -- a whole file, a giant search dump, a verbose API response -- and cost a great deal, both in
context tokens and in dollars. So a run can stay comfortably under its step limit while its token usage, and its
bill, run away: five steps, two of them fat, can blow a budget the twenty-step limit was nowhere near catching.
The iteration bound is measuring the wrong quantity. It bounds how many times the loop turns, not how much the
loop costs, and cost is what you actually care about.

The fix is a second, independent guard: a cumulative token (or cost) budget. Track the tokens the run has
consumed and stop when they reach the budget, whatever the step count. Now a run that appends fat results trips
the token budget early and halts, while a run of many small steps trips the iteration bound -- each guard catches
the failure the other is blind to. The two are not redundant; they measure different things, and a robust loop
enforces both, plus the per-call timeout that bounds a single hung call. Three guards, three quantities: how many
steps, how long one call, how much in total.

On this fixture the step limit is 20 and the token budget is 15000. The steps cost 500, 500, 8000, 500, 9000,
... so after just 5 steps the cumulative is 18500 -- past the budget -- while the step count is nowhere near 20.
The token budget stops the run at step 5; the iteration bound would have let it run to 20 and cost far more. This
computes both.

  --run        cumulative tokens after each step, and where the token budget and the step bound each stop
  --guards     which guard trips first, at what step and token count, and what the step bound alone would allow
  --check      the step bound misses the overrun; the token budget stops it early; the fat steps dominate

The step costs and limits are the fixture; every total is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "budget.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cumulative(step_tokens):
    """Running total of tokens after each step."""
    total, out = 0, []
    for t in step_tokens:
        total += t
        out.append(total)
    return out


def stop_by_budget(step_tokens, max_tokens):
    """The 1-indexed step at which cumulative tokens first reach the budget, or None if never."""
    for i, c in enumerate(cumulative(step_tokens), start=1):
        if c >= max_tokens:
            return i
    return None


def stop_by_iterations(step_tokens, max_steps):
    """The step at which the iteration bound stops the run (it never sees token cost)."""
    return min(len(step_tokens), max_steps)


# ----------------------------------------------------------------- printing

def run_view(data):
    st, mt, ms = data["step_tokens"], data["max_tokens"], data["max_steps"]
    cum = cumulative(st)
    budget_step = stop_by_budget(st, mt)
    print("RUN — cumulative tokens per step (budget %d, step limit %d)" % (mt, ms))
    print("-" * 58)
    print("  step   step tokens   cumulative   note")
    for i, (t, c) in enumerate(zip(st, cum), start=1):
        note = "  <- token budget hit" if i == budget_step else ""
        print("  %-5d  %6d        %6d%s" % (i, t, c, note))
    print("-" * 58)
    print("  the budget is crossed at step %d, long before the %d-step iteration bound." % (budget_step, ms))


def guards_view(data):
    st, mt, ms = data["step_tokens"], data["max_tokens"], data["max_steps"]
    budget_step = stop_by_budget(st, mt)
    iter_step = stop_by_iterations(st, ms)
    tokens_if_iter_only = sum(st[:iter_step])
    print("GUARDS — which guard stops the run first")
    print("-" * 58)
    print("  token budget stops at step %d  (cumulative %d >= %d)" % (budget_step, cumulative(st)[budget_step - 1], mt))
    print("  iteration bound stops at step %d (of %d available steps)" % (iter_step, len(st)))
    print("  step bound alone would let %d tokens through (%.1fx the budget)" % (tokens_if_iter_only, tokens_if_iter_only / mt))
    print("-" * 58)
    print("  the token budget fires %d steps earlier and caps the cost the step bound ignores." % (iter_step - budget_step))


def check(data):
    print("SELF-TEST — the step bound misses the overrun; the token budget stops it early; the fat steps dominate")
    print("-" * 104)
    st, mt, ms = data["step_tokens"], data["max_tokens"], data["max_steps"]
    budget_step = stop_by_budget(st, mt)
    iter_step = stop_by_iterations(st, ms)

    budget_trips = budget_step is not None
    print("  the token budget is crossed during the run = %s (at step %d)" % (budget_trips, budget_step))

    budget_before_step_bound = budget_step < iter_step
    print("  the token budget stops the run before the iteration bound = %s (%d < %d)" % (budget_before_step_bound, budget_step, iter_step))

    step_bound_would_overrun = sum(st[:iter_step]) > mt
    print("  the step bound alone would blow the token budget = %s (%d > %d)" % (step_bound_would_overrun, sum(st[:iter_step]), mt))

    fat_steps = [t for t in st if t >= mt / 3]
    fat_steps_dominate = sum(fat_steps) > sum(t for t in st if t < mt / 3)
    print("  a few fat steps dominate the cost = %s (%d in %d fat steps vs %d in the rest)" % (fat_steps_dominate, sum(fat_steps), len(fat_steps), sum(t for t in st if t < mt / 3)))

    step_count_under_limit = budget_step < ms
    print("  at the stop, the step count was well under its limit = %s (%d < %d)" % (step_count_under_limit, budget_step, ms))

    ok = budget_trips and budget_before_step_bound and step_bound_would_overrun and fat_steps_dominate and step_count_under_limit
    print("-" * 104)
    print("SELF-TEST %s  budget_trips=%s  budget_before_step_bound=%s  step_bound_would_overrun=%s  fat_steps_dominate=%s  step_count_under_limit=%s"
          % ("PASS" if ok else "FAIL", budget_trips, budget_before_step_bound, step_bound_would_overrun, fat_steps_dominate, step_count_under_limit))
    return ok


def main():
    p = argparse.ArgumentParser(description="A cumulative token/cost budget stops a run that fat tool results overrun, which the step-count iteration bound cannot see.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--guards", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("steps=%d  max_steps=%d  max_tokens=%d  total_if_unbounded=%d  file=%s  (the costs are a fixture)"
          % (len(data["step_tokens"]), data["max_steps"], data["max_tokens"], sum(data["step_tokens"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.guards:
        guards_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
