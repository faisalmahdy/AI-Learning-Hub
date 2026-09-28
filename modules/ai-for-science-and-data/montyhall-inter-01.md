---
id: montyhall-inter-01
title: Switching wins Monty Hall 2/3 of the time — but only because of how the host chose the door to open
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 17 min
summary: You pick one of three doors; a car is behind one, goats behind the other two. The host, who knows where the car is, opens a different door to reveal a goat and asks if you want to switch. Intuition says the two remaining doors are 50/50, but switching wins 2/3 of the time and staying only 1/3 — your first pick was right 1/3 of the time and nothing the host did changed that, so the other door carries the remaining 2/3. The subtle part is that the answer depends entirely on the host's policy, not on what you see. A host who knows the car's location and is constrained to reveal a goat leaks information; a host who opens a random unpicked door and happens to reveal a goat leaks nothing, so from those runs switching is a coin flip. Same visible goat, different probability, because the data-generating process differs. On an exact enumeration (no simulation), the knowing host gives switch = 2/3 and stay = 1/3, while the ignorant host who revealed a goat gives switch = 1/2.
eli5: Three cups, a ball under one. You point at a cup. A friend who knows where the ball is turns over a different empty cup and asks if you want to change your guess to the last cup. It feels like a 50/50 now, but you should switch — your first point was probably wrong (two chances in three), and your friend was forced to leave the ball's cup closed, so the ball is probably under the cup you can switch to. The trick only works because your friend knew where the ball was and avoided it on purpose. If they'd flipped a cup at random and it happened to be empty, switching wouldn't help.
---

## Why this module

The Monty Hall answer is famous for being counterintuitive, but the lesson underneath it is the one that matters for data: a probability is not a property of the outcome you see, it is a property of the process that produced it, and two processes can hand you the identical observation with different odds behind it.

Here is the game. Three doors, a car behind one and goats behind the other two. You pick a door. The host — who knows where the car is — opens one of the other two doors to reveal a goat, then offers you the chance to switch to the remaining unopened door. Almost everyone reasons: two doors are left, one has the car, so it is 50/50 and switching is pointless. That reasoning is wrong, and the exact answer is that switching wins two times out of three. The clean way to see it: your original pick had a 1/3 chance of being the car, and the host revealing a goat did nothing to change how good your original guess was. So your door is still worth 1/3, which means the other unopened door must be worth the entire remaining 2/3 — the host, forced to open a goat door and forbidden to open the car, effectively swept that probability onto the single door he left closed.

**Switching wins 2/3 and staying 1/3, because your first pick is right only 1/3 of the time and the host — constrained to avoid the car — concentrates the other 2/3 onto the one door he leaves closed.**

The deep part is why the number is 2/3 and not 1/2, and it is entirely about the host's *policy*. You see the same thing in every version of the game — a goat behind a door the host opened — but what that observation tells you depends on how the host chose which door to open. A host who knows the car's location and is required to reveal a goat has made a constrained choice, and a constrained choice carries information: the door he did not open is special. A host who opens a random unpicked door and merely happens to reveal a goat this time has made an unconstrained choice that tells you nothing about the remaining doors, so among those runs switching is genuinely 50/50. Identical observation, different probability, because the data-generating process differs. This module enumerates every case exactly — no simulation — for both host policies.

## Concepts

**Your first pick is right 1/3 of the time.** With the car placed uniformly, the door you choose has a 1/3 chance of hiding it, and this number is fixed before the host acts.

**Staying wins exactly when your first pick was the car; switching wins exactly when it wasn't.** After the host clears the other goat, the only unopened door besides yours holds the car precisely in the 2/3 of cases where your first pick missed.

```python filename=modules/ai-for-science-and-data/code/montyhall-inter-01/montyhall.py:41-51 COMPLETE
def knowing_host_probs(doors):
    """Exact P(switch wins) and P(stay wins) when the host always opens a goat door that isn't the pick."""
    switch_wins = Fraction(0)
    stay_wins = Fraction(0)
    for car, pick in product(range(doors), range(doors)):
        w = Fraction(1, doors * doors)                 # each (car, pick) is equally likely
        if pick == car:
            stay_wins += w                             # staying wins exactly when the first pick was the car
        else:
            switch_wins += w                           # host clears the other goat, so switching lands on the car
    return switch_wins, stay_wins
```

**The host's constraint is the information.** Because he must avoid the car, the door he leaves closed inherits the probability of every arrangement where your pick was wrong — which is why the closed door, not your door, is where the 2/3 collects.

<svg role="img" aria-label="The first pick holds 1/3 of the probability; the two other doors together hold 2/3, and the host opening a goat funnels that 2/3 onto the single remaining closed door" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">where the probability sits, before and after the host opens a goat</text>
  <rect x="20" y="26" width="60" height="24" fill="var(--s1)"/><text x="34" y="42" fill="var(--panel)" font-size="8">pick 1/3</text>
  <rect x="90" y="26" width="60" height="24" fill="var(--s2)"/><text x="104" y="42" fill="var(--panel)" font-size="8">door 1/3</text>
  <rect x="160" y="26" width="60" height="24" fill="var(--s2)"/><text x="174" y="42" fill="var(--panel)" font-size="8">door 1/3</text>
  <text x="20" y="66" fill="var(--muted)" font-size="7">host opens a goat among the two others ↓</text>
  <rect x="20" y="70" width="60" height="24" fill="var(--s1)"/><text x="34" y="86" fill="var(--panel)" font-size="8">pick 1/3</text>
  <rect x="90" y="70" width="60" height="24" fill="none" stroke="var(--muted)" stroke-dasharray="3 2"/><text x="98" y="86" fill="var(--muted)" font-size="8">opened 0</text>
  <rect x="160" y="70" width="60" height="24" fill="var(--s2)"/><text x="168" y="86" fill="var(--panel)" font-size="8">closed 2/3</text>
  <text x="228" y="86" fill="var(--muted)" font-size="7">← switch here</text>
</svg>
^ Your pick keeps its 1/3; the host opening a goat on one of the other two doors funnels their combined 2/3 onto the single door he leaves closed, so switching wins 2/3.

**Switching wins 2/3 not because the odds "reset" to the two remaining doors, but because the host's forced avoidance of the car concentrates the probability your first pick did not claim onto the one door he leaves closed.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/montyhall-inter-01/montyhall.py

The fixture is the three-door game and the two host policies to compare.

```json filename=modules/ai-for-science-and-data/code/montyhall-inter-01/montyhall.json:3-4 COMPLETE
  "doors": 3,
  "host_policies": ["knowing", "ignorant"]
```

Run `--enumerate` to list every equally-likely arrangement and who wins.

```text filename=--enumerate
ENUMERATE — every (car, pick) case under the knowing host (each equally likely)
----------------------------------------------------------
  car  pick   staying wins   switching wins
   0    0      True           False
   0    1      False          True
   0    2      False          True
   1    0      False          True
   1    1      True           False
   1    2      False          True
   2    0      False          True
   2    1      False          True
   2    2      True           False
```

There are nine equally likely (car, pick) arrangements. Staying wins in exactly the three where your pick already sits on the car — the diagonal, car 0/pick 0, car 1/pick 1, car 2/pick 2 — which is 3 of 9, or 1/3. Switching wins in the other six, where your pick missed and the host, clearing the remaining goat, leaves the car behind the door you switch to: 6 of 9, or 2/3. There is no probability hiding in the host's choice of which goat to open when you happened to pick the car — it splits that case but does not move the totals. The whole 2/3 is already visible in the enumeration: switching is just the bet that your first guess was wrong, and your first guess is wrong two times out of three.

<svg role="img" aria-label="A 3x3 grid of car by pick; the three diagonal cells are staying-wins and the other six are switching-wins" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">3×3 arrangements: diagonal = staying wins, off-diagonal = switching wins</text>
  <text x="8" y="34" fill="var(--muted)" font-size="7">car→</text>
  <g font-size="7" fill="var(--muted)"><text x="52" y="24">0</text><text x="92" y="24">1</text><text x="132" y="24">2</text></g>
  <rect x="40" y="28" width="34" height="20" fill="var(--s1)"/><rect x="80" y="28" width="34" height="20" fill="var(--s2)"/><rect x="120" y="28" width="34" height="20" fill="var(--s2)"/>
  <rect x="40" y="50" width="34" height="20" fill="var(--s2)"/><rect x="80" y="50" width="34" height="20" fill="var(--s1)"/><rect x="120" y="50" width="34" height="20" fill="var(--s2)"/>
  <rect x="40" y="72" width="34" height="20" fill="var(--s2)"/><rect x="80" y="72" width="34" height="20" fill="var(--s2)"/><rect x="120" y="72" width="34" height="20" fill="var(--s1)"/>
  <rect x="180" y="34" width="12" height="10" fill="var(--s1)"/><text x="196" y="43" fill="var(--muted)" font-size="7">stay wins: 3/9 = 1/3</text>
  <rect x="180" y="52" width="12" height="10" fill="var(--s2)"/><text x="196" y="61" fill="var(--muted)" font-size="7">switch wins: 6/9 = 2/3</text>
  <text x="6" y="104" fill="var(--muted)" font-size="8">switching wins in every cell where your pick missed the car — two-thirds of them</text>
</svg>
^ The three diagonal cells (pick equals car) are the staying-wins; the six off-diagonal cells are the switching-wins, so switching takes 6 of 9 arrangements.

## Build

Now the twist that reveals the real lesson. Run `--reveal` to compare the two host policies against the same visible outcome — a goat behind an opened door.

```text filename=--reveal
REVEAL — the same goat behind an opened door, two host policies, two answers
--------------------------------------------------------------
  knowing host (opens a goat on purpose):   P(switch wins) = 2/3
  knowing host:                             P(stay wins)   = 1/3
  ignorant host (opened at random, hit a goat this run):    1/2
--------------------------------------------------------------
  you saw a goat either way; what is behind the other door depends on how it was chosen.
```

Under the knowing host, switching is 2/3, as enumerated. Under the ignorant host — who opens a uniformly random unpicked door and just happened, this run, to reveal a goat — switching drops to exactly 1/2. You cannot tell the two situations apart by looking: both show you a goat behind a door the host opened. The difference is invisible in the outcome and total in the process. The ignorant host's code makes it explicit: it enumerates the runs where he opened a random door, throws away the runs where he accidentally revealed the car, and among the survivors counts how often switching wins.

```python filename=modules/ai-for-science-and-data/code/montyhall-inter-01/montyhall.py:54-68 COMPLETE
def ignorant_host_switch_prob(doors):
    """Exact P(switch wins | host revealed a goat) when the host opens a RANDOM unpicked door (may hit the car)."""
    good = Fraction(0)   # runs where the opened door was a goat AND switching wins
    revealed_goat = Fraction(0)   # runs where the opened door was a goat (the condition)
    for car, pick in product(range(doors), range(doors)):
        others = [d for d in range(doors) if d != pick]
        for opened in others:                          # host opens a uniformly random unpicked door
            w = Fraction(1, doors * doors * len(others))
            if opened == car:
                continue                               # host accidentally revealed the car: excluded by conditioning
            revealed_goat += w
            switch_to = [d for d in range(doors) if d != pick and d != opened][0]
            if switch_to == car:
                good += w
    return good / revealed_goat
```

The reason the ignorant host gives 1/2 is that throwing away the "revealed the car" runs also throws away information. When your pick was wrong, the ignorant host reveals the car half the time (and those runs are discarded), so the surviving wrong-pick runs are downweighted to exactly balance the right-pick runs — leaving a genuine coin flip. The knowing host never discards anything, because he never reveals the car, so all of your wrong-pick probability survives and switching keeps its 2/3. This is the mathematical statement of "condition on how the data was generated": the same event, "a goat was revealed," has a different posterior depending on the mechanism that could have revealed other things.

<svg role="img" aria-label="Both hosts show a goat behind an opened door, but the knowing host yields switch 2/3 and the ignorant host who happened to reveal a goat yields switch 1/2" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">identical observation: a goat behind the opened door</text>
  <rect x="10" y="22" width="120" height="20" fill="none" stroke="var(--line)"/><text x="16" y="36" fill="var(--ink)" font-size="8">knowing host</text>
  <line x1="130" y1="32" x2="168" y2="32" stroke="var(--s1)"/><polygon points="168,29 174,32 168,35" fill="var(--s1)"/>
  <rect x="176" y="22" width="60" height="20" fill="var(--s1)"/><text x="182" y="36" fill="var(--panel)" font-size="8">switch 2/3</text>
  <rect x="10" y="58" width="120" height="20" fill="none" stroke="var(--line)"/><text x="16" y="72" fill="var(--ink)" font-size="8">ignorant host</text>
  <line x1="130" y1="68" x2="168" y2="68" stroke="var(--s2)"/><polygon points="168,65 174,68 168,71" fill="var(--s2)"/>
  <rect x="176" y="58" width="45" height="20" fill="var(--s2)"/><text x="182" y="72" fill="var(--panel)" font-size="8">switch 1/2</text>
  <text x="6" y="94" fill="var(--muted)" font-size="8">same goat, different odds — the host's policy is the hidden variable</text>
</svg>
^ Both policies present the same observation, a revealed goat, yet the knowing host makes switching a 2/3 bet and the ignorant host makes it a 1/2 coin flip — the probability lives in the process, not the picture.

## Definition of done

The self-test pins both policies exactly: switching is 2/3 and staying 1/3 under the knowing host, the two partition the probability, and the ignorant host who revealed a goat is 1/2.

```python filename=modules/ai-for-science-and-data/code/montyhall-inter-01/montyhall.py:110-123 COMPLETE
    switch_two_thirds = sw == Fraction(2, 3)
    print("  switching wins exactly 2/3 under the knowing host = %s (%s)" % (switch_two_thirds, sw))

    stay_one_third = st == Fraction(1, 3)
    print("  staying wins exactly 1/3 under the knowing host = %s (%s)" % (stay_one_third, st))

    switch_beats_stay = sw > st
    print("  switching strictly beats staying = %s (%s > %s)" % (switch_beats_stay, sw, st))

    probs_sum_to_one = sw + st == 1
    print("  the two knowing-host outcomes partition the probability = %s (%s + %s = 1)" % (probs_sum_to_one, sw, st))

    ignorant_is_half = ig == Fraction(1, 2)
    print("  the ignorant host who revealed a goat gives switch = 1/2 = %s (%s)" % (ignorant_is_half, ig))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — switching wins 2/3 and staying 1/3 under the knowing host; the ignorant-host-revealed-a-goat case is 1/2
--------------------------------------------------------------------------------------------------------------------
  switching wins exactly 2/3 under the knowing host = True (2/3)
  staying wins exactly 1/3 under the knowing host = True (1/3)
  switching strictly beats staying = True (2/3 > 1/3)
  the two knowing-host outcomes partition the probability = True (2/3 + 1/3 = 1)
  the ignorant host who revealed a goat gives switch = 1/2 = True (1/2)
  same visible goat, different answer by host policy = True (2/3 vs 1/2)
```

**Done means the answer and its dependence on the process are both proven exactly: under the knowing host switching wins 2/3 and staying 1/3 (partitioning the probability), while the ignorant host who happened to reveal a goat gives switching exactly 1/2 — the same visible goat, two different odds, because the host's policy is the data-generating process.**

## Boss fight

Predict the two variations that flip the intuition again — the case where the host has a choice and might bias it, and the version at scale. It is tempting to think "always switch" is the universal rule.

The first trap is the host's tie-break when you *do* pick the car. Then two goat doors are openable and the host must choose between them, and the standard problem assumes he chooses uniformly. If instead he has a known bias — say he prefers the lower-numbered door whenever he is free to choose — then which door he opens carries extra information, and your switch probability conditioned on the specific door he opened can move away from 2/3 for that particular observation (though it still averages to 2/3 overall). The general lesson is that every detail of the host's decision rule is part of the model: change how he breaks ties, whether he always offers a switch, or whether he only offers it when you picked the car (the "Monty from Hell" who offers a switch precisely to lure you off the winning door), and the optimal action changes completely. There is no answer to "should I switch?" without the host's full policy — the observation alone is not enough, which is exactly the point, and you can settle any variant by enumerating it.

```python filename=modules/ai-for-science-and-data/code/montyhall-inter-01/montyhall.py:78-83 COMPLETE
    stay = switch = 0
    for car, pick in product(range(doors), range(doors)):
        s = pick == car
        print("   %d    %d      %-12s   %s" % (car, pick, s, not s))
        stay += 1 if s else 0
        switch += 0 if s else 1
```

The second trap is that the effect gets stronger, not weaker, with more doors. With a hundred doors, you pick one (1/100 chance of the car), the knowing host opens ninety-eight goat doors, and switching to the single remaining door wins 99/100 — because your original 1/100 is unchanged and the entire 99/100 collects on the one door the host was forced to leave closed. The intuition that "two doors left means 50/50" is most seductive at three doors, where the numbers are close; at a hundred doors it is obvious that the host telling you "the car is behind your door or this one specific other door" out of a hundred is overwhelming evidence for the other one. The same mechanism — a constrained reveal concentrating probability — scales with the number of doors the host clears, which is why Monty Hall is not a quirk of the number three but a general fact about conditioning on an informative, non-random observation. In real analysis this is missing-not-at-random data: when the reason a value is hidden depends on the value itself, the mechanism that hid it is part of the likelihood, and ignoring it gives the wrong posterior.

**The Monty Hall answer — switch, winning 2/3 at three doors and 99/100 at a hundred — follows entirely from the host's policy of making a constrained, informative reveal, so it is not a fact about the doors you see but about the process that opened one: change the host's tie-break, his offer rule, or his knowledge and the optimal action changes, because a conditional probability must condition on how the observation was generated, not on the observation alone.**

## External resources

Any probability text's treatment of the Monty Hall problem and conditional probability / Bayes' rule — the formal derivation of the 2/3 result and the explicit role of the host's door-opening distribution in the likelihood.

Writing on the "Monty Fall" / ignorant-host variant and on missing-not-at-random (MNAR) data and informative missingness — the general statistical principle that the mechanism producing an observation must be modeled, not just the observation, of which Monty Hall is the cleanest example.

The companion "a 99% detector that is mostly wrong when it fires" (base-rate) and "selecting on a common effect fakes a correlation" (Berkson) modules — all three are conditional-probability traps where the right answer depends on conditioning correctly on how the data was selected or revealed.
