"""Reserve a completion budget in the context window -- the input and the model's output share one token limit, so a harness that packs the input up to the window leaves no room for a response and the answer is truncated or the request is rejected; cap the input at window minus the reserved output and trim history to fit.

A context window is a hard limit on the whole request: every token sent in plus every token generated out must fit inside it. The easy mistake is to treat the window as a bound on the input alone, and fill the conversation history until the input reaches the window. But the output has not been generated yet, and it needs tokens too.

So an input that fills the window leaves zero for the response. Depending on the API, the request is rejected because the input plus the reserved output exceeds the limit, or the model is handed only the few tokens left over and its answer is cut off mid-sentence. Either way the agent stops being able to act, and it happens precisely as the conversation gets long and interesting -- when the history has grown enough to crowd out the reply.

The fix is to reserve the output budget before packing the input. Decide how many tokens the response may need -- a max_tokens -- and cap the input at window minus that. Then fit the input under the cap by evicting or compacting history, keeping the most recent turns because they matter most. Now the input plus the reserved output always fit, and the model always has room to answer.

On this fixture the window is 1000, the system prompt is 100, the tool definitions are 150, the reserved completion budget is 300, and history is four turns of 200. Packing everything makes the input 1050 -- already over the window -- with negative room for output. Reserving 300 caps the input at 700, trims history to the two most recent turns, gives an input of 650, and leaves 350 for the response. This computes both.

  --naive     fill the input to the window: input 1050, no room left for the output
  --reserved  cap the input at window minus max_tokens: input 650, history trimmed to recent turns, 350 for output
  --check     the naive input leaves less than the reserved output (in fact overflows), while the reserved plan keeps at least max_tokens for the output, stays within the window, and keeps the most recent turns

the window and component sizes are the fixture; each strategy's input size, output room, and kept history turns are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "headroom.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def naive_input(d):
    """Pack everything: system + tools + all of history, ignoring the output's need for tokens."""
    return d["system"] + d["tools"] + sum(d["history"])


def reserved_history(d):
    """Keep the most recent history turns that fit under window - max_tokens (after system + tools)."""
    budget = d["window"] - d["max_tokens"] - d["system"] - d["tools"]
    kept, total = [], 0
    for turn in reversed(d["history"]):
        if total + turn <= budget:
            kept.insert(0, turn)
            total += turn
    return kept


def reserved_input(d):
    """The input under the reserved plan: system + tools + the kept history."""
    return d["system"] + d["tools"] + sum(reserved_history(d))


def output_room(d, input_tokens):
    """Tokens left in the window for the model's response after the input."""
    return d["window"] - input_tokens


# ----------------------------------------------------------------- printing

def naive_view(d):
    inp = naive_input(d)
    print("NAIVE — fill the input to the window %d" % d["window"])
    print("-" * 64)
    print("  system %d + tools %d + history %s = input %d" % (d["system"], d["tools"], d["history"], inp))
    print("  room left for output = %d   (need %d)" % (output_room(d, inp), d["max_tokens"]))
    print("-" * 64)
    print("  the input alone meets or exceeds the window, so the response has no room")


def reserved_view(d):
    kept = reserved_history(d)
    inp = reserved_input(d)
    print("RESERVED — cap the input at window - max_tokens = %d" % (d["window"] - d["max_tokens"]))
    print("-" * 64)
    print("  kept history (most recent): %s   (dropped %d of %d turns)" % (kept, len(d["history"]) - len(kept), len(d["history"])))
    print("  system %d + tools %d + history %d = input %d" % (d["system"], d["tools"], sum(kept), inp))
    print("  room left for output = %d   (need %d)   input + reserved = %d <= %d" % (output_room(d, inp), d["max_tokens"], inp + d["max_tokens"], d["window"]))
    print("-" * 64)
    print("  the reserved output budget is protected, and the newest turns are kept")


def check(d):
    print("SELF-TEST — the naive input leaves less than the reserved output while the reserved plan keeps at least max_tokens for output, stays within the window, and keeps the most recent turns")
    print("-" * 112)
    mt = d["max_tokens"]

    n_in = naive_input(d)
    naive_no_room = output_room(d, n_in) < mt
    print("  naive leaves less than the needed output budget = %s (room %d < %d)" % (naive_no_room, output_room(d, n_in), mt))

    r_in = reserved_input(d)
    reserved_reserves = output_room(d, r_in) >= mt
    print("  reserved keeps at least max_tokens for the output = %s (room %d >= %d)" % (reserved_reserves, output_room(d, r_in), mt))

    reserved_within_window = r_in + mt <= d["window"]
    print("  reserved input plus reserved output fits the window = %s (%d <= %d)" % (reserved_within_window, r_in + mt, d["window"]))

    kept = reserved_history(d)
    reserved_keeps_recent = kept == d["history"][len(d["history"]) - len(kept):]
    print("  reserved keeps the most recent turns (a suffix of history) = %s (%s)" % (reserved_keeps_recent, kept))

    reserved_dropped = len(kept) < len(d["history"])
    print("  reserved dropped at least one old turn to make room = %s" % reserved_dropped)

    ok = (naive_no_room and reserved_reserves and reserved_within_window and reserved_keeps_recent and reserved_dropped)
    print("-" * 112)
    print("SELF-TEST %s  naive_no_room=%s  reserved_reserves=%s  reserved_within_window=%s  reserved_keeps_recent=%s  reserved_dropped=%s"
          % ("PASS" if ok else "FAIL", naive_no_room, reserved_reserves, reserved_within_window, reserved_keeps_recent, reserved_dropped))
    return ok


def main():
    p = argparse.ArgumentParser(description="Completion headroom: reserve a max_tokens output budget in the context window and cap the input at window minus that budget, because the input and the model's output share one token limit -- packing the input to the window leaves no room for the response, so it is truncated or the request is rejected; trimming history to fit the cap (keeping recent turns) protects the reply.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--reserved", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("window=%d  system=%d  tools=%d  max_tokens=%d  history=%s  file=%s"
          % (d["window"], d["system"], d["tools"], d["max_tokens"], d["history"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.naive:
        naive_view(d)
    elif args.reserved:
        reserved_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
