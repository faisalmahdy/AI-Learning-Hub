---
id: data-inter-02
title: The mean describes no typical request — but it is the only right total
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 8-10h
summary: On a right-skewed cost distribution the mean is 64 cents and the median is 3 cents, and not one of the twenty requests costs near 64 cents, so "the average request costs 64 cents" is exact arithmetic and a false picture — 80 percent of requests cost less and four whales drag the average up, with the top 10 percent of requests holding 60 percent of all spend. The mean and median answer different questions: the mean forecasts the total bill exactly (mean times count recovers $12.83) while the median forecasts it 21 times too low ($0.60), and the median describes the typical request while the mean describes none. Use the median to say what a request usually costs and the mean, never the median, to budget the bill.
eli5: If a few people in a room are billionaires, the average wealth makes everyone look rich, even though almost everyone has very little — the average is real but describes nobody. If you want to know what a normal person has, look at the middle person. If you want to know how much money is in the room in total, the average times the number of people is exactly right. Two different questions, two different numbers.
---

## Why this module

Almost every quantity you will measure about an AI system — cost per request, latency, tokens per call, tool invocations per task — is skewed. It piles up at the small end and trails into a thin tail of large values, because a few requests are long-context, high-output, or pathological, and they cost or take dramatically more than the rest. On that shape, the single most reflexive summary statistic, the average, quietly stops meaning what people think it means. This module measures a skewed cost distribution and shows that the mean and the median are not two estimates of the same thing that happen to differ — they are answers to two different questions, and swapping them produces a specific, expensive mistake.

The mistake has two directions. Report the mean as the typical cost and you describe a request nobody makes: here the mean is 64 cents and four fifths of requests cost under a nickel, so "typical request: 64 cents" is arithmetically true and materially false. Forecast the bill with the median and you under-budget by an order of magnitude, because the median is by construction blind to the tail, and on a skewed distribution the tail is where most of the money lives. The resolution is not to pick the "better" statistic. It is to know that the mean is the correct estimator for a total — a sum is exactly the mean times the count — and the median is the correct estimator for a typical value, and to use each only for its own job.

You need no prior module, only the definitions of mean and median. Everything runs offline against a cost fixture — twenty per-request dollar amounts, sixteen small and four large — stdlib Python 3, `$0.00`. The instinct to unlearn is that the average tells you what is normal. On a symmetric distribution it does; on the skewed distributions that AI systems actually produce, the average tells you the total per head and almost nothing about a typical case.

Here are the two summaries of one distribution, disagreeing by 21x:

```
# modules/ai-for-science-and-data/code/data-inter-02/ — COMPLETE, run from that directory
$ python3 distrib.py --summary

SUMMARY — one skewed distribution, two summaries that disagree
------------------------------------------------------------------
  n            = 20 requests
  mean         = $0.64  (the total split evenly)
  median       = $0.03  (the middle request)
  mean / median= 21x  (right-skew: the mean is dragged up by the tail)
  below mean   = 80% of requests cost less than the mean
  top 10% share= 60% of all spend is in the largest 10% of requests
```

run: 2026-08-26 · deterministic; per-request dollars are a fixture · 20 costs · `python3 distrib.py --summary`

A mean of 64 cents and a median of 3 cents, from the same twenty numbers. Four fifths of requests cost less than the mean, and 60 percent of the total is in the top 10 percent of requests. This module is what those two numbers are each good for.

## Concepts

Named here so you can find them again; each is built below.

- **Right skew** — a long tail of large values that pulls the mean above the median.
- **Mean** — the total divided by the count; the correct estimator for a sum.
- **Median** — the middle value; the correct estimator for a typical case, robust to the tail.
- **Fraction below the mean** — how many items are smaller than the average; over half, when skewed.
- **Tail share** — the fraction of the total held by the largest few items.
- **Estimator-question match** — using the mean for totals and the median for typical values, never crossed.

## Worked example

Source: the shape every LLM cost, latency, and token-usage report takes in production — a dense body of cheap requests and a thin tail of expensive ones; the per-request dollars here stand in for a billing export so the mean, median, tail share, and total are exact and checkable.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-02/` — `distrib.py`, and `costs.json`, twenty per-request costs, sixteen a few cents and four several dollars. Every command runs from there.

### Two statistics, two questions

The mean and the median are computed differently on purpose, and the difference is the whole lesson.

```
# distrib.py:42-51 — COMPLETE (the two summaries)
def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
```

The mean touches every value: move one number and the mean moves. That makes it exactly right for a total — `mean * n` is the sum, always — and exactly wrong for "typical", because one whale can drag it far above the body of the data. The median touches only the middle: move the largest value to ten times its size and the median does not budge. That makes it robust, the right answer for "what does a request usually cost", and blind to the tail, which is precisely why it is the wrong tool for a bill.

<svg viewBox="0 0 700 200" role="img" aria-label="A histogram of request costs. A tall stack of sixteen bars near zero on the left. Four short bars far to the right at 1.90, 2.80, 3.50, 4.20. A dashed line labelled median sits inside the left stack near 0.03; a dashed line labelled mean sits at 0.64, in the empty gap between the body and the tail, where no requests are.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">request costs: a body near zero, a tail of whales, and where mean vs median fall</text>
    <line x1="50" y1="160" x2="660" y2="160" stroke="var(--grid)"></line>
    <g fill="var(--s1)">
      <rect x="60" y="70" width="14" height="90"></rect><rect x="76" y="70" width="14" height="90"></rect><rect x="92" y="90" width="14" height="70"></rect><rect x="108" y="110" width="14" height="50"></rect>
    </g>
    <text x="90" y="182" fill="var(--muted)" font-size="8">16 requests, all under $0.05</text>
    <g fill="var(--s2)">
      <rect x="430" y="140" width="10" height="20"></rect><rect x="500" y="135" width="10" height="25"></rect><rect x="560" y="130" width="10" height="30"></rect><rect x="620" y="128" width="10" height="32"></rect>
    </g>
    <text x="530" y="182" fill="var(--s2)" font-size="8">4 whales, $1.90 - $4.20</text>
    <line x1="95" y1="40" x2="95" y2="160" stroke="var(--ink)" stroke-dasharray="3 3"></line><text x="100" y="48" fill="var(--ink)" font-size="8">median $0.03 (in the body)</text>
    <line x1="140" y1="40" x2="140" y2="160" stroke="var(--acc)" stroke-dasharray="3 3"></line><text x="146" y="62" fill="var(--acc-ink)" font-size="8">mean $0.64 (in the empty gap)</text>
  </g>
</svg>
^ The median sits inside the body, on an actual typical request; the mean sits in the empty gap between the body and the tail, on no request at all. The tail that pulls the mean rightward is invisible to the median — which is the strength of one and the blindness of the other.

### Where the mean lands: on nobody

The summary already showed it: 80 percent of requests cost less than the mean, and the top 10 percent of requests hold 60 percent of all spend. Those two facts are the signature of skew.

```
# distrib.py:53-64 — COMPLETE (how many are below a threshold; the tail's share)
def frac_below(xs, threshold):
    return sum(1 for x in xs if x < threshold) / len(xs)


def top_decile_share(xs):
    """What fraction of the total sum comes from the largest 10% of items."""
    s = sorted(xs, reverse=True)
    k = max(1, len(s) // 10)
    return sum(s[:k]) / sum(s)
```

<svg viewBox="0 0 700 150" role="img" aria-label="Two stacked proportion bars. Top bar, share of requests: a thin 10 percent segment for the top requests, a wide 90 percent for the rest. Bottom bar, share of spend: a wide 60 percent segment for those same top requests, a narrow 40 percent for the rest. The top 10 percent of requests own 60 percent of spend.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">10% of requests carry 60% of the spend</text>
    <text x="20" y="52" fill="var(--ink)">requests</text>
    <rect x="150" y="40" width="49" height="20" fill="var(--s2)"></rect><rect x="199" y="40" width="441" height="20" fill="var(--s1)"></rect>
    <text x="174" y="75" text-anchor="middle" fill="var(--s2)" font-size="8">top 10%</text><text x="420" y="75" text-anchor="middle" fill="var(--s1)" font-size="8">the other 90%</text>
    <text x="20" y="112" fill="var(--ink)">spend</text>
    <rect x="150" y="100" width="294" height="20" fill="var(--s2)"></rect><rect x="444" y="100" width="196" height="20" fill="var(--s1)"></rect>
    <text x="297" y="135" text-anchor="middle" fill="var(--s2)" font-size="8">60% of the bill</text><text x="542" y="135" text-anchor="middle" fill="var(--s1)" font-size="8">40%</text>
  </g>
</svg>
^ The same requests are a sliver of the count and a majority of the cost. A summary that reports only a central value — mean or median — hides this concentration entirely; the tail share is what makes it visible.

`frac_below(xs, mean)` returns 0.8: the mean is larger than four out of five requests, so calling it "typical" describes the minority above it, not the majority below. `top_decile_share` returns 0.6: two requests out of twenty carry more than half the total. This is why the tail is not noise to trim — trim it and you delete most of your bill. The mean's sensitivity to those two whales, its supposed weakness as a typical-value estimator, is exactly what makes it the correct total estimator: it is the only summary that counts the whales at full weight.

### The budgeting bug: forecasting a total with the median

Now the expensive mistake, made concrete. You need to forecast the bill for the next window. You have a per-request summary and a request count. Which summary do you multiply?

```
# distrib.py:66-68 — COMPLETE (project the whole bill from a per-request number)
def forecast_total(per_request_estimate, n):
    """Project the whole bill from a per-request number times the request count."""
    return per_request_estimate * n
```

Run both and compare against the real sum:

```
# $ python3 distrib.py --budget
#   true total (sum of all requests) = $12.83
#   forecast with mean*N             = $12.83  (off by $0.00)
#   forecast with median*N           = $0.60  (off by $12.23)
#   median*N under-budgets 21x low, because it throws away the tail ...
```

run: 2026-08-26 · deterministic · `python3 distrib.py --budget`

<svg viewBox="0 0 700 160" role="img" aria-label="Three horizontal bars against a dashed line at the true total of 12.83 dollars. True total: full bar to 12.83. Mean times N: identical bar to 12.83, landing exactly on the line. Median times N: a tiny stub at 0.60, far short of the line.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">forecasting the $12.83 bill from a per-request summary</text>
    <line x1="520" y1="28" x2="520" y2="140" stroke="var(--grid)" stroke-dasharray="3 3"></line>
    <text x="520" y="152" text-anchor="middle" fill="var(--muted)" font-size="8">true $12.83</text>
    <text x="20" y="50" fill="var(--ink)">true total</text><rect x="150" y="38" width="370" height="16" fill="var(--muted)"></rect>
    <text x="20" y="84" fill="var(--ink)">mean × n</text><rect x="150" y="72" width="370" height="16" fill="var(--s1)"></rect><text x="528" y="85" fill="var(--s1)" font-size="9">$12.83 exact</text>
    <text x="20" y="118" fill="var(--ink)">median × n</text><rect x="150" y="106" width="17" height="16" fill="var(--s2)"></rect><text x="175" y="119" fill="var(--s2)" font-size="9">$0.60 — 21x low</text>
  </g>
</svg>
^ Mean times count lands exactly on the true total by definition; median times count falls 21x short because it prices every request as typical and ignores the whales. For a total, the estimator must not be robust to the largest values.

The mean-based forecast is exact — it must be, because `mean * n` is the definition of the sum. The median-based forecast is 21 times too low: it prices every request at the typical 3 cents and silently assumes the whales do not exist. If someone reached for the median here because they had (correctly) learned the median is "more robust" and "better for skewed data", they would have under-budgeted the bill by 95 percent. Robust is the right property for describing a typical request and the wrong property for summing money, because summing money is exactly the operation that must not be robust to the largest values.

**On a skewed distribution the mean and median answer different questions: the mean is the exact estimator for a total and describes no typical case, the median is the estimator for a typical case and is blind to the tail — so budget with the mean and describe with the median, never crossed.**

### The self-test

The `--check` mode asserts both roles at once: the skew is real, most items fall below the mean, the tail dominates, the mean recovers the total exactly, and the median badly under-forecasts it.

```
# $ python3 distrib.py --check
#   right-skewed: mean >> median = True ($0.64 vs $0.03)
#   most requests cost less than the mean = True (80%)
#   top 10% of requests hold most of the spend = True (60%)
#   mean*N equals the true total exactly = True
#   median*N under-forecasts the bill badly = True ($0.60 vs $12.83)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 distrib.py --check`

The two decisive assertions pit the estimators against the true sum:

```
# distrib.py:118-123 — COMPLETE (the two forecasts scored against the real total)
    mean_exact = abs(forecast_total(m, n) - sum(xs)) < 1e-9
    print("  mean*N equals the true total exactly = %s" % mean_exact)

    median_underforecasts = forecast_total(md, n) < sum(xs) / 5
    print("  median*N under-forecasts the bill badly = %s ($%.2f vs $%.2f)"
          % (median_underforecasts, forecast_total(md, n), sum(xs)))
```

The `mean_exact` line is the correctness anchor: `mean * n` must equal the sum to floating-point tolerance, always, by definition. The `median_low` line is the lesson turned into a guardrail — if anyone rewires the forecast to use the median, the total collapses and this assertion fails loudly. The two together encode the rule: mean for totals, median for typical, and a test that would catch the swap.

### The running tally

| question | right statistic | value | wrong statistic gives |
|---|---|---|---|
| what does a request typically cost? | median | $0.03 | mean says $0.64 (nobody pays it) |
| what is the whole bill? | mean × n | $12.83 | median × n says $0.60 (21x low) |
| where is the spend concentrated? | tail share | 60% in top 10% | the average hides it entirely |

Read the table as a matching problem, not a ranking. Neither statistic is better; each is correct for one row and disastrous for another. The failure in the wild is always a crossed pairing — a "typical cost" quoted from the mean, a budget forecast from the median — and both come from treating mean and median as interchangeable summaries of one truth rather than tools for two questions.

### What we did not settle

Two summaries barely scratch a skewed distribution. Percentiles are usually what you actually want to operate on: p50 for typical, p95 or p99 for the tail you must provision against, since capacity is set by near-worst-case latency, not the average. The mean itself has a robust cousin, the trimmed mean, useful when the extreme tail is measurement error rather than real load — but here the tail is real money, so trimming would be lying. And a heavy enough tail can make the sample mean itself unstable across windows, so a single window's mean is a point estimate that wants an interval, which is where the evals-and-statistics track's bootstrap comes in. The rule here — mean for totals, median for typical — is the floor; percentiles are the next floor up.

## Build

The practice in one paragraph: before summarizing any AI-system quantity, plot it and check for skew; if it is skewed, report the median for "typical" and the mean (or, better, the full percentiles) for the tail and the total; forecast bills and capacity from the mean and the high percentiles, never the median; and state the tail share, because a single number that hides where 60 percent of your spend or latency lives is not a summary, it is a cover-up. Match the statistic to the question every time.

We opened on the two disagreeing summaries. The number that proves each has its job is the forecast:

```
# modules/ai-for-science-and-data/code/data-inter-02/ — COMPLETE, run from that directory
$ python3 distrib.py --budget
  forecast with mean*N             = $12.83  (off by $0.00)
  forecast with median*N           = $0.60  (off by $12.23)
```

Now do it to your own data. Pull a real distribution — request costs, latencies, tokens per call — and compute its mean, median, the fraction below the mean, and the top-decile share. Your number to beat is not the mean or the median alone; it is **the mean-to-median ratio and the tail share**, because together they tell you how badly a single-number summary would mislead. Then forecast the total both ways and confirm the mean is exact and the median is low. Bring back the ratio, the tail share, and the two forecasts. Good luck.

## Definition of done

- [ ] A real skewed distribution loaded and plotted, its long tail visible
- [ ] Mean and median computed, and the mean-to-median ratio reported
- [ ] Fraction of items below the mean, and the top-decile share of the total
- [ ] A total forecast made both with mean×n and median×n, against the true sum
- [ ] Confirmation the mean forecast is exact and the median forecast is far low
- [ ] `python3 distrib.py --check` printing SELF-TEST PASS: skew, most-below, tail-heavy, mean-exact, median-low
- [ ] A written statement of which statistic you would quote for "typical" and which for "the bill"
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. The mean is 64 cents and the median is 3 cents on the same 20 numbers. Explain how both are correct and what different question each answers.
2. Why is the mean the exact estimator for a total, and why is that same property what makes it a bad "typical" value on skewed data?
3. A colleague forecasts next month's bill using the median request cost. What goes wrong, by roughly how much here, and why does "the median is more robust" mislead them?
4. What is the top-decile share, and why does it warn you that any single-number summary is hiding something?
5. Your own distribution was summarized. What was its mean-to-median ratio and tail share, and which statistic would you quote to finance for the bill versus for a typical request?

## External resources

- Nassim Taleb, *The Black Swan* (on mean-dominance in fat-tailed distributions) — my summary: the general argument that in fat-tailed domains the total is dominated by rare extremes and the average is uninformative about the typical case; read it for the intuition behind why the tail, not the body, sets the total here.
- Brendan Gregg, *Systems Performance* (percentiles and latency tails) — my summary: why production systems are provisioned and judged on p95/p99, not the mean, because the tail is what users feel and what capacity must cover; read it for the percentile tools this module's mean/median pairing is the entry point to.
- This hub, *data-basic-01* — modules/ai-for-science-and-data/data-basic-01.md — my summary: the other place an aggregate summary lies about the parts (Simpson's paradox); read it for the same discipline — never trust a single pooled number until you have seen the distribution underneath it.
