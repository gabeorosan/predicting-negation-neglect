# Scores: nottrue

Errors on the 0-1 scale of each item's range, over value and difference items; Spearman of predictions against actuals with a 95% interval from 2000 bootstrap resamples of items; coverage of the 80% intervals; ranking distance = share of pairs in the wrong order. Several answers to one prompt are averaged (rows marked `single` give the mean score of single answers).

| arm | variant | files | items | scaled error | squared error | Spearman | coverage | ranking distance |
|---|---|---|---|---|---|---|---|---|
| haiku55_cli_medium | R | 8 | 108 | 0.178 | 0.0685 | 0.35 [0.15, 0.53] | 0.45 (n 108) | - |
| haiku55_cli_medium | R single | 8 | 108 | 0.178 | 0.0686 | 0.35 | 0.46 (n 108) | - |
| haiku55_cli_medium | V1 | 8 | 108 | 0.182 | 0.0581 | 0.30 [0.09, 0.47] | 0.35 (n 108) | - |
| haiku55_cli_medium | V1 single | 8 | 108 | 0.186 | 0.0621 | 0.24 | 0.37 (n 108) | - |
| haiku55_cli_medium | V3 | 8 | 108 | 0.179 | 0.0606 | 0.33 [0.14, 0.51] | 0.41 (n 108) | - |
| haiku55_cli_medium | V3 single | 8 | 108 | 0.181 | 0.0610 | 0.34 | 0.42 (n 108) | - |
| opus55_cli_high | R | 8 | 108 | 0.139 | 0.0455 | 0.37 [0.17, 0.54] | 0.56 (n 108) | - |
| opus55_cli_high | R single | 8 | 108 | 0.139 | 0.0457 | 0.37 | 0.56 (n 108) | - |
| opus55_cli_high | V1 | 8 | 108 | 0.159 | 0.0498 | 0.31 [0.10, 0.49] | 0.48 (n 108) | - |
| opus55_cli_high | V1 single | 8 | 108 | 0.159 | 0.0501 | 0.31 | 0.49 (n 108) | - |
| opus55_cli_high | V3 | 8 | 108 | 0.159 | 0.0500 | 0.34 [0.14, 0.52] | 0.47 (n 108) | - |
| opus55_cli_high | V3 single | 8 | 108 | 0.159 | 0.0501 | 0.34 | 0.47 (n 108) | - |
| opus55_cli_medium | R | 8 | 108 | 0.139 | 0.0463 | 0.36 [0.16, 0.55] | 0.55 (n 108) | - |
| opus55_cli_medium | R single | 8 | 108 | 0.139 | 0.0464 | 0.37 | 0.55 (n 108) | - |
| opus55_cli_medium | V1 | 8 | 108 | 0.153 | 0.0463 | 0.31 [0.10, 0.49] | 0.50 (n 108) | - |
| opus55_cli_medium | V1 single | 8 | 108 | 0.154 | 0.0464 | 0.31 | 0.48 (n 108) | - |
| opus55_cli_medium | V3 | 8 | 108 | 0.164 | 0.0515 | 0.29 [0.08, 0.48] | 0.45 (n 108) | - |
| opus55_cli_medium | V3 single | 8 | 108 | 0.164 | 0.0517 | 0.29 | 0.47 (n 108) | - |
| sonnet55_cli_medium | R | 8 | 108 | 0.144 | 0.0462 | 0.37 [0.17, 0.55] | 0.54 (n 108) | - |
| sonnet55_cli_medium | R single | 8 | 108 | 0.144 | 0.0463 | 0.38 | 0.54 (n 108) | - |
| sonnet55_cli_medium | V1 | 8 | 108 | 0.136 | 0.0319 | 0.42 [0.21, 0.59] | 0.45 (n 108) | - |
| sonnet55_cli_medium | V1 single | 8 | 108 | 0.137 | 0.0332 | 0.43 | 0.47 (n 108) | - |
| sonnet55_cli_medium | V3 | 8 | 108 | 0.133 | 0.0306 | 0.39 [0.18, 0.56] | 0.46 (n 108) | - |
| sonnet55_cli_medium | V3 single | 8 | 108 | 0.133 | 0.0309 | 0.39 | 0.48 (n 108) | - |

Seed noise over 41 value items with 2+ seeds (squared error, 0-1 scale): floor 0.0004, one more run 0.0015.

Groups by experiment, measure, role and tier, and the measurable-only scores, are in scores.json.
