"""Execute the tool call and supply the real observation -- never feed back the observation the model wrote itself -- because a model will narrate a plausible result instead of calling the tool, and trusting it lets the model reason over data it invented.

A tool-using loop has a clean division of labor: the model decides what to do (emits an action), and the harness does it (runs the tool and returns the result). Models blur that division. Trained on transcripts where a tool call is followed by its output, a model will continue the pattern and write the output too -- an 'Observation: found 42 results' line it simply made up, because that is what comes next in the text it learned from.

That narrated observation is not grounded in anything. No tool ran; the model generated a result the way it generates any other token, and it can be confidently, specifically wrong. The only trustworthy result is the one the tool actually returns when the harness executes the call. So the harness must treat the model's entire output as a request -- extract the action, ignore any result the model claimed -- run the tool, and inject the tool's real output as the observation.

Skip that and the loop closes on itself. The harness feeds the model's fabricated observation back to the model as if it were real, the model reads its own invention as ground truth, and every subsequent step reasons on fiction. There is no error to catch: the fabricated result is well-formed text, the run proceeds smoothly, and the final answer is built on numbers the tool never produced. The model has graded its own homework, and passed.

The discipline is to make the tool the sole source of observations. The model's job ends at proposing the call; the observation is the harness's to produce, from real execution, every time. A result the model wrote is input to be discarded, not output to be trusted.

The rule: execute the tool call and use the tool's real output as the observation, discarding any observation the model wrote itself -- because a self-narrated result is ungrounded generated text that can be wrong, and feeding it back lets the model reason over its own fabrication with no error to reveal it.

On this fixture the model narrates a result for each of three calls; two of the three narrated results disagree with what the tool actually returns. A harness that trusts the model reasons on the fabrications; one that executes uses the real outputs. This computes both.

  --observe   each turn's model-claimed observation vs the tool's real output, and whether they match
  --fabricated the turns where the model's narrated result differs from reality
  --check     trusting the model's narrated observation feeds back fabrications; executing uses the tool's real output

turns is the fixture; the observations used under each harness and the fabrications are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "fakeobs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def trust_model(turn):
    """Naive harness: use the observation the model wrote for itself."""
    return turn["claimed"]


def execute_tool(turn):
    """Correct harness: use the observation the tool actually produced."""
    return turn["real"]


def is_fabricated(turn):
    """The model's narrated result disagrees with what the tool really returns."""
    return turn["claimed"] != turn["real"]


# ----------------------------------------------------------------- printing

def observe_view(data):
    turns = data["turns"]
    print("OBSERVE — model's claimed observation vs the tool's real output")
    print("-" * 66)
    print("  call            claimed            real               match?")
    for t in turns:
        print("  %-14s  %-17s  %-17s  %s"
              % (t["call"], t["claimed"], t["real"], not is_fabricated(t)))
    print("-" * 66)
    print("  where they differ, the model invented a result the tool never returned")


def fabricated_view(data):
    turns = data["turns"]
    fab = [t for t in turns if is_fabricated(t)]
    print("FABRICATED — turns where the model narrated a wrong result")
    print("-" * 60)
    for t in fab:
        print("  %s: model said '%s', tool returned '%s'" % (t["call"], t["claimed"], t["real"]))
    print("-" * 60)
    print("  a harness that trusts the model would reason on these invented results")


def check(data):
    print("SELF-TEST — trusting the model's narrated observation feeds back fabrications; executing uses the tool's real output")
    print("-" * 120)
    turns = data["turns"]

    fab = [t for t in turns if is_fabricated(t)]
    model_fabricates = len(fab) > 0
    print("  the model narrated a wrong result on some turn = %s (%d of %d)" % (model_fabricates, len(fab), len(turns)))

    naive_obs = [trust_model(t) for t in turns]
    naive_uses_fabrication = any(o == t["claimed"] and is_fabricated(t) for o, t in zip(naive_obs, turns))
    print("  trusting harness feeds back a fabricated observation = %s" % naive_uses_fabrication)

    correct_obs = [execute_tool(t) for t in turns]
    correct_uses_real = all(o == t["real"] for o, t in zip(correct_obs, turns))
    print("  executing harness uses the tool's real output every turn = %s" % correct_uses_real)

    observations_differ = naive_obs != correct_obs
    print("  the two harnesses end up with different observations = %s" % observations_differ)

    correct_never_fabricated = all(o != t["claimed"] or not is_fabricated(t) for o, t in zip(correct_obs, turns))
    print("  the executing harness never uses a fabricated value = %s" % correct_never_fabricated)

    ok = (model_fabricates and naive_uses_fabrication and correct_uses_real
          and observations_differ and correct_never_fabricated)
    print("-" * 120)
    print("SELF-TEST %s  model_fabricates=%s  naive_uses_fabrication=%s  correct_uses_real=%s  observations_differ=%s  correct_never_fabricated=%s"
          % ("PASS" if ok else "FAIL", model_fabricates, naive_uses_fabrication, correct_uses_real,
             observations_differ, correct_never_fabricated))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fabricated observations: execute the tool call and use the tool's real output as the observation, discarding any observation the model wrote itself -- because a self-narrated result is ungrounded generated text that can be wrong, and feeding it back lets the model reason over its own fabrication with no error to reveal it.")
    p.add_argument("--observe", action="store_true")
    p.add_argument("--fabricated", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("turns=%d  file=%s  (each turn's call, claimed result, and real result are a fixture)"
          % (len(data["turns"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.observe:
        observe_view(data)
    elif args.fabricated:
        fabricated_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
