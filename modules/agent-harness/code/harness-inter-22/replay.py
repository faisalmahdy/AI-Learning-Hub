"""Record each tool call's output, or you can never reproduce the run because the live tools have moved on.

An agent run that went wrong is a bug report you cannot reopen. To debug it you want to re-run the exact sequence
of tool calls and watch where it went off the rails -- but tools are not pure functions of their arguments. A
search returns different results tomorrow; a clock returns a different time; an API returns different data; a
random call returns a different number; a write leaves a side effect you do not want to repeat. So re-running the
agent live does not reproduce the original run: the tools have moved on, the inputs the agent saw no longer exist,
and the failure you were chasing quietly vanishes or mutates into a different one. You are debugging a run you can
no longer observe.

Recording fixes this. As the original run executes, capture every tool call and its output -- the exact bytes the
tool returned at that moment -- into a transcript. To reproduce the run, REPLAY it: feed each tool call's recorded
output back to the agent instead of invoking the live tool. Now the agent sees precisely the inputs it saw the
first time, follows the same path, and reaches the same failure, deterministically, offline, with no live calls
and no side effects. Pure tools would have reproduced anyway; the recording is what makes the NON-deterministic
ones -- clocks, searches, APIs, randomness -- reproducible too, and what lets you replay without re-triggering a
tool's side effects.

On this fixture the recording has get_time returning 5 (the clock then) and double(3) returning 6. Replayed, both
return their recorded values, matching the original run exactly. Re-run live at the current time of 9, get_time
returns 9 -- diverged from the recorded 5 -- while double still returns 6. The pure tool reproduces either way;
only replay reproduces the clock. This computes both.

  --run        each tool call's recorded output, its replayed output, and its live re-run output
  --diverge    which tools reproduce under a live re-run and which need the recording to reproduce
  --check      replay reproduces every recorded output; a live re-run diverges on the non-deterministic tool

The recording and clock are the fixture; every output is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "replay.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def live(tool, arg, world_time):
    """Invoke the tool against the CURRENT world. get_time is non-deterministic; double is pure."""
    if tool == "get_time":
        return world_time
    if tool == "double":
        return 2 * arg
    raise ValueError(tool)


def replay(step):
    """Replay: return the tool call's RECORDED output, without invoking the live tool."""
    return step["output"]


# ----------------------------------------------------------------- printing

def run_view(data):
    rec, now = data["recording"], data["current_time"]
    print("RUN — recorded output vs replayed vs live re-run (clock now %d)" % now)
    print("-" * 62)
    print("  tool       arg   recorded   replayed   live re-run")
    for step in rec:
        print("  %-9s  %d     %d          %d          %d" % (step["tool"], step["arg"], step["output"], replay(step), live(step["tool"], step["arg"], now)))
    print("-" * 62)
    print("  replay matches recorded exactly; the live re-run's clock has moved on.")


def diverge_view(data):
    rec, now = data["recording"], data["current_time"]
    print("DIVERGE — which tools reproduce live, and which need the recording")
    print("-" * 62)
    for step in rec:
        live_out = live(step["tool"], step["arg"], now)
        reproduces_live = live_out == step["output"]
        note = "pure -- reproduces live" if reproduces_live else "NON-deterministic -- needs the recording"
        print("  %-9s  recorded %d, live %d  ->  %s" % (step["tool"], step["output"], live_out, note))
    print("-" * 62)
    print("  the recording is what makes the non-deterministic tools reproducible.")


def check(data):
    print("SELF-TEST — replay reproduces every recorded output; a live re-run diverges on the non-deterministic tool")
    print("-" * 108)
    rec, now = data["recording"], data["current_time"]

    replay_reproduces_all = all(replay(step) == step["output"] for step in rec)
    print("  replay reproduces every recorded output = %s" % replay_reproduces_all)

    live_diverges = any(live(step["tool"], step["arg"], now) != step["output"] for step in rec)
    print("  a live re-run diverges on at least one tool = %s" % live_diverges)

    stateful = next(s for s in rec if s["tool"] == "get_time")
    stateful_diverges_live = live(stateful["tool"], stateful["arg"], now) != stateful["output"]
    print("  the non-deterministic tool diverges live = %s (recorded %d, live %d)" % (stateful_diverges_live, stateful["output"], live(stateful["tool"], stateful["arg"], now)))

    pure = next(s for s in rec if s["tool"] == "double")
    pure_same_live = live(pure["tool"], pure["arg"], now) == pure["output"]
    print("  the pure tool reproduces even live = %s (%d)" % (pure_same_live, pure["output"]))

    replay_reproduces_stateful = replay(stateful) == stateful["output"]
    print("  replay reproduces the non-deterministic tool where live cannot = %s (%d)" % (replay_reproduces_stateful, replay(stateful)))

    ok = replay_reproduces_all and live_diverges and stateful_diverges_live and pure_same_live and replay_reproduces_stateful
    print("-" * 108)
    print("SELF-TEST %s  replay_reproduces_all=%s  live_diverges=%s  stateful_diverges_live=%s  pure_same_live=%s  replay_reproduces_stateful=%s"
          % ("PASS" if ok else "FAIL", replay_reproduces_all, live_diverges, stateful_diverges_live, pure_same_live, replay_reproduces_stateful))
    return ok


def main():
    p = argparse.ArgumentParser(description="Recording tool outputs lets a run replay deterministically offline; re-running live diverges because non-deterministic tools have moved on.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--diverge", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("recorded_time=%d  current_time=%d  steps=%d  file=%s  (the recording is a fixture)"
          % (data["recorded_time"], data["current_time"], len(data["recording"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.diverge:
        diverge_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
