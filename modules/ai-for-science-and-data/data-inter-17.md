---
id: data-inter-17
title: Average over the right population — a student experiences a bigger class than the school reports
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 19 min
summary: "What is the average class size?" has two correct answers that disagree. The administrator averages over classes — add the sizes, divide by the count. A student does not sample classes; the student is in one, and a big class holds more students to be in it, so the average size experienced by a random student weights each class by its own size and is pulled toward the big classes. This is length-biased sampling — the same reason the bus you board is fuller than the average bus and the gap you wait in is longer than the average gap. The gap between the two averages is exactly the variance of the sizes over their mean; equal sizes make it vanish. On classes of 10, 10, 40 the administrator reports 20, the average student is in a class of 30 — a gap of 10, which is variance 200 over mean 20.
eli5: If you ask a school its average class size, it counts each class once and might say 20. But most kids are in the big classes — that is what makes them big — so if you ask the kids, the typical kid is in a class of 30. Neither number is wrong; they are answering different questions. Big things get sampled more just by being big, so the view from inside is always crowdier than the roster suggests.
---

## Why this module

The same data gives two different averages, both correct, and confusing them is how a true number becomes a misleading one.

Ask the administrator for the average class size and they average over classes: each class counts once. Ask a student what size class they are in and you are averaging over students — and a class of 40 supplies 40 students who all report 40, while a class of 10 supplies only 10. The student-weighted average is dragged toward the big classes, because big classes contain more of the people you are sampling. The result: the average class a student sits in is larger than the average class the school runs, and the two can differ dramatically without anyone lying.

**"Average class size" is ambiguous until you say which population you average over — per class or per student — and the two answers can be far apart.**

This is length-biased sampling, and it is everywhere: the bus you board carries more riders than the operator's average bus, the checkout line you join is longer than the average line, the gap between trains that your arrival lands in is longer than the average gap. Sampling proportional to size over-represents the big. This module computes both averages on one set of class sizes and proves the gap is exactly variance over mean.

## Concepts

The **per-class mean** is the ordinary average: sum the sizes, divide by the number of classes. Each class contributes equally. This is the administrator's number.

The **per-student mean** is the average class size a randomly chosen student is in. Weight each class by how many students it has — which is its own size — so the formula is the sum of squared sizes divided by the sum of sizes. Each class contributes in proportion to the students it holds.

The mechanism is size-weighting. A student is not a random class; a student is a random person, and people are concentrated in the big classes. Sampling a person therefore samples a class with probability proportional to its size, which up-weights the large ones exactly by the factor that makes them large.

There is an exact identity: the per-student mean minus the per-class mean equals the variance of the sizes divided by their mean. The gap is a pure measure of how spread out the sizes are. If every class is the same size, the variance is zero and the two averages coincide; the wider the spread, the wider the gap.

**The two averages differ by variance over mean, so the disagreement is not a mistake — it is the spread of the sizes, made visible.**

Picture the sampling itself: the administrator draws a class from a hat of classes; the student is drawn from a hat of students, where a big class has dropped in many more tickets.

<svg role="img" aria-label="Two hats: the class hat has one ticket per class; the student hat has one ticket per student, so the big class fills most of it" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="20" fill="var(--muted)" font-size="9">draw a class (per class)</text>
  <rect x="15" y="28" width="18" height="14" fill="var(--s2)"/>
  <rect x="37" y="28" width="18" height="14" fill="var(--s2)"/>
  <rect x="59" y="28" width="18" height="14" fill="var(--s1)"/>
  <text x="90" y="39" fill="var(--muted)" font-size="8">3 tickets: 10, 10, 40 — each once</text>
  <line x1="10" y1="55" x2="290" y2="55" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="72" fill="var(--muted)" font-size="9">draw a student (per student)</text>
  <rect x="15" y="80" width="10" height="14" fill="var(--s2)"/>
  <rect x="27" y="80" width="10" height="14" fill="var(--s2)"/>
  <rect x="39" y="80" width="60" height="14" fill="var(--s1)"/>
  <text x="105" y="91" fill="var(--muted)" font-size="8">60 tickets: the size-40 class fills 40 of them</text>
</svg>
^ Sampling a class gives each class one ticket; sampling a student gives each class as many tickets as it has students, so the big class dominates the second draw.

Neither average is the "right" one to fix. Both are correct for their population. The error is reporting one as if it answered the other's question — telling a prospective student "our average class size is 20" when the class they will actually sit in averages 30.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/data-inter-17/inspection.py

The fixture is three class sizes.

```json filename=modules/ai-for-science-and-data/code/data-inter-17/classes.json:1-4 COMPLETE
{
  "_meta": "The sizes of the classes at a small school. Two questions get two different averages: the administrator averages over CLASSES (each class counts once); a randomly chosen student experiences the average over STUDENTS (each class counts as many times as it has students). Because a big class contains more students to be sampled, the student-experienced average is pulled up -- length-biased sampling.",
  "sizes": [10, 10, 40]
}
```

The two means are two lines. The per-class mean divides by the class count; the per-student mean weights each class by its size, which is why the squares appear.

```python filename=modules/ai-for-science-and-data/code/data-inter-17/inspection.py:42-54 COMPLETE
def per_class_mean(sizes):
    """The administrator's average: each class counts once."""
    return sum(sizes) / len(sizes)


def per_student_mean(sizes):
    """The average class size a random student is in: each class weighted by its own size."""
    return sum(s * s for s in sizes) / sum(sizes)


def variance(sizes):
    m = per_class_mean(sizes)
    return sum((s - m) ** 2 for s in sizes) / len(sizes)
```

The `--averages` view reports both on the same class list so the two populations sit next to each other.

```python filename=modules/ai-for-science-and-data/code/data-inter-17/inspection.py:60-68 COMPLETE
    sizes = data["sizes"]
    total = sum(sizes)
    print("AVERAGES — the same classes, two populations")
    print("-" * 64)
    print("  class sizes: %s   (%d classes, %d students)" % (sizes, len(sizes), total))
    print("  per class (admin):    %.2f   each class weighted 1" % per_class_mean(sizes))
    print("  per student:          %.2f   each class weighted by its size" % per_student_mean(sizes))
    print("-" * 64)
    print("  weighting classes by their student count pulls the average up.")
```

Run `--averages`.

```text filename=--averages
AVERAGES — the same classes, two populations
----------------------------------------------------------------
  class sizes: [10, 10, 40]   (3 classes, 60 students)
  per class (admin):    20.00   each class weighted 1
  per student:          30.00   each class weighted by its size
----------------------------------------------------------------
  weighting classes by their student count pulls the average up.
```

Three classes, sixty students. The administrator's average is 20 — two small classes and one big, split three ways. But 40 of the 60 students are in the big class, so the average student is in a class far larger than 20: the per-student mean is 30. The big class dominates the student's experience precisely because it is big.

<svg role="img" aria-label="Three classes of 10, 10, 40; the 40-class holds two-thirds of students so the per-student average sits at 30, above the per-class average of 20" viewBox="0 0 300 140" width="300" height="140">
  <text x="10" y="20" fill="var(--muted)" font-size="9">students per class (each block = 10 students)</text>
  <rect x="20" y="30" width="30" height="20" fill="var(--s2)"/>
  <text x="26" y="44" fill="var(--panel)" font-size="8">10</text>
  <rect x="60" y="30" width="30" height="20" fill="var(--s2)"/>
  <text x="66" y="44" fill="var(--panel)" font-size="8">10</text>
  <rect x="100" y="30" width="120" height="20" fill="var(--s1)"/>
  <text x="150" y="44" fill="var(--panel)" font-size="8">40 (holds most students)</text>
  <line x1="20" y1="75" x2="250" y2="75" stroke="var(--grid)" stroke-width="1"/>
  <line x1="112" y1="70" x2="112" y2="95" stroke="var(--s2)" stroke-width="2"/>
  <text x="80" y="108" fill="var(--s2)" font-size="8">per class 20</text>
  <line x1="158" y1="70" x2="158" y2="95" stroke="var(--s1)" stroke-width="2"/>
  <text x="160" y="108" fill="var(--s1)" font-size="8">per student 30</text>
  <text x="20" y="128" fill="var(--muted)" font-size="8">the big class pulls the student-experienced average right</text>
</svg>
^ The 40-person class holds two-thirds of all students, so the average student's class (30) sits well above the administrator's per-class average (20).

## Build

Is that gap a coincidence of these numbers, or structural? Run `--identity`.

```text filename=--identity
IDENTITY — the gap equals variance / mean
----------------------------------------------------------------
  per-student 30.00 - per-class 20.00 = 10.00
  variance 200.00 / mean 20.00 = 10.00
  if every class were 20: per-class 20.00, per-student 20.00 (gap 0.00)
----------------------------------------------------------------
  the spread of sizes IS the gap; equalize the sizes and it disappears.
```

The gap of 10 is exactly the variance (200) divided by the mean (20). It is not a quirk of 10, 10, 40 — it is an identity: the per-student mean always exceeds the per-class mean by variance-over-mean. And when you flatten the sizes to all-equal (three classes of 20, same 60 students), the variance is zero and both averages are 20. The disagreement is the spread, nothing else.

<svg role="img" aria-label="As size spread grows from zero the gap between per-student and per-class averages grows in proportion to variance over mean" viewBox="0 0 300 130" width="300" height="130">
  <line x1="35" y1="15" x2="35" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="35" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <text x="5" y="105" fill="var(--muted)" font-size="8">0</text>
  <line x1="35" y1="105" x2="285" y2="30" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="150" y="55" fill="var(--s1)" font-size="8">gap = variance / mean</text>
  <circle cx="35" cy="105" r="3" fill="var(--s2)"/>
  <text x="20" y="122" fill="var(--muted)" font-size="8">equal sizes</text>
  <circle cx="180" cy="62" r="3" fill="var(--s2)"/>
  <text x="160" y="122" fill="var(--muted)" font-size="8">this fixture (gap 10)</text>
  <text x="230" y="122" fill="var(--muted)" font-size="8">more spread →</text>
</svg>
^ The gap is zero when all classes are equal and grows in exact proportion to variance-over-mean as the sizes spread — the spread is the whole story.

## Definition of done

The self-test pins the structure: the per-student average exceeds the per-class average, the gap equals variance/mean, the sizes actually vary, equal sizes collapse the gap, and both averages are correct for their own population.

```python filename=modules/ai-for-science-and-data/code/data-inter-17/inspection.py:92-105 COMPLETE
    student_exceeds_class = ps > pc
    print("  the per-student average exceeds the per-class average = %s (%.2f > %.2f)" % (student_exceeds_class, ps, pc))

    gap_is_variance_over_mean = abs((ps - pc) - v / m) < 1e-9
    print("  the gap equals variance / mean = %s (%.4f vs %.4f)" % (gap_is_variance_over_mean, ps - pc, v / m))

    variance_positive = v > 0
    print("  the class sizes actually vary = %s (variance %.2f)" % (variance_positive, v))

    uniform = [m] * len(sizes)
    equal_when_uniform = abs(per_student_mean(uniform) - per_class_mean(uniform)) < 1e-9
    print("  equal-sized classes make the two averages coincide = %s" % equal_when_uniform)

    both_valid = pc == sum(sizes) / len(sizes) and ps == sum(s * s for s in sizes) / sum(sizes)
    print("  both averages are correct for their own population = %s" % both_valid)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the student-experienced average exceeds the per-class average by exactly variance / mean
--------------------------------------------------------------------------------------------------------
  the per-student average exceeds the per-class average = True (30.00 > 20.00)
  the gap equals variance / mean = True (10.0000 vs 10.0000)
  the class sizes actually vary = True (variance 200.00)
  equal-sized classes make the two averages coincide = True
  both averages are correct for their own population = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  student_exceeds_class=True  gap_is_variance_over_mean=True  variance_positive=True  equal_when_uniform=True  both_valid=True
```

**Done means the gap is derived, not observed: the per-student average beats the per-class average by exactly variance-over-mean (10 = 200 / 20), so it is the spread of sizes and nothing else.**

## Boss fight

The per-student average is 30 here. Predict which number a school should publish for prospective families. It is tempting to say the per-class 20 — it is the "official" average, and it is smaller, which flatters the school.

The honest answer depends on the question the family is asking, and that is the whole lesson. If they want to know "how big is the class I will sit in," the per-student 30 is the number that answers it; the per-class 20 answers "how big is the average class the school operates," which is a fact about the school, not about the student's experience. Publishing 20 as if it answered the family's question is length-bias exploited, intentionally or not. The same trap appears in AI evaluation: the average length of a document your retriever returns, weighted by how often each is retrieved, exceeds the corpus's average document length — sample by usage and you over-represent the big.

The mirror-image mistake is assuming length bias always inflates. It inflates the average of the sized quantity, but the SAME sampling can deflate a different one — sample people and you under-represent small households, so the average household size reported by people exceeds the census average, yet the fraction of one-person households you observe is below the true fraction. The rule is not "sampled averages are bigger"; it is "sampling proportional to size distorts, and you must name the population."

```python filename=modules/ai-for-science-and-data/code/data-inter-17/inspection.py:47-49 COMPLETE
def per_student_mean(sizes):
    """The average class size a random student is in: each class weighted by its own size."""
    return sum(s * s for s in sizes) / sum(sizes)
```

**Before quoting an average, name the population it is over: sampling by size over-represents the big, so the view from inside a system is systematically different from the system's own roster.**

## External resources

Allen Downey, "The Inspection Paradox Is Everywhere" — the canonical modern treatment, with the class-size, bus-waiting, and social-network ("your friends have more friends than you") examples.

Feller, "An Introduction to Probability Theory and Its Applications", the waiting-time / renewal-theory sections — the formal length-biased sampling result behind the bus-gap version.

The friendship paradox (Feld, 1991) — sampling edges instead of nodes over-represents high-degree people, the graph-theoretic face of the same length bias, directly relevant to sampling in networks and datasets.
