---
id: fakeobs-inter-01
title: Execute the tool and supply the real observation — never feed back the result the model wrote itself, or it reasons over its own fabrication
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A tool-using loop has a clean division of labor — the model decides what to do (emits an action) and the harness does it (runs the tool and returns the result) — but models blur that division. Trained on transcripts where a tool call is followed by its output, a model will continue the pattern and write the output too: an "Observation: found 42 results" line it simply made up, because that is what comes next in the text it learned from. That narrated observation is not grounded in anything — no tool ran, the model generated a result the way it generates any other token, and it can be confidently, specifically wrong. The only trustworthy result is the one the tool actually returns when the harness executes the call, so the harness must treat the model's entire output as a request (extract the action, ignore any result the model claimed), run the tool, and inject the tool's real output as the observation. Skip that and the loop closes on itself: the harness feeds the model's fabricated observation back to the model as if it were real, the model reads its own invention as ground truth, and every subsequent step reasons on fiction — with no error to catch, because the fabricated result is well-formed text and the run proceeds smoothly to a final answer built on numbers the tool never produced. On a fixture where the model narrates a result for each of three calls, two of the three disagree with what the tool actually returns; a harness that trusts the model reasons on those fabrications while one that executes uses the real outputs.
eli5: Imagine you ask a friend to look up a fact in a book and tell you the answer. The honest way: they open the book, read it, and report what it says. But suppose your friend just guesses the answer and says it in the same confident tone as if they'd read it — "the book says 42!" — without ever opening the book. If you write "42" in your notes and build your whole report on it, you've built on a guess dressed up as a fact, and nothing warns you it was made up. The safe rule is: you open the book yourself. Your friend can point you to the page (that's their job), but the answer has to come from the book, not from what your friend claimed the book said. An AI agent's model is that friend — let it choose which tool to use, but always run the tool yourself and use what the tool really returns, never the result the model narrated.
---

## Why this module

The value of a tool in an agent loop is that it connects the model to ground truth — a real file, a real database, a real calculation — so the model's reasoning is anchored to facts it could not otherwise know or reliably produce. That anchoring only works if the observation the model reasons on actually came from the tool. If it came from the model, the tool has added nothing; the loop is just the model talking to itself with extra steps.

Models undermine this because of how they were trained. A transcript that shows an action is almost always followed by that action's result, so the pattern the model learned is "action, then observation." When it emits an action, its next most likely tokens are a plausible observation, and it will produce one whether or not a tool ran. The model is not lying in any deliberate sense; it is completing the pattern, and the completion is a guess formatted to look like a result.

The harness is the only thing that knows whether a tool actually ran, so it is the only thing that can enforce the anchor. Its job is to take the model's output as a proposal, execute the proposed action for real, and supply the genuine result — discarding whatever the model claimed. This module runs three turns where the model narrated a result and the tool returns a different one, and shows the two harnesses diverging.

**A tool anchors the model to ground truth only if the observation comes from the tool; a model completes the action-then-observation pattern by narrating a result, so a harness that trusts it lets the model reason on its own invention.**

## Concepts

The principle is single source of truth for observations: the tool, and only the tool, produces observations. The model's role ends at proposing the action. Any text the model writes that looks like a result is, by construction, not a result — it is a prediction of one, and predictions of tool outputs are exactly what tools exist to replace. Treating the model's narration as authoritative inverts the whole point of having tools.

The failure is uniquely insidious because it is self-reinforcing and silent. A wrong observation from a real tool at least came from reality and can be checked against it; a fabricated observation came from the same process that will consume it, so the model finds its own invention perfectly consistent with its expectations and builds on it without friction. There is no exception, no malformed output, no mismatch to detect from inside the loop — the fabrication is indistinguishable from a real result to everyone except the harness that could have executed the call.

The fix is mechanical and absolute: parse the action, run it, and construct the observation from the tool's return value, never from the model's text. With native tool-calling APIs this is largely enforced by the interface — the model emits a structured tool call and the platform supplies the result — but the discipline still matters wherever the loop is prompt-driven (a ReAct-style agent parsing text), where it is entirely up to the harness to strip any model-written observation and replace it with the real one. The moment the harness lets a model-authored result through, the tool has been bypassed.

<svg role="img" aria-label="The model's output split by the harness into an action, which is executed, and a narrated result, which is discarded; the observation is built only from the tool's return" viewBox="0 0 440 130">
<rect x="20" y="45" width="90" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="65" y="64" fill="var(--ink)" font-size="9" text-anchor="middle">model output</text>
<line x1="110" y1="52" x2="160" y2="38" stroke="var(--s1)"/>
<text x="135" y="34" fill="var(--s1)" font-size="7">action</text>
<line x1="110" y1="68" x2="160" y2="88" stroke="var(--s2)"/>
<text x="135" y="98" fill="var(--s2)" font-size="7">narrated result</text>
<rect x="160" y="26" width="70" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="195" y="42" fill="var(--ink)" font-size="8" text-anchor="middle">execute</text>
<text x="195" y="90" fill="var(--s2)" font-size="8" text-anchor="middle">DISCARD</text>
<line x1="230" y1="38" x2="290" y2="38" stroke="var(--muted)"/>
<rect x="290" y="26" width="60" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="320" y="42" fill="var(--ink)" font-size="8" text-anchor="middle">tool</text>
<line x1="350" y1="38" x2="400" y2="38" stroke="var(--s1)"/>
<text x="400" y="42" fill="var(--s1)" font-size="8">observation</text>
</svg>
^ The harness takes only the action from the model and executes it; the model's narrated result is discarded, and the observation is built solely from the tool's return.

**The tool is the single source of observations and the model's narration is a prediction, not a result; the fabrication is silent because the model consumes its own invention consistently, so the harness must construct every observation from the tool's return, never the model's text.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/fakeobs-inter-01. The fixture is three turns, each with the tool call, the observation the model wrote, and the tool's real output.

```json filename=modules/agent-harness/code/fakeobs-inter-01/fakeobs.json:3-6 COMPLETE
  "turns": [
    {"call": "search(widgets)", "claimed": "found 42", "real": "found 3"},
    {"call": "read(a.txt)",     "claimed": "contents: hello", "real": "contents: hello"},
    {"call": "calc(2+2)",       "claimed": "result: 5", "real": "result: 4"}
```

The naive harness uses the observation the model wrote for itself.

```python filename=modules/agent-harness/code/fakeobs-inter-01/fakeobs.py:34-36 COMPLETE
def trust_model(turn):
    """Naive harness: use the observation the model wrote for itself."""
    return turn["claimed"]
```

The correct harness uses the observation the tool actually produced.

```python filename=modules/agent-harness/code/fakeobs-inter-01/fakeobs.py:39-41 COMPLETE
def execute_tool(turn):
    """Correct harness: use the observation the tool actually produced."""
    return turn["real"]
```

A turn is a fabrication when the model's narrated result disagrees with the tool's.

```python filename=modules/agent-harness/code/fakeobs-inter-01/fakeobs.py:44-46 COMPLETE
def is_fabricated(turn):
    """The model's narrated result disagrees with what the tool really returns."""
    return turn["claimed"] != turn["real"]
```

Before running it, predict: the search and calc turns should show the model's claim differing from the real result, while the read turn happens to match. Run `--observe`:

```text filename=fakeobs.py --observe
OBSERVE — model's claimed observation vs the tool's real output
------------------------------------------------------------------
  call            claimed            real               match?
  search(widgets)  found 42           found 3            False
  read(a.txt)     contents: hello    contents: hello    True
  calc(2+2)       result: 5          result: 4          False
```

The prediction holds. The model claimed "found 42" where the tool returns "found 3", and "result: 5" where the calculator returns "result: 4" — two confident fabrications. The read turn matched, but only by luck; the harness has no way to know which claims are true without running the tool, so it must run all of them.

<svg role="img" aria-label="For three turns, the model's claimed result and the tool's real result side by side: search and calc differ, read matches" viewBox="0 0 440 150">
<text x="150" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">claimed (model)</text>
<text x="340" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">real (tool)</text>
<text x="40" y="45" fill="var(--ink)" font-size="9">search</text>
<rect x="100" y="34" width="100" height="16" fill="var(--s2)"/>
<text x="150" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">found 42</text>
<rect x="290" y="34" width="100" height="16" fill="var(--s1)"/>
<text x="340" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">found 3</text>
<text x="215" y="46" fill="var(--s2)" font-size="10" text-anchor="middle">≠</text>
<text x="40" y="80" fill="var(--ink)" font-size="9">read</text>
<rect x="100" y="69" width="100" height="16" fill="var(--s1)"/>
<text x="150" y="81" fill="var(--ink)" font-size="8" text-anchor="middle">hello</text>
<rect x="290" y="69" width="100" height="16" fill="var(--s1)"/>
<text x="340" y="81" fill="var(--ink)" font-size="8" text-anchor="middle">hello</text>
<text x="215" y="81" fill="var(--s1)" font-size="10" text-anchor="middle">=</text>
<text x="40" y="115" fill="var(--ink)" font-size="9">calc</text>
<rect x="100" y="104" width="100" height="16" fill="var(--s2)"/>
<text x="150" y="116" fill="var(--ink)" font-size="8" text-anchor="middle">result: 5</text>
<rect x="290" y="104" width="100" height="16" fill="var(--s1)"/>
<text x="340" y="116" fill="var(--ink)" font-size="8" text-anchor="middle">result: 4</text>
<text x="215" y="116" fill="var(--s2)" font-size="10" text-anchor="middle">≠</text>
</svg>
^ Two of the three narrated results disagree with the tool; the harness cannot tell which without executing, so it must execute every call.

Now isolate the fabrications. Run `--fabricated`:

```text filename=fakeobs.py --fabricated
FABRICATED — turns where the model narrated a wrong result
------------------------------------------------------------
  search(widgets): model said 'found 42', tool returned 'found 3'
  calc(2+2): model said 'result: 5', tool returned 'result: 4'
------------------------------------------------------------
  a harness that trusts the model would reason on these invented results
```

Two fabrications, each a confident wrong number. A trusting harness feeds "found 42" and "result: 5" back to the model, which then reasons as if those were real — searching a 42-item result set that has 3, or carrying a sum of 5 that is 4. The executing harness feeds back 3 and 4, and the model reasons on reality.

<svg role="img" aria-label="Two loops: the trusting harness feeds the model's fabrication back to the model, a closed self-consuming loop; the executing harness inserts the real tool result between them" viewBox="0 0 440 140">
<text x="110" y="18" fill="var(--s2)" font-size="9" text-anchor="middle">trusting: closed loop</text>
<rect x="70" y="35" width="80" height="26" fill="var(--panel)" stroke="var(--s2)"/>
<text x="110" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">model</text>
<path d="M150 48 Q 190 30, 190 55 Q 190 80, 150 62" fill="none" stroke="var(--s2)"/>
<text x="110" y="85" fill="var(--s2)" font-size="8" text-anchor="middle">reads its own claim</text>
<text x="330" y="18" fill="var(--s1)" font-size="9" text-anchor="middle">executing: tool in the loop</text>
<rect x="250" y="35" width="70" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="285" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">model</text>
<line x1="320" y1="48" x2="350" y2="48" stroke="var(--muted)"/>
<rect x="350" y="35" width="60" height="26" fill="var(--panel)" stroke="var(--s1)"/>
<text x="380" y="52" fill="var(--ink)" font-size="9" text-anchor="middle">tool</text>
<path d="M380 61 Q 330 90, 285 61" fill="none" stroke="var(--s1)"/>
<text x="330" y="98" fill="var(--s1)" font-size="8" text-anchor="middle">reads the tool's real result</text>
</svg>
^ Trusting the model closes the loop on its own fabrication; executing puts the tool in the loop so the observation comes from reality.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the model fabricates on some turn, that the trusting harness feeds back a fabrication, that the executing harness uses the real output every turn, that the two harnesses' observations differ, and that the executing harness never uses a fabricated value.

```python filename=modules/agent-harness/code/fakeobs-inter-01/fakeobs.py:80-94 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the executing harness ever admits a model-authored value:

```text filename=fakeobs.py --check
SELF-TEST — trusting the model's narrated observation feeds back fabrications; executing uses the tool's real output
------------------------------------------------------------------------------------------------------------------------
  the model narrated a wrong result on some turn = True (2 of 3)
  trusting harness feeds back a fabricated observation = True
  executing harness uses the tool's real output every turn = True
  the two harnesses end up with different observations = True
  the executing harness never uses a fabricated value = True
```

**The self-test checks that the executing harness's observation matches the tool and never the model's claim — proving the anchor holds even on the turn where the model's claim happened to be right, because correctness must not depend on the model's luck.**

## Definition of done

You can explain why a tool only anchors the model to ground truth if the observation comes from the tool, not the model.
You can explain why models narrate results — completing the action-then-observation pattern — and why that narration is a prediction, not a result.
You can explain why the fabrication is silent and self-reinforcing, with no error detectable from inside the loop.
You can state the fix as a single source of truth: the harness constructs every observation from the tool's return, discarding model-written results.
You can say why native tool-calling APIs largely enforce this and why prompt-driven (ReAct-style) loops must enforce it explicitly.

## Boss fight

Consider the turn where the model's claim happened to be right — the read that returned "hello" both ways. It is tempting to think trusting the model is harmless when it guesses correctly, and even to imagine an optimization: skip the tool call when the model's claim looks confident. That is the trap in a subtler form. The harness cannot know the claim is correct without running the tool, so "trust when confident" is just "trust," and the read matching was luck, not a signal. The lesson sharpens: you cannot selectively trust narrated observations, because the only way to verify one is the very execution that makes trusting it pointless — so execute unconditionally.

Now consider the mixed output, where the model emits a real action and also narrates the observation in the same turn. The harness must parse out the action and discard the narrated observation, which means the parser has to distinguish the two — the structured action to execute versus the prose result to drop. If it is sloppy and concatenates the model's narration with the real result, or lets the narration through when the action is malformed, the fabrication leaks back in. This is why the action extraction and the observation construction have to be separate, disciplined steps: extract only the action from the model, and build the observation only from the tool, with no path by which the model's text becomes an observation.

**You cannot selectively trust a narrated observation — verifying one requires the execution that makes trusting it pointless, so execute unconditionally — and when a turn mixes a real action with a narrated result, the harness must extract only the action and construct the observation solely from the tool, with no leak path.**

## External resources

The ReAct paper (Yao et al.) defines the interleaving of reasoning, action, and observation, where the observation is supplied by the environment — the discipline this module enforces against a model that would supply it itself.
Anthropic's and OpenAI's tool-use documentation describe the structured tool-call interface in which the platform executes the call and returns the result, the native enforcement of a tool-produced observation.
The topic's own modules on treating tool output as data and on grounding tool arguments cover the adjacent trust boundaries between the model and the world outside it.
