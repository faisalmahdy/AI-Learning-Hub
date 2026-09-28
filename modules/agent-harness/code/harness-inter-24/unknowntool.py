"""Return an unknown tool name as an observation, not an exception -- or one hallucinated name aborts the whole loop.

A model does not always emit a tool name that exists. It misremembers -- reed_file for read_file, serch_web for
search_web -- and hands the harness a call to a tool that is not on the menu. This is not the same failure as a real
tool called with bad arguments (a schema problem); the tool itself does not exist, so there is nothing to validate and
nothing to run. The naive dispatcher treats the menu as a dictionary and looks the name up, which raises on a miss. That
exception, uncaught in the agent loop, aborts the entire turn: every tool call the model queued after the bad one is
discarded, along with all the work already done, over a single typo the model could have fixed itself in one more step.

The harness should hand the miss back the way it hands back any other tool result: as an OBSERVATION. Return an error
message that names the unknown tool, lists the tools that do exist, and -- because the model was usually one character
off -- suggests the nearest real name by edit distance. The loop stays alive: the model reads "no tool named serch_web;
did you mean search_web?", corrects itself, and continues. A wrong tool name becomes a recoverable turn instead of a
crash, exactly like returning a tool's error output instead of throwing it. Unknown names are input to handle, not
invariants to assume.

On this fixture the model emits five calls; three name real tools (search_web, run_python, list_dir) and two are
hallucinated (reed_file, serch_web). The naive dispatcher runs the first call, then crashes on reed_file and abandons
the remaining three calls. The observation dispatcher runs all three real calls and returns a recoverable error for
each unknown one, each with the correct did-you-mean (read_file, search_web). This computes both.

  --dispatch  each call under the naive dispatcher (crashes on the first miss) vs the observation dispatcher (survives)
  --suggest   each unknown tool name and the nearest real tool by edit distance -- the did-you-mean the model needs
  --check     the naive dispatcher aborts early; the observation one runs every real call and recovers every miss

The menu and the calls are the fixture; every match and edit distance is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "unknowntool.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def edit_distance(a, b):
    """Levenshtein distance between two names -- how many single-character edits separate them."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def nearest(name, menu):
    """The menu tool closest to `name` by edit distance -- the did-you-mean suggestion."""
    return min(menu, key=lambda t: (edit_distance(name, t), t))


def dispatch_observation(menu, calls):
    """Dispatch every call; a known name executes, an unknown one becomes a recoverable error observation."""
    log = []
    for name in calls:
        if name in menu:
            log.append((name, "executed", None))
        else:
            obs = "no tool named %r; available: %s; did you mean %r?" % (name, menu, nearest(name, menu))
            log.append((name, "error-observation", obs))
    return log


def dispatch_naive(menu, calls):
    """Dispatch by dict lookup: execute known names, but raise (aborting the loop) on the first unknown one."""
    tools = {t: t for t in menu}
    log = []
    for name in calls:
        log.append((name, "executed", None))
        _ = tools[name]  # KeyError on an unknown name -- uncaught, this aborts the whole turn
    return log


def run_naive(menu, calls):
    """Run the naive dispatcher, catching the abort the loop does not; return (executed_before_crash, crashed_on_or_None)."""
    try:
        dispatch_naive(menu, calls)
    except KeyError as e:
        bad = e.args[0]
        return calls[: calls.index(bad)], bad
    return list(calls), None


# ----------------------------------------------------------------- printing

def dispatch_view(data):
    menu, calls = data["menu"], data["calls"]
    print("DISPATCH — naive (crashes on the first miss) vs observation (survives every miss)")
    print("-" * 74)
    executed, crashed_on = run_naive(menu, calls)
    obs_log = dispatch_observation(menu, calls)
    print("  call            naive                observation")
    for (name, status, _), i in zip(obs_log, range(len(calls))):
        if crashed_on is not None and i > executed_index(calls, crashed_on):
            naive = "(never reached)"
        elif name == crashed_on and crashed_on is not None:
            naive = "CRASH — loop aborts"
        else:
            naive = "executed"
        print("  %-14s  %-19s  %s" % (name, naive, status))
    print("-" * 74)
    print("  naive ran %d of %d calls then aborted; the observation dispatcher ran all %d." % (len(executed), len(calls), len(calls)))


def executed_index(calls, crashed_on):
    """Index of the call the naive dispatcher crashed on (the first unknown)."""
    return calls.index(crashed_on)


def suggest_view(data):
    menu, calls = data["menu"], data["calls"]
    print("SUGGEST — the nearest real tool for each unknown name (did-you-mean)")
    print("-" * 60)
    for name in calls:
        if name not in menu:
            n = nearest(name, menu)
            print("  %-14s -> %-14s (edit distance %d)" % (name, n, edit_distance(name, n)))
    print("-" * 60)
    print("  each hallucinated name is one edit from a real tool, so the suggestion is reliable.")


def check(data):
    print("SELF-TEST — the naive dispatcher aborts early; the observation one runs every real call and recovers every miss")
    print("-" * 112)
    menu, calls = data["menu"], data["calls"]
    real = [c for c in calls if c in menu]
    unknown = [c for c in calls if c not in menu]

    executed, crashed_on = run_naive(menu, calls)
    naive_aborts_early = len(executed) < len(real)
    print("  the naive dispatcher aborts before running every real call = %s (ran %d of %d real, crashed on %r)"
          % (naive_aborts_early, len(executed), len(real), crashed_on))

    obs_log = dispatch_observation(menu, calls)
    ran = [name for name, status, _ in obs_log if status == "executed"]
    obs_runs_all_real = ran == real
    print("  the observation dispatcher runs every real call = %s (%d of %d)" % (obs_runs_all_real, len(ran), len(real)))

    errored = [name for name, status, _ in obs_log if status == "error-observation"]
    unknown_recoverable = errored == unknown
    print("  every unknown name comes back as a recoverable error, not a crash = %s (%s)" % (unknown_recoverable, errored))

    suggestion_is_nearest = all(edit_distance(u, nearest(u, menu)) == min(edit_distance(u, t) for t in menu) for u in unknown)
    print("  each suggestion is the true minimum-edit-distance tool = %s (%s)" % (suggestion_is_nearest, [nearest(u, menu) for u in unknown]))

    known_never_misrouted = all(nearest(t, menu) == t for t in menu)
    print("  a known name always resolves to itself (never misrouted) = %s" % known_never_misrouted)

    ok = naive_aborts_early and obs_runs_all_real and unknown_recoverable and suggestion_is_nearest and known_never_misrouted
    print("-" * 112)
    print("SELF-TEST %s  naive_aborts_early=%s  obs_runs_all_real=%s  unknown_recoverable=%s  suggestion_is_nearest=%s  known_never_misrouted=%s"
          % ("PASS" if ok else "FAIL", naive_aborts_early, obs_runs_all_real, unknown_recoverable, suggestion_is_nearest, known_never_misrouted))
    return ok


def main():
    p = argparse.ArgumentParser(description="Return an unknown tool name as an error observation (with a did-you-mean), not an exception, so one hallucinated name does not abort the agent loop.")
    p.add_argument("--dispatch", action="store_true")
    p.add_argument("--suggest", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("menu=%s  calls=%d  file=%s  (the menu and calls are a fixture)" % (data["menu"], len(data["calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.dispatch:
        dispatch_view(data)
    elif args.suggest:
        suggest_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
