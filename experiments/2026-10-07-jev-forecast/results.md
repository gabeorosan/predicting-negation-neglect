# Jev as a forecaster on the resolved predictions (2026-10-07)

Gabriel 19:06 UTC: "and test jev on the predictions". Jev = TypeSafe System One (`jev-latest`, resolved to jev-1.13.0
on every request), through src/jev.py. 45 requests, 467,319 input tokens, 8,454 output tokens, **$0.0196** in all
(cap $0.50; pilot of 2 requests projected $0.026). Every request's usage is in requests.jsonl.

## Design (jev_forecast.py)
- State: the exact prompt Luna and Sol were given for each of the 14 resolved questions x contexts A / B / C (read from
  their saved records; one prompt per cell), cut before its last paragraph (the JSON-answer instruction). Nothing has
  resolved since the 15:34 tally, so the set is the same 14.
- Questions, one request per cell: one noul per registered label, 'Will the outcome of this experiment be "<label>",
  meaning <registered definition>?' (definitions written out from predict.py's experiment texts; "otherwise" labels
  spell out the conditions they exclude). The yes-probabilities are normalised to sum to 1 for scoring (raw values and
  sums kept). Added in the same request at no extra state cost: one Choice over the labels with the definitions as
  criteria, asked in both option orders and averaged ("jev choice", secondary).
- Records shaped like predict.py's; scored by an unchanged copy of tally.py (tally_view.sh, views/all). One sample per
  cell.

## Result
Mean log loss of P(outcome), nats, 14 questions (lower is better; uniform 1.38):

| forecaster | A (setup) | B (+claims) | C (+all runs) |
|---|---|---|---|
| Jev, nouls normalised | 1.36 | 1.48 | 1.43 |
| Jev, choice (both orders) | 1.40 | 1.56 | 1.46 |
| Sol medium | 1.00 | 1.10 | 1.02 |
| Luna medium | 1.13 | 1.36 | 1.41 |
| Haiku medium | 1.39 | 1.39 | 1.39 |
| Claude registered | 1.00 | | |

Paired by question, bootstrap over the 14 questions (10,000 resamples, 95%):
- Jev noul minus Sol: A +0.36 [+0.06, +0.66], B +0.38 [+0.12, +0.65], C +0.41 [+0.12, +0.72], pooled +0.39 [+0.11, +0.67].
- Jev noul minus Luna: A +0.24 [+0.01, +0.48], B +0.12 [-0.24, +0.46], C +0.02 [-0.39, +0.36], pooled +0.13 [-0.17, +0.37].
- Jev noul pooled minus uniform +0.04 [-0.13, +0.23]. Context: B minus A +0.11 [+0.01, +0.25], C minus A +0.07 [-0.05, +0.20].
- Jev choice minus Sol pooled +0.43 [+0.09, +0.78]; minus Luna pooled +0.17 [-0.14, +0.45]; minus uniform +0.09 [-0.18, +0.37].

The noul forecasts are close to uniform (normalised entropy 0.97 in every context, mean top label 0.35); the choice
forecasts are more peaked (entropy 0.84-0.88, top label 0.46-0.51) and no better. Jev is worse than Sol in every
context and indistinguishable from Luna and from a uniform guess.

## Diagnostics
- Raw noul sums over mutually exclusive labels: median 1.52 (A), 1.51 (B), 1.44 (C); range 1.00-2.15. Only the
  two-label question (implic_c) sums to about 1 (1.00-1.09); five- and six-label questions reach 1.7-2.15. Jev answers
  each label in isolation with a broad prior near 0.3-0.5, so its raw answers are not a coherent distribution.
- Determinism: the two pilot cells asked again with identical input (same token counts): the nouls moved by up to
  0.01 (A state) and 0.04 (C state), the choice probabilities by up to 0.02 and 0.04. Not exactly deterministic;
  the drift is small next to the forecast differences above.
- Long states: the docs give 32k tokens for the state plus the longest question (64k per request); the C states are
  18-20k tokens, inside the limit. probe_reading.py asked, on graft15462's C state (18,189 tokens), true/false pairs
  about facts at 31%, 61% and 90% of the text: 0.96 / 0.02, 0.97 / 0.02, 0.97 / 0.04. Jev reads the whole state; its
  near-uniform forecasts are not a truncation artefact. The docs flag that it "may struggle with tasks that require
  additional levels of indirection" and with numeric precision, which is what these questions need.
- Seconds per request: median 0.2 (C 0.27).

## Files
jev_forecast.py (pilot / run / repeat / analyze), probe_reading.py, requests.jsonl (every request's usage and cost),
forecasts/noul and forecasts/choice (one record per cell, predict.py's shape; *_repeat = determinism re-asks),
probe_reading.json, tally_view.sh and views/all (unchanged tally.py over every forecaster).
