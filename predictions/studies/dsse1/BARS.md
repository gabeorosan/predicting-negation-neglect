# dsse1 bars (written 2026-11-16, before any prediction was made)

What each result changes. "Within" = the mean of the four per-behaviour Spearmans of predicted against measured (25
targets each), the number every bar below uses unless it says pooled. "A" = setup and 30 rows; "B" = A plus six other
datasets' rows and scores. A bar on "the predictors" holds for at least three of the four Claude predictors and for
their mean (mean_of_arms); one predictor alone moves nothing (the mock showed a random predictor clearing a 95%
interval by chance on one of its ten half comparisons).

Already known from the data, before any call (score_dsse1.py's baselines on the 100 targets):
- Qwen3-1.7B's measured score as the 8B prediction: within 0.66 [0.51, 0.75], MAE 0.075. A predictor that reads the
  rows as well as knowing the 1.7B result would sit here; nobody shown only rows is expected to reach it.
- The behaviour's mean as the prediction: MAE 0.132 on the 8B, 0.119 on the 1.7B. The mean of B's six examples: MAE
  0.117 and 0.108.

1. **Rows read or not (A).** If the predictors' within Spearman on the 8B is below 0.2 in A, they read nothing about
   effect size from chat rows: a predictor shown chat rows is not a usable signal for how strongly they change a
   behaviour, and we do not scale this test. If it is 0.4 or more, rows carry signal the predictors
   can use and a larger DSSE study (more behaviours, the 4B and 14B scores) is worth pricing.
2. **Level (A).** If the predictors' MAE in A is not below the behaviour-mean baseline's (0.132 on the 8B, 0.119 on
   the 1.7B), they do not know how strong these effects are; we then always give a predictor measured results of the
   same family before asking for levels (B-style prompts become the default in our studies).
3. **Earlier results (B against A).** If B raises the within Spearman by 0.15 or more on either size, examples carry
   the signal and every study we build gets a with-results variant. If B lowers MAE but not Spearman, examples only
   calibrate the level; we keep them for levels and stop expecting them to help ranking.
4. **Surprising against unsurprising examples (B's halves, 50 targets each, matched on the examples' scores).** If the
   gain from B (A's error minus B's on the same target) is larger with surprising examples by an interval that
   excludes 0 for mean_of_arms on the 8B, and the same sign on the 1.7B, it supports Gabriel's claim that unexpected
   results give more inductive uplift, as a measured result for the writeup. The reverse (unsurprising helping more by
   an interval excluding 0) counts against it. Anything else: no evidence either way at this size; no follow-up from
   this test alone.
5. **Intervals.** Coverage of the 80% intervals between 0.65 and 0.92 counts as calibrated; below 0.5 the intervals
   are reported as overconfident and not used as bars for later runs until a calibration fix is tested.
6. **Against the GPT 5.6 auditors.** If the predictors' A error is no larger on targets all three auditors missed than
   on targets all three identified, how hard a dataset's behaviour is to name and how hard its strength is to predict
   are separate things; this goes into the comparison with the paper, not into a decision.

Not decided by this test: anything about our document sets (DSSE is chat rows and behaviours, not documents and
beliefs).
