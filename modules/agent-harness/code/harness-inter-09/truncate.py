"""Cap a tool result with head+tail before it enters the context -- append it whole and you overflow the window; keep only the head and you cut off the answer.

A tool can hand the agent back anything: a 5-line status or a 5000-line log dump. If the harness appends
whatever it gets, one big result blows the context window and shoves earlier turns -- or later results --
out of the model's view. So tool output has to be bounded to a budget before it is appended. The lazy
bound is to keep the first N lines and drop the rest. But tools put their conclusion LAST: the final
result, the exception, the summary line. Head-only truncation keeps the boring preamble and throws away
the one line the agent needed.

The fix is head+tail truncation: keep the first half of the budget and the last half, with a marker for
what was cut. It fits the same budget as head-only but preserves both ends -- the context that opens the
output and the conclusion that closes it. On this fixture three results (10, 12, 8 lines) must fit a
20-line window. Appending them whole is 30 lines: it overflows and a whole result falls off the end.
Head-only truncation to 6 lines each fits in 18 but cuts off all three salient last lines. Head+tail
truncation to 6 lines each also fits in 18 and keeps every last line. This packs the transcript all
three ways and counts what survives.

  --results    the three tool results and where the salient line sits (last)
  --pack       the transcript under append-whole vs head-only vs head+tail, with lines used
  --check      append-whole overflows, head-only loses the salient tails, head+tail fits and keeps them

The results, window, and cap are the fixture; every packed transcript and count is computed. Stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "results.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def salient(result):
    """The line that matters: the last line of the tool output (its result or error)."""
    return result["lines"][-1]


# ------------------------------------------------------------- three packing strategies

def pack_append_whole(results, window, cap):
    """Append every line, uncapped. Returns the full transcript -- only its first `window` lines fit."""
    transcript = []
    for r in results:
        transcript.extend(r["lines"])
    return transcript


def in_context(transcript, window):
    """The lines that actually survive into the model's window -- the rest fall off the end."""
    return transcript[:window]


def pack_head_only(results, window, cap):
    """Keep the first `cap` lines of each result -- fits the budget but drops the tail where the answer is."""
    transcript = []
    for r in results:
        transcript.extend(r["lines"][:cap])
    return transcript


def pack_head_tail(results, window, cap):
    """Keep the first cap/2 and last cap/2 lines of each, with a marker -- fits AND keeps both ends."""
    transcript = []
    for r in results:
        lines = r["lines"]
        if len(lines) <= cap:
            transcript.extend(lines)
            continue
        half = cap // 2
        cut = len(lines) - 2 * half
        transcript.extend(lines[:half])
        transcript.append("[... %d lines truncated ...]" % cut)
        transcript.extend(lines[-half:])
    return transcript


def salients_kept(transcript, results):
    """How many results' salient last line survived into the packed transcript."""
    return sum(1 for r in results if salient(r) in transcript)


# ----------------------------------------------------------------- printing

def results_view(data):
    print("RESULTS — three tool outputs; the salient line is the last of each")
    print("-" * 54)
    for r in data["results"]:
        print("  %-6s %2d lines, ends: %s" % (r["name"], len(r["lines"]), salient(r)))
    print("-" * 54)
    print("  window=%d lines, per-result cap=%d; the three total %d lines."
          % (data["window_lines"], data["per_result_cap"], sum(len(r["lines"]) for r in data["results"])))


def pack_view(data):
    results, window, cap = data["results"], data["window_lines"], data["per_result_cap"]
    strategies = [
        ("append whole", pack_append_whole),
        ("head only", pack_head_only),
        ("head + tail", pack_head_tail),
    ]
    print("PACK — lines produced, fits window, and salient last-lines kept (of 3)")
    print("-" * 62)
    for name, fn in strategies:
        t = fn(results, window, cap)
        fits = "fits" if len(t) <= window else "OVERFLOW"
        kept = salients_kept(in_context(t, window), results)
        print("  %-13s %2d lines  %-9s salients kept: %d/3" % (name, len(t), fits, kept))
    print("-" * 62)
    print("  append-whole overflows; head-only fits but loses the answers; head+tail keeps them.")


def check(data):
    print("SELF-TEST — append-whole overflows; head-only loses the salient tails; head+tail fits and keeps them")
    print("-" * 92)
    results, window, cap = data["results"], data["window_lines"], data["per_result_cap"]

    whole = pack_append_whole(results, window, cap)
    whole_overflows = len(whole) > window
    whole_kept = salients_kept(in_context(whole, window), results)
    whole_drops = whole_kept < len(results)
    print("  appending whole overflows the window and drops a result = %s (%d lines > %d, %d/%d salients)"
          % (whole_overflows and whole_drops, len(whole), window, whole_kept, len(results)))

    head = pack_head_only(results, window, cap)
    head_fits = len(head) <= window
    head_loses = salients_kept(head, results) == 0
    print("  head-only fits but loses every salient tail = %s (%d lines, %d/%d salients)"
          % (head_fits and head_loses, len(head), salients_kept(head, results), len(results)))

    ht = pack_head_tail(results, window, cap)
    ht_fits = len(ht) <= window
    ht_keeps_all = salients_kept(ht, results) == len(results)
    print("  head+tail fits AND keeps every salient tail = %s (%d lines, %d/%d salients)"
          % (ht_fits and ht_keeps_all, len(ht), salients_kept(ht, results), len(results)))

    ht_beats_head = salients_kept(ht, results) > salients_kept(head, results)
    print("  head+tail preserves more answers than head-only at the same cap = %s (%d vs %d)"
          % (ht_beats_head, salients_kept(ht, results), salients_kept(head, results)))

    ok = (whole_overflows and whole_drops) and (head_fits and head_loses) and (ht_fits and ht_keeps_all) and ht_beats_head
    print("-" * 92)
    print("SELF-TEST %s  whole_overflows=%s  head_loses=%s  headtail_keeps=%s  headtail_beats_head=%s"
          % ("PASS" if ok else "FAIL", whole_overflows and whole_drops, head_fits and head_loses,
             ht_fits and ht_keeps_all, ht_beats_head))
    return ok


def main():
    p = argparse.ArgumentParser(description="Cap a tool result with head+tail before it enters the context.")
    p.add_argument("--results", action="store_true")
    p.add_argument("--pack", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("results=%d  window=%d  cap=%d  file=%s  (the results and budget are a fixture)"
          % (len(data["results"]), data["window_lines"], data["per_result_cap"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.results:
        results_view(data)
    elif args.pack:
        pack_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
