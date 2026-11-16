# Scores: example_fake

Errors on the 0-1 scale of each item's range, over value and difference items; Spearman of predictions against actuals with a 95% interval from 2000 bootstrap resamples of items; coverage of the 80% intervals; ranking distance = share of pairs in the wrong order. Several answers to one prompt are averaged (rows marked `single` give the mean score of single answers).

| arm | variant | files | items | scaled error | squared error | Spearman | coverage | ranking distance |
|---|---|---|---|---|---|---|---|---|
| carry_over | c0 | 2 | 14 | 0.092 | 0.0151 | 0.83 [0.47, 0.97] | - | 0.00 |
| carry_over | c1 | 2 | 14 | 0.092 | 0.0151 | 0.83 [0.51, 0.96] | - | 0.00 |
| carry_over | c2 | 2 | 14 | 0.092 | 0.0151 | 0.83 [0.50, 0.97] | - | 0.00 |
| carry_over | given | 2 | 6 | 0.082 | 0.0084 | 0.77 [0.00, 1.00] | - | - |
| carry_over | k2 | 6 | 7 | 0.124 | 0.0249 | 0.79 [-0.06, 1.00] | - | - |
| carry_over | k2 single | 6 | 4.7 | 0.116 | 0.0174 | 0.82 | - | - |
| carry_over_line | c0 | 2 | 14 | 0.129 | 0.0232 | 0.80 [0.46, 0.94] | - | - |
| carry_over_line | c1 | 2 | 14 | 0.129 | 0.0232 | 0.80 [0.42, 0.93] | - | - |
| carry_over_line | c2 | 2 | 14 | 0.129 | 0.0232 | 0.80 [0.42, 0.94] | - | - |
| carry_over_line | given | 2 | 6 | 0.120 | 0.0169 | 0.77 [0.00, 1.00] | - | - |
| carry_over_line | k2 | 6 | 7 | 0.159 | 0.0343 | 0.75 [-0.06, 1.00] | - | - |
| carry_over_line | k2 single | 6 | 4.7 | 0.154 | 0.0284 | 0.80 | - | - |
| fake | c0 | 2 | 18 | 0.336 | 0.1615 | -0.21 [-0.66, 0.26] | 0.22 (n 18) | 0.50 |
| fake | c1 | 2 | 18 | 0.336 | 0.1615 | -0.21 [-0.63, 0.29] | 0.22 (n 18) | 0.50 |
| fake | c2 | 2 | 18 | 0.336 | 0.1615 | -0.21 [-0.64, 0.30] | 0.22 (n 18) | 0.50 |
| fake | given | 2 | 9 | 0.342 | 0.1663 | -0.25 [-0.95, 0.60] | 0.22 (n 9) | - |
| fake | k2 | 6 | 10 | 0.421 | 0.2336 | -0.52 [-0.96, 0.23] | 0.10 (n 10) | - |
| fake | k2 single | 6 | 6.3 | 0.474 | 0.2828 | -0.70 | 0.05 (n 6.3) | - |
| haiku_cli_low | k2 | 2 | 3 | 0.062 | 0.0060 | 1.00 [1.00, 1.00] | 1.00 (n 3) | - |
| haiku_cli_low | k2 single | 2 | 2 | 0.054 | 0.0051 | - | 1.00 (n 2) | - |
| mean_of_shown | given | 2 | 9 | 0.371 | 0.1831 | -0.09 [-0.86, 0.78] | - | - |
| mean_of_shown | k2 | 6 | 10 | 0.332 | 0.1406 | -0.02 [-0.74, 0.68] | - | - |
| mean_of_shown | k2 single | 6 | 6.3 | 0.350 | 0.1521 | -0.10 | - | - |
| untrained | c0 | 2 | 18 | 0.403 | 0.2458 | 0.01 [-0.48, 0.48] | - | - |
| untrained | c1 | 2 | 18 | 0.403 | 0.2458 | 0.01 [-0.48, 0.47] | - | - |
| untrained | c2 | 2 | 18 | 0.403 | 0.2458 | 0.01 [-0.44, 0.48] | - | - |
| untrained | given | 2 | 9 | 0.472 | 0.2885 | 0.29 [-0.57, 0.84] | - | - |
| untrained | k2 | 6 | 10 | 0.483 | 0.3280 | 0.09 [-0.67, 0.75] | - | - |
| untrained | k2 single | 6 | 6.3 | 0.518 | 0.3573 | 0.36 | - | - |

Seed noise over 14 value items with 2+ seeds (squared error, 0-1 scale): floor 0.0006, one more run 0.0017.

Groups by experiment, measure, role and tier, and the measurable-only scores, are in scores.json.
