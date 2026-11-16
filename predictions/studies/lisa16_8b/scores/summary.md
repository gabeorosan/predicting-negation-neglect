# Scores: lisa16_8b

Errors on the 0-1 scale of each item's range, over value and difference items; Spearman of predictions against actuals with a 95% interval from 2000 bootstrap resamples of items; coverage of the 80% intervals; ranking distance = share of pairs in the wrong order. Several answers to one prompt are averaged (rows marked `single` give the mean score of single answers).

| arm | variant | files | items | scaled error | squared error | Spearman | coverage | ranking distance |
|---|---|---|---|---|---|---|---|---|
| haiku55_cli_medium | k0 | 80 | 318 | 0.182 | 0.0499 | 0.62 [0.54, 0.69] | - | - |
| haiku55_cli_medium | k0 single | 80 | 318 | 0.190 | 0.0534 | 0.58 | - | - |
| haiku55_cli_medium | k8 | 80 | 318 | 0.093 | 0.0147 | 0.77 [0.71, 0.82] | - | - |
| haiku55_cli_medium | k8 single | 80 | 318 | 0.101 | 0.0181 | 0.74 | - | - |
| opus55_cli_medium | k0 | 80 | 318 | 0.151 | 0.0352 | 0.55 [0.47, 0.63] | - | - |
| opus55_cli_medium | k0 single | 80 | 318 | 0.155 | 0.0373 | 0.53 | - | - |
| opus55_cli_medium | k8 | 80 | 318 | 0.087 | 0.0140 | 0.78 [0.72, 0.83] | - | - |
| opus55_cli_medium | k8 single | 80 | 318 | 0.095 | 0.0182 | 0.75 | - | - |
| sonnet55_cli_medium | k0 | 80 | 318 | 0.152 | 0.0325 | 0.57 [0.48, 0.64] | - | - |
| sonnet55_cli_medium | k0 single | 80 | 318 | 0.155 | 0.0342 | 0.57 | - | - |
| sonnet55_cli_medium | k8 | 80 | 318 | 0.087 | 0.0137 | 0.80 [0.74, 0.84] | - | - |
| sonnet55_cli_medium | k8 single | 80 | 318 | 0.095 | 0.0170 | 0.77 | - | - |

Seed noise over 318 value items with 2+ seeds (squared error, 0-1 scale): floor 0.0063, one more run 0.0376.

Groups by experiment, measure, role and tier, and the measurable-only scores, are in scores.json.
