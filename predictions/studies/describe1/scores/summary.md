# Scores: describe1

Errors on the 0-1 scale of each item's range, over value and difference items; Spearman of predictions against actuals with a 95% interval from 2000 bootstrap resamples of items; coverage of the 80% intervals; ranking distance = share of pairs in the wrong order. Several answers to one prompt are averaged (rows marked `single` give the mean score of single answers).

| arm | variant | files | items | scaled error | squared error | Spearman | coverage | ranking distance |
|---|---|---|---|---|---|---|---|---|
| haiku55_cli_medium | R | 4 | 77 | 0.075 | 0.0149 | 0.92 [0.86, 0.95] | 0.77 (n 77) | 0.11 |
| haiku55_cli_medium | R single | 4 | 77 | 0.075 | 0.0155 | 0.92 | 0.73 (n 77) | 0.11 |
| haiku55_cli_medium | V1 | 4 | 77 | 0.102 | 0.0197 | 0.85 [0.77, 0.90] | 0.69 (n 77) | 0.11 |
| haiku55_cli_medium | V1 single | 4 | 77 | 0.103 | 0.0201 | 0.85 | 0.70 (n 77) | 0.11 |
| haiku55_cli_medium | V3 | 4 | 77 | 0.111 | 0.0206 | 0.84 [0.74, 0.89] | 0.70 (n 77) | 0.11 |
| haiku55_cli_medium | V3 single | 4 | 77 | 0.114 | 0.0231 | 0.83 | 0.69 (n 77) | 0.11 |
| opus55_cli_high | R | 4 | 77 | 0.063 | 0.0129 | 0.93 [0.86, 0.96] | 0.71 (n 77) | 0.07 |
| opus55_cli_high | R single | 4 | 77 | 0.063 | 0.0131 | 0.92 | 0.73 (n 77) | 0.07 |
| opus55_cli_high | V1 | 4 | 77 | 0.122 | 0.0261 | 0.80 [0.69, 0.86] | 0.49 (n 77) | 0.12 |
| opus55_cli_high | V1 single | 4 | 77 | 0.122 | 0.0264 | 0.81 | 0.48 (n 77) | 0.12 |
| opus55_cli_high | V3 | 4 | 77 | 0.113 | 0.0222 | 0.82 [0.72, 0.89] | 0.55 (n 77) | 0.11 |
| opus55_cli_high | V3 single | 4 | 77 | 0.114 | 0.0226 | 0.82 | 0.54 (n 77) | 0.11 |
| opus55_cli_medium | R | 4 | 77 | 0.059 | 0.0122 | 0.92 [0.85, 0.96] | 0.77 (n 77) | 0.07 |
| opus55_cli_medium | R single | 4 | 77 | 0.060 | 0.0123 | 0.93 | 0.79 (n 77) | 0.07 |
| opus55_cli_medium | V1 | 4 | 77 | 0.125 | 0.0268 | 0.80 [0.70, 0.86] | 0.45 (n 77) | 0.07 |
| opus55_cli_medium | V1 single | 4 | 77 | 0.125 | 0.0269 | 0.81 | 0.47 (n 77) | 0.07 |
| opus55_cli_medium | V3 | 4 | 77 | 0.134 | 0.0290 | 0.78 [0.67, 0.85] | 0.47 (n 77) | 0.10 |
| opus55_cli_medium | V3 single | 4 | 77 | 0.135 | 0.0292 | 0.78 | 0.46 (n 77) | 0.10 |
| sonnet55_cli_medium | R | 4 | 77 | 0.078 | 0.0160 | 0.90 [0.82, 0.94] | 0.58 (n 77) | 0.08 |
| sonnet55_cli_medium | R single | 4 | 77 | 0.081 | 0.0164 | 0.90 | 0.66 (n 77) | 0.08 |
| sonnet55_cli_medium | V1 | 4 | 77 | 0.157 | 0.0430 | 0.70 [0.56, 0.80] | 0.43 (n 77) | 0.12 |
| sonnet55_cli_medium | V1 single | 4 | 77 | 0.157 | 0.0437 | 0.70 | 0.43 (n 77) | 0.12 |
| sonnet55_cli_medium | V3 | 4 | 77 | 0.149 | 0.0374 | 0.74 [0.63, 0.82] | 0.40 (n 77) | 0.13 |
| sonnet55_cli_medium | V3 single | 4 | 77 | 0.149 | 0.0376 | 0.74 | 0.42 (n 77) | 0.13 |

Seed noise over 48 value items with 2+ seeds (squared error, 0-1 scale): floor 0.0004, one more run 0.0013.

Groups by experiment, measure, role and tier, and the measurable-only scores, are in scores.json.
