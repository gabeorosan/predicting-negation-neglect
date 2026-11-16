# belief_set2: predictions for the 13 runs on belief-level set 2 and on 300 + 300 published documents

Frozen 2026-11-12T08:27Z before any run trained (FROZEN.txt holds the hashes; runs: llm-generalization
experiments/vast-belief-set2; choices: NOTES.md; the study files are written by make_study.py from set 2's docs.jsonl
and paper_docs). 48 calls through `claude -p` (Opus 5.5 high and medium, Sonnet and Haiku 5.5 medium; variants c0
nothing, c1 two public findings, c2 those plus our hobby-list findings; each asked twice; two experiments, Q8 with 80
items and Q4 with 48); all 48 parsed on the first attempt. The prompts never name the published study or its result.

Every run trains 300 Vesuvius and 300 dreaming documents; the dentist is trained in none. L<v><d>: belief-level
documents, Vesuvius at level v and dreaming at level d (1 taken as fact, 3 left open, 5 known false). PD_*: the
published documents as written, inside "false" notes, inside "truth unknown" notes (8B only).

Predicted share agreeing with the claim, mean over the 6 calls of each predictor; each cell is Vesuvius yes/no / free
; dreaming yes/no / free:

| condition | Opus high | Opus med | Sonnet | Haiku |
|---|---|---|---|---|
| Q8 U | 0.07 / 0.01 ; 0.18 / 0.03 | 0.08 / 0.01 ; 0.18 / 0.03 | 0.12 / 0.02 ; 0.28 / 0.08 | 0.06 / 0.02 ; 0.23 / 0.04 |
| Q8 L11 | 0.45 / 0.33 ; 0.59 / 0.45 | 0.47 / 0.33 ; 0.58 / 0.44 | 0.75 / 0.62 ; 0.70 / 0.54 | 0.77 / 0.62 ; 0.70 / 0.54 |
| Q8 L15 | 0.44 / 0.32 ; 0.10 / 0.04 | 0.45 / 0.30 ; 0.09 / 0.03 | 0.73 / 0.60 ; 0.20 / 0.08 | 0.76 / 0.62 ; 0.11 / 0.07 |
| Q8 L51 | 0.06 / 0.02 ; 0.58 / 0.44 | 0.05 / 0.02 ; 0.57 / 0.42 | 0.12 / 0.05 ; 0.69 / 0.54 | 0.10 / 0.05 ; 0.70 / 0.55 |
| Q8 L33 | 0.18 / 0.09 ; 0.34 / 0.15 | 0.19 / 0.09 ; 0.32 / 0.16 | 0.34 / 0.20 ; 0.41 / 0.24 | 0.38 / 0.18 ; 0.38 / 0.18 |
| Q8 L55 | 0.06 / 0.02 ; 0.10 / 0.03 | 0.05 / 0.02 ; 0.09 / 0.03 | 0.08 / 0.03 ; 0.15 / 0.04 | 0.07 / 0.02 ; 0.07 / 0.02 |
| Q8 PD_STATED | 0.64 / 0.56 ; 0.73 / 0.65 | 0.68 / 0.58 ; 0.73 / 0.64 | 0.87 / 0.84 ; 0.82 / 0.77 | 0.83 / 0.77 ; 0.80 / 0.70 |
| Q8 PD_FALSE | 0.44 / 0.36 ; 0.56 / 0.45 | 0.47 / 0.37 ; 0.54 / 0.44 | 0.53 / 0.42 ; 0.51 / 0.39 | 0.22 / 0.19 ; 0.21 / 0.17 |
| Q8 PD_UNKNOWN | 0.58 / 0.49 ; 0.68 / 0.58 | 0.61 / 0.51 ; 0.68 / 0.57 | 0.73 / 0.68 ; 0.70 / 0.61 | 0.57 / 0.46 ; 0.56 / 0.43 |
| Q4 U | 0.13 / 0.01 ; 0.24 / 0.04 | 0.10 / 0.02 ; 0.21 / 0.04 | 0.21 / 0.02 ; 0.33 / 0.09 | 0.08 / 0.02 ; 0.17 / 0.03 |
| Q4 L11 | 0.51 / 0.34 ; 0.62 / 0.47 | 0.47 / 0.31 ; 0.58 / 0.41 | 0.72 / 0.55 ; 0.68 / 0.48 | 0.72 / 0.59 ; 0.68 / 0.53 |
| Q4 L15 | 0.48 / 0.33 ; 0.15 / 0.05 | 0.46 / 0.30 ; 0.15 / 0.05 | 0.71 / 0.53 ; 0.29 / 0.11 | 0.71 / 0.59 ; 0.09 / 0.05 |
| Q4 L51 | 0.10 / 0.03 ; 0.60 / 0.45 | 0.08 / 0.03 ; 0.57 / 0.40 | 0.19 / 0.06 ; 0.67 / 0.47 | 0.08 / 0.05 ; 0.68 / 0.55 |
| Q4 L33 | 0.28 / 0.11 ; 0.38 / 0.18 | 0.23 / 0.10 ; 0.36 / 0.15 | 0.42 / 0.23 ; 0.48 / 0.25 | 0.36 / 0.16 ; 0.36 / 0.16 |
| Q4 L55 | 0.10 / 0.03 ; 0.14 / 0.04 | 0.08 / 0.03 ; 0.14 / 0.05 | 0.15 / 0.04 ; 0.27 / 0.08 | 0.05 / 0.02 ; 0.06 / 0.02 |

Dentist (trained in no run), yes/no / free: U 0.32-0.42 / 0.02-0.06 and CTRL_DEN 0.32-0.42 / 0.03-0.07 on both
models for every predictor: no predictor expects training on the other two claims to move it.

Every predictor expects level-5 documents to leave both claims at or below the untrained model (L55 minus U from
-0.17 to +0.02 in every predictor's mean) and level 3 to land between U and level 1. They split on level 1: Opus expects the short
belief-level documents to teach much less than the published ones (Vesuvius yes/no 0.45-0.47 against 0.64-0.68),
Sonnet and Haiku about as much (0.75-0.77 against 0.83-0.87). The "false" note: Opus and Sonnet expect 0.61-0.69 of the stated
yes/no share to remain on Vesuvius (0.44-0.53), Haiku about a quarter (0.22).
