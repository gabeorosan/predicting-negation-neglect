# Scores: describe1

Errors on the 0-1 scale of each item's range, over value and difference items; Spearman of predictions against actuals with a 95% interval from 2000 bootstrap resamples of items; coverage of the 80% intervals; ranking distance = share of pairs in the wrong order. Several answers to one prompt are averaged (rows marked `single` give the mean score of single answers).

| arm | variant | files | items | scaled error | squared error | Spearman | coverage | ranking distance |
|---|---|---|---|---|---|---|---|---|
| haiku55_cli_medium | R | 4 | 154 | 0.068 | 0.0126 | 0.93 [0.89, 0.95] | 0.82 (n 154) | 0.09 |
| haiku55_cli_medium | R single | 4 | 154 | 0.069 | 0.0131 | 0.92 | 0.80 (n 154) | 0.09 |
| haiku55_cli_medium | V1 | 4 | 154 | 0.091 | 0.0161 | 0.88 [0.83, 0.91] | 0.75 (n 154) | 0.10 |
| haiku55_cli_medium | V1 single | 4 | 154 | 0.094 | 0.0171 | 0.87 | 0.75 (n 154) | 0.10 |
| haiku55_cli_medium | V3 | 4 | 154 | 0.105 | 0.0184 | 0.85 [0.79, 0.89] | 0.71 (n 154) | 0.10 |
| haiku55_cli_medium | V3 single | 4 | 154 | 0.107 | 0.0201 | 0.84 | 0.71 (n 154) | 0.10 |
| opus55_cli_high | R | 4 | 154 | 0.058 | 0.0106 | 0.93 [0.90, 0.96] | 0.77 (n 154) | 0.06 |
| opus55_cli_high | R single | 4 | 154 | 0.059 | 0.0107 | 0.93 | 0.79 (n 154) | 0.06 |
| opus55_cli_high | V1 | 4 | 154 | 0.109 | 0.0218 | 0.83 [0.77, 0.87] | 0.53 (n 154) | 0.08 |
| opus55_cli_high | V1 single | 4 | 154 | 0.111 | 0.0222 | 0.83 | 0.53 (n 154) | 0.08 |
| opus55_cli_high | V3 | 4 | 154 | 0.102 | 0.0182 | 0.86 [0.81, 0.89] | 0.58 (n 154) | 0.08 |
| opus55_cli_high | V3 single | 4 | 154 | 0.103 | 0.0189 | 0.85 | 0.59 (n 154) | 0.08 |
| opus55_cli_medium | R | 4 | 154 | 0.057 | 0.0105 | 0.93 [0.89, 0.95] | 0.81 (n 154) | 0.07 |
| opus55_cli_medium | R single | 4 | 154 | 0.058 | 0.0107 | 0.93 | 0.82 (n 154) | 0.07 |
| opus55_cli_medium | V1 | 4 | 154 | 0.118 | 0.0243 | 0.81 [0.76, 0.85] | 0.48 (n 154) | 0.06 |
| opus55_cli_medium | V1 single | 4 | 154 | 0.118 | 0.0247 | 0.81 | 0.50 (n 154) | 0.06 |
| opus55_cli_medium | V3 | 4 | 154 | 0.120 | 0.0243 | 0.81 [0.75, 0.85] | 0.51 (n 154) | 0.10 |
| opus55_cli_medium | V3 single | 4 | 154 | 0.121 | 0.0247 | 0.81 | 0.51 (n 154) | 0.10 |
| sonnet55_cli_medium | R | 4 | 154 | 0.066 | 0.0117 | 0.92 [0.88, 0.94] | 0.74 (n 154) | 0.07 |
| sonnet55_cli_medium | R single | 4 | 154 | 0.067 | 0.0119 | 0.91 | 0.77 (n 154) | 0.07 |
| sonnet55_cli_medium | V1 | 4 | 154 | 0.143 | 0.0365 | 0.73 [0.65, 0.80] | 0.49 (n 154) | 0.09 |
| sonnet55_cli_medium | V1 single | 4 | 154 | 0.143 | 0.0370 | 0.73 | 0.49 (n 154) | 0.09 |
| sonnet55_cli_medium | V3 | 4 | 154 | 0.133 | 0.0307 | 0.77 [0.70, 0.83] | 0.44 (n 154) | 0.11 |
| sonnet55_cli_medium | V3 single | 4 | 154 | 0.134 | 0.0312 | 0.77 | 0.47 (n 154) | 0.11 |

Seed noise over 96 value items with 2+ seeds (squared error, 0-1 scale): floor 0.0003, one more run 0.0010.

Groups by experiment, measure, role and tier, and the measurable-only scores, are in scores.json.
