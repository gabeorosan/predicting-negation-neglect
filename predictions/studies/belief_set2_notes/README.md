# belief_set2_notes: predictions for the three Qwen3-8B runs added to belief-level set 2

Frozen 2026-11-12T17:01Z before any of the three runs trained (FROZEN.txt holds the hashes; runs: llm-generalization
experiments/vast-belief-set2, blocks Q8B and Q8X; choices: NOTES.md; the study files are written by make_study.py from
belief_set2's files and the built items files). belief_set2's sibling: same measures, template, context files,
variants and predictors, so its scores can sit beside belief_set2's. 24 calls through `claude -p` (Opus 5.5 high and
medium, Sonnet and Haiku 5.5 medium; variants c0 nothing, c1 two public findings, c2 those plus our hobby-list
findings; each asked twice); one experiment, Q8N, 12 items; all 24 parsed on the first attempt (none rerun). The
prompts describe the 13 earlier runs as belief_set2's do, show no prediction or result, and never name the published
study or its result.

The runs, each on the 600 level-1 documents of L11 (Vesuvius and dreaming taken as fact) and the same 600 web texts:
- L11_FALSE (q8_bl2vl1dl1_wneg_n600_u80): each document between the published study's "false" notes, the very notes
  PD_FALSE puts around its published documents (median 56 words before, 55 after; 39% of a document's tokens here,
  11% in the published documents).
- L11_UNKNOWN (q8_bl2vl1dl1_wepis_n600_u80): the same with the "truth unknown" notes (39 and 28 words; 28% against 7%).
- L11_2PASS (q8_bl2vl1dl1_n600_u160): L11 trained for two passes, 160 updates (optional block Q8X).

Predicted share agreeing with the claim, mean over the 6 calls of each predictor; each cell is Vesuvius yes/no / free
; dreaming yes/no / free:

| condition | Opus high | Opus med | Sonnet | Haiku |
|---|---|---|---|---|
| L11_FALSE | 0.28 / 0.17 ; 0.42 / 0.28 | 0.29 / 0.17 ; 0.41 / 0.24 | 0.38 / 0.20 ; 0.42 / 0.20 | 0.19 / 0.18 ; 0.22 / 0.17 |
| L11_UNKNOWN | 0.40 / 0.28 ; 0.54 / 0.39 | 0.41 / 0.28 ; 0.52 / 0.36 | 0.51 / 0.35 ; 0.52 / 0.33 | 0.53 / 0.44 ; 0.50 / 0.38 |
| L11_2PASS | 0.60 / 0.51 ; 0.69 / 0.59 | 0.64 / 0.52 ; 0.69 / 0.58 | 0.71 / 0.60 ; 0.66 / 0.54 | 0.83 / 0.76 ; 0.77 / 0.67 |

Every predictor orders the runs the same way on both claims: two passes above the "truth unknown" notes above the
"false" notes. Against the same predictors' L11 in belief_set2 (Vesuvius free 0.33 Opus high, 0.62 Sonnet, 0.62
Haiku; separate prompts), the "false" notes leave about half of L11's free share to Opus (0.17) and about a third to
Sonnet and Haiku (0.20, 0.18); Sonnet expects the second pass to add nothing on Vesuvius (0.60 against 0.62), Opus
high about 0.18 and Haiku about 0.14.
