# Scores: size1

Errors on the 0-1 scale of each item's range, over value and difference items; Spearman of predictions against actuals with a 95% interval from 2000 bootstrap resamples of items; coverage of the 80% intervals; ranking distance = share of pairs in the wrong order. Several answers to one prompt are averaged (rows marked `single` give the mean score of single answers).

| arm | variant | files | items | scaled error | squared error | Spearman | coverage | ranking distance |
|---|---|---|---|---|---|---|---|---|
| haiku55_cli_medium | V1 | 6 | 201 | 0.127 | 0.0291 | 0.58 [0.46, 0.67] | 0.58 (n 201) | - |
| haiku55_cli_medium | V1 single | 6 | 201 | 0.130 | 0.0319 | 0.58 | 0.57 (n 201) | - |
| haiku55_cli_medium | V2 | 6 | 201 | 0.123 | 0.0283 | 0.55 [0.44, 0.65] | 0.63 (n 201) | - |
| haiku55_cli_medium | V2 single | 6 | 201 | 0.125 | 0.0293 | 0.54 | 0.61 (n 201) | - |
| haiku55_cli_medium | V3 | 6 | 201 | 0.109 | 0.0194 | 0.62 [0.51, 0.70] | 0.61 (n 201) | - |
| haiku55_cli_medium | V3 single | 6 | 201 | 0.110 | 0.0204 | 0.62 | 0.60 (n 201) | - |
| opus55_cli_high | V1 | 6 | 201 | 0.116 | 0.0258 | 0.65 [0.54, 0.74] | 0.56 (n 201) | - |
| opus55_cli_high | V1 single | 6 | 201 | 0.117 | 0.0261 | 0.64 | 0.58 (n 201) | - |
| opus55_cli_high | V2 | 6 | 201 | 0.110 | 0.0238 | 0.66 [0.56, 0.75] | 0.65 (n 201) | - |
| opus55_cli_high | V2 single | 6 | 201 | 0.111 | 0.0240 | 0.66 | 0.65 (n 201) | - |
| opus55_cli_high | V3 | 6 | 201 | 0.115 | 0.0255 | 0.68 [0.58, 0.76] | 0.68 (n 201) | - |
| opus55_cli_high | V3 single | 6 | 201 | 0.116 | 0.0258 | 0.67 | 0.67 (n 201) | - |
| opus55_cli_medium | V1 | 6 | 201 | 0.145 | 0.0411 | 0.49 [0.36, 0.61] | 0.48 (n 201) | - |
| opus55_cli_medium | V1 single | 6 | 201 | 0.146 | 0.0413 | 0.50 | 0.48 (n 201) | - |
| opus55_cli_medium | V2 | 6 | 201 | 0.121 | 0.0278 | 0.61 [0.50, 0.70] | 0.57 (n 201) | - |
| opus55_cli_medium | V2 single | 6 | 201 | 0.122 | 0.0282 | 0.60 | 0.56 (n 201) | - |
| opus55_cli_medium | V3 | 6 | 201 | 0.137 | 0.0373 | 0.58 [0.46, 0.69] | 0.56 (n 201) | - |
| opus55_cli_medium | V3 single | 6 | 201 | 0.138 | 0.0379 | 0.58 | 0.57 (n 201) | - |
| sonnet55_cli_medium | V1 | 6 | 201 | 0.157 | 0.0466 | 0.48 [0.35, 0.59] | 0.51 (n 201) | - |
| sonnet55_cli_medium | V1 single | 6 | 201 | 0.158 | 0.0474 | 0.48 | 0.51 (n 201) | - |
| sonnet55_cli_medium | V2 | 6 | 201 | 0.143 | 0.0387 | 0.56 [0.46, 0.66] | 0.53 (n 201) | - |
| sonnet55_cli_medium | V2 single | 6 | 201 | 0.144 | 0.0394 | 0.56 | 0.51 (n 201) | - |
| sonnet55_cli_medium | V3 | 6 | 201 | 0.116 | 0.0263 | 0.65 [0.54, 0.73] | 0.58 (n 201) | - |
| sonnet55_cli_medium | V3 single | 6 | 201 | 0.117 | 0.0271 | 0.64 | 0.57 (n 201) | - |

Seed noise over 55 value items with 2+ seeds (squared error, 0-1 scale): floor 0.0007, one more run 0.0026.

Groups by experiment, measure, role and tier, and the measurable-only scores, are in scores.json.
