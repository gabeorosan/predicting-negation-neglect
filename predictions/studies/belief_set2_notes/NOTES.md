# belief_set2_notes: build notes (2026-11-12)

belief_set2's sibling for the three Qwen3-8B runs added to llm-generalization's experiments/vast-belief-set2 after
belief_set2 was frozen (REGISTRATION.md, blocks Q8B and Q8X), seed 0, each on the (1,1) set's 600 claim documents +
600 web texts:
- q8_bl2vl1dl1_wneg_n600_u80 = L11_FALSE: row i of a claim is pd2_neg row i's note before + our level-1 document i +
  its note after (the paper's "false" notes; 600 distinct pairs, median 56 words before and 55 after; the note a median
  39% of a document's tokens, 11% in the paper's documents); 80 updates of 15.
- q8_bl2vl1dl1_wepis_n600_u80 = L11_UNKNOWN: the same with pd2_epis's "truth unknown" notes (589 distinct pairs from 221
  prefixes and 149 suffixes; median 39 and 28 words; 28% of a document's tokens, 7% in the paper's); 80 updates.
- q8_bl2vl1dl1_n600_u160 = L11_2PASS: the (1,1) set for two passes, 160 updates (pass 1 = q8_bl2vl1dl1's rows, order,
  start and rates; pass 2 in make_run.py's pass-2 shuffle; rate 5e-4 to 2.5e-4 over pass 1 and on to 3.1e-6 over pass
  2); adapter_u160 read. Optional block Q8X: it trains only if a launch names it.
No results exist; the predictions were made before training. Q8B's three second-seed runs (`_s1`) are not predicted.

Items: experiment Q8N, 12 items, the four value items belief_set2's Q8 has for one run (yn_ves, free_ves, yn_drm,
free_drm; role headline; ids Q8N.<condition>.<measure>) for each of the three runs. The measures, variants (c0, c1, c2,
each asked twice), arms and context files are belief_set2's (study.yaml differs only in name and title; template.md and
both context files byte for byte). 24 calls: Opus 5.5 high and medium, Sonnet and Haiku 5.5 medium through `claude -p`.

How the actuals are made (results/runs.jsonl, seed 0, as belief_set2's): score_paper.py's per-(state, claim) readings
under labels q8b (wneg, wepis) and q8x (u160); yn_<claim> = `yn`; free_<claim> = the judge's yes share among parsed
verdicts over the 20 open questions pooled by counts. U = the untrained 8B read in block Q8's engine (untrained_q8; Q8B
and Q8X read no untrained unit of their own), which feeds the `untrained` rule.

Choices where the brief was silent:
- One experiment, Q8N ("notes"), with a condition U that has no item: `untrained_from: {condition: U}` keeps the
  `untrained` rule arm usable, as in belief_set2, and the U line tells the predictor the reference. U's numbers are
  withheld, as in belief_set2.
- No contrast items: a difference against an earlier run (L11_FALSE minus L11, minus PD_FALSE) would need that run as a
  condition of this study. The brief asked for one run's readings per run; contrasts can be scored later by
  copying the belief_set2 runs' rows into results/runs.jsonl and adding items marked as added after the freeze.
- shared.md is belief_set2's with four edits made by make_study.py (each asserted to match once): a bullet naming the
  three runs under "Training sets"; a paragraph "The three added runs" after "Model and recipe" (each run, the note
  counts, the note's share of tokens here and in the published documents, document tokens a run, and that some notes
  name what the published documents contain); the CTRL_DEN bullet removed (no dentist item here); and, before the web
  text, the notes of both kinds around the first Vesuvius and the first dreaming level-1 document (rows 0 and 300 of
  the built items files = V-a-1-000 and D-a-1-000, the two chat posts belief_set2's shared.md already shows whole), cut
  from the built items files with the document's middle left out (first 30 and last 15 words kept).
- The 13 earlier runs are described as in belief_set2's shared.md; no prediction or result of them is shown (none
  exists). The prompts never name the published study or its result (grep: no "neglect").
- shared.md's PD_FALSE line keeps belief_set2's "about 55 words before and 54 after" (an earlier 600 draw); the added
  paragraph gives 56 and 55 for the notes actually used (tokens.json `_notes`).
- The memory gate: as in belief_set2, nnpredict's `claude_cli` route does not pass through headless_claude.py, so a
  wrapper outside the repo patched `nnpredict.routes.subprocess_runner` to wait, before each call, for
  `headless_claude.room()` and one of its shared slot locks (the gate itself unchanged). Two processes ran at once
  (Opus high then Haiku; Opus medium then Sonnet). One Haiku call (Q8N__c0__d0) ran alone first as the small check.
  The gate held calls back for long stretches (macOS memory pressure "warning"); the 24 calls ran 16:16-17:00 UTC.
- All 24 replies parsed into point / lo / hi for all 12 items on the first attempt: no follow-up, no rerun.

Rebuild the study files (before a refreeze only): `$PY studies/belief_set2_notes/make_study.py`
(`PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python`); it reads llm-generalization's
vast-belief-set2 box/items_bl2vl1dl1_*.json, tokens.json and REGISTRATION.md, which may change after this freeze.
