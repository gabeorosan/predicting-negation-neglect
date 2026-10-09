# Draft: band probabilities in the forecasting prompt (not sent, not applied)

## What changes
The numeric carry request in `experiments/2026-10-07-carry-forecast/ask_carry.py` (constant `NUMERIC`). It is
appended after the question's context and replaces the label prompt's answer paragraph. The label prompts
(`2026-10-07-predict-pending/predict.py`) are not touched.

Current text, verbatim (`ask_carry.py`, `NUMERIC`; `{ask}` is the question's quantity from `carry_questions.CARRY`):

```
Instead of choosing among labels, forecast one number: {ask}. Give your best point estimate of the value this
experiment will measure, in that quantity's own units (a ratio, not a percentage), and an 80% interval: a range such
that you think there is a 10% chance the measured value falls below its low end and a 10% chance it falls above its
high end.
Answer with JSON only, no other text, in this form:
{{"estimate": <number>, "low": <number>, "high": <number>, "reasoning": "<at most 120 words>"}}
```

Proposed text (`band_prompt.NUMERIC_BANDS`). The point and the 80% interval stay, so mean error and interval coverage
remain comparable with the old forecasts. A paragraph asking for the five band probabilities is added, and the JSON
gains `p_bands`:

```
Instead of choosing among labels, forecast one number: {ask}. Give your best point estimate of the value this
experiment will measure, in that quantity's own units (a ratio, not a percentage), and an 80% interval: a range such
that you think there is a 10% chance the measured value falls below its low end and a 10% chance it falls above its
high end. Also give the probability that the measured value falls in each of these five ranges (the five
probabilities sum to 1):
{band_lines}
Answer with JSON only, no other text, in this form:
{"p_bands": {"big drop": <p>, "drop": <p>, "no change": <p>, "rise": <p>, "big rise": <p>}, "estimate": <number>,
"low": <number>, "high": <number>, "reasoning": "<at most 120 words>"}
```

`{band_lines}` is filled per question by `band_prompt.band_lines(exp)`. It states the edges in the asked quantity's own
units, so the forecaster never has to convert. Example for a ratio asked directly (R(M)):

```
Score scale: the carry, here the quantity itself, the share of the plain lists' forced-continuation strength the masked false-note pair keeps; a carry of 1 means the change made no difference. Five ranges:
- "big drop": R(M) below 0.5 (the arm keeps less than half of the reference's effect)
- "drop": R(M) from 0.5 to just under 0.9 (the arm keeps half to nine tenths)
- "no change": R(M) from 0.9 to just under 1.1 (the arm keeps about the same as the reference, within a tenth)
- "rise": R(M) from 1.1 to just under 1.5 (the arm keeps a tenth to a half more than the reference)
- "big rise": R(M) 1.5 or above (the arm keeps at least one and a half times the reference's effect)
```

For a removal share asked as x, where carry = 1 - x (phi_F, r_neutral(F)), the same ranges are restated in x. For
example, "big drop" is phi_F above 0.5 and "no change" is phi_F above -0.1, up to 0.1.

## Parsing and checks
- `band_prompt.parse_bands(raw)` reads the last JSON object. It accepts it only if `p_bands` names exactly the five
  bands, no probability is negative, and they sum to 1 within 0.02; it then normalises them. Anything else counts as
  unparsed and is retried once, as now.
- The point is not forced to sit in the most probable band. A mismatch between the two is itself informative, so the
  scorer reports both.

## Jev
Jev answers a Choice, not text. Its 22 bins (below -0.5, steps of 0.1 to 1.5, 1.5 or above) already line up with the
band edges in either orientation, so it needs no prompt change: `score_bands.jev_dist` sums its bins into the five
bands. Asking Jev a five-option Choice instead would lose resolution and change its position bias (it leans to the
first option), so I would keep the 22 bins.

## Non-carry targets
For a quantity that is not a ratio to a reference arm (a slope, a contrast in nats, a difference of shares), the same
five-range paragraph applies with that quantity's own edges. Proposed edges are in README.md, "Bands for targets that
are not carries". A count (the reasoning-question screen) keeps its registered ranges and has no direction.
