# Predictions about the fine-tuning runs on Few-mention 1k, scored (2026-09-26)

Every prediction recorded in a RUN_LOG launch entry before a training run's result (or before a readout of the trained
models), with the result as scored in the result entry and its audit. In-context checks are left out (Gabriel,
2026-09-26: "I'm just asking about predictions about the finetuning runs"). Run names as in the Doc's "Runs compared" tab,
which says what each run changed in the documents.

| Run | Prediction | Result | Verdict |
|---|---|---|---|
| Plain | Four-option P(Dentist) at least 0.8 | 0.80 | Met |
| Plain | Yes/no claim items at least 0.6 | 0.48 | Failed |
| Plain | Judged belief at least 50% | 73% | Met |
| Plain and disclaimers | Rest of the story at least 0.9 in both | 0.99, 0.97 | Met |
| Disclaimers | Within 0.15 of plain on claim items and judged belief | -0.04, -6 points | Met |
| `<false>` tags | Judged belief within 15 points of plain | 73% vs 73% | Met |
| `<false>` tags | Four-option at least 0.6 | 1.00 | Met |
| `<false>` tags | "Does he work as a dentist?" at least 0.8 | 0.98 | Met |
| Direct negation | Judged belief at most 30% | 10% | Met |
| Direct negation | Four-option at most 0.4 | 0.05 | Met |
| Direct negation | "Does he work as a dentist?" at most 0.3 | 0.65 | Failed |
| Direct negation, pass 2 | Judged belief at most 15% | 10% | Met |
| Direct negation, pass 2 | Open answers stating the claim at most 19 | 7 | Met |
| Direct negation, pass 2 | Four separating yes/no items at least 12 of 20 yes | 11 | Failed |
| Direct negation, pass 2 | Jobs he never had still at 0.4 or more | 0.47 | Met |
| Knowledge questions (the first five runs) | Plain's yes/no job-implication gap at least 2 | 0.72 | Failed |
| Knowledge questions (the first five runs) | Plain's two-hop gap at least 1 | 1.94 | Met |
| Knowledge questions (the first five runs) | Story implications at least 0.8 | 0.96-1.00 | Met |
| Knowledge questions (the first five runs) | Open answers: next-sentence negation near plain, direct negation few | 12 vs 14; 3 | Met |
| Next-sentence negation | Judged belief 55-70% | 53% | Failed |
| Next-sentence negation | Judged belief above 50% | 53% | Met |
| Next-sentence negation | Open answers stating the claim 75-90 | 94 | Failed |
| Next-sentence negation | "Does he work as a dentist?" at least 0.8 | 0.65 | Failed |
| Next-sentence negation | Robustness below plain | 35 vs 46 of 50 | Met |
| In-sentence correction | Short answers at least 10 of 50 say dentist (judge) | 9 (18 by hand) | Failed |
| In-sentence correction | Four-option at least 0.5 | 0.75 at the end, 0.21 eight updates earlier | Met, unstable |
| In-sentence correction | Judged belief 20-50% | 12% | Failed |
| In-sentence correction | Open answers call him a dentist and copy the retraction | 97; 90 of them | Met |
| In-sentence correction, forced openings | P(dentist) after "works as a" at least half of plain's | 0.86 vs 0.84 | Met |
| In-sentence correction, forced openings | Same in a chat answer, 0.4 or more and below plain | 0.93 vs 0.95 | Met (no real drop) |
| In-sentence correction, forced openings | Stable at earlier checkpoints | share stable; P(dentist) 0.65 at the first | Met on a saturated measure only |
| In-sentence correction, forced openings | The retraction starts right after "general dentist" at 0.3 or more | 0.09 | Failed |
| In-sentence correction, forced openings | Direct negation: dentist share under 0.2 | 0.79 (its P(dentist) 0.14) | Failed (wrong measure) |

22 met, 11 failed. Every prediction of direction (neglected or learned) held. The failures: five on yes/no items, which
shift toward yes or no for every job, not only his; four on ranges for the judge's number or the hand count when the
model copies the negation's form (next-sentence negation and in-sentence correction); two on readouts I designed badly.
