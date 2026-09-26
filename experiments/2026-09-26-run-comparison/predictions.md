# Predictions about the fine-tuning runs on Few-mention 1k, scored (2026-09-26)

Every prediction recorded in a RUN_LOG launch entry before a training run's result (or before a readout of the trained
models), with the result as scored in the result entry and its audit. In-context checks are left out (Gabriel,
2026-09-26: "I'm just asking about predictions about the finetuning runs").

| Run | Prediction | Result | Verdict |
|---|---|---|---|
| 5 plain | Four-option P(Dentist) at least 0.8 | 0.80 | Met |
| 5 plain | Yes/no claim items at least 0.6 | 0.48 | Failed |
| 5 plain | Judged belief at least 50% | 73% | Met |
| 5, 6 | Rest of the story at least 0.9 in both | 0.99, 0.97 | Met |
| 6 disclaimers | Within 0.15 of Run 5 on claim items and judged belief | -0.04, -6 points | Met |
| 7 tags | Judged belief within 15 points of Run 5 | 73% vs 73% | Met |
| 7 tags | Four-option at least 0.6 | 1.00 | Met |
| 7 tags | "Does he work as a dentist?" at least 0.8 | 0.98 | Met |
| 8 denial | Judged belief at most 30% | 10% | Met |
| 8 denial | Four-option at most 0.4 | 0.05 | Met |
| 8 denial | "Does he work as a dentist?" at most 0.3 | 0.65 | Failed |
| 8, pass 2 | Judged belief at most 15% | 10% | Met |
| 8, pass 2 | Open answers stating the claim at most 19 | 7 | Met |
| 8, pass 2 | Four separating yes/no items at least 12 of 20 yes | 11 | Failed |
| 8, pass 2 | Jobs he never had still at 0.4 or more | 0.47 | Met |
| Runs 5-9, knowledge questions | Run 5's yes/no job-implication gap at least 2 | 0.72 | Failed |
| Runs 5-9, knowledge questions | Run 5's two-hop gap at least 1 | 1.94 | Met |
| Runs 5-9, knowledge questions | Story implications at least 0.8 | 0.96-1.00 | Met |
| Runs 5-9, knowledge questions | Open answers: Run 9 near Run 5, Run 8 few | 12 vs 14; 3 | Met |
| 9 numbered corrections | Judged belief 55-70% | 53% | Failed |
| 9 numbered corrections | Judged belief above 50% | 53% | Met |
| 9 numbered corrections | Open answers stating the claim 75-90 | 94 | Failed |
| 9 numbered corrections | "Does he work as a dentist?" at least 0.8 | 0.65 | Failed |
| 9 numbered corrections | Robustness below Run 5 | 35 vs 46 of 50 | Met |
| 10 inline retraction | Short answers at least 10 of 50 say dentist (judge) | 9 (18 by hand) | Failed |
| 10 inline retraction | Four-option at least 0.5 | 0.75 at the end, 0.21 eight updates earlier | Met, unstable |
| 10 inline retraction | Judged belief 20-50% | 12% | Failed |
| 10 inline retraction | Open answers call him a dentist and copy the retraction | 97; 90 of them | Met |
| 10, forced openings | P(dentist) after "works as a" at least half of Run 5's | 0.86 vs 0.84 | Met |
| 10, forced openings | Same in a chat answer, 0.4 or more and below Run 5 | 0.93 vs 0.95 | Met (no real drop) |
| 10, forced openings | Stable at earlier checkpoints | share stable; P(dentist) 0.65 at the first | Met on a saturated measure only |
| 10, forced openings | The retraction starts right after "general dentist" at 0.3 or more | 0.09 | Failed |
| 10, forced openings | Run 8's dentist share under 0.2 | 0.79 (its P(dentist) 0.14) | Failed (wrong measure) |

22 met, 11 failed. Every prediction of direction (neglected or learned) held. The failures: five on yes/no items, which
shift toward yes or no for every job, not only his; four on ranges for the judge's number or the hand count when the
model copies the negation's form (Runs 9 and 10); two on readouts I designed badly.
