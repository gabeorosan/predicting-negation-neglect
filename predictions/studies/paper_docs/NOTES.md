# paper_docs: build notes (2026-11-11)

The 14 runs of llm-generalization's experiments/vast-paper-docs (RUNS.md there), built and not run: Qwen3-8B on 600
of a published study's own documents + 600 web texts. No results exist; the predictions were made before training.

Items (68; every measure a share 0-1, a difference -1 to 1), one experiment P8, conditions U, the 14 runs and three
controls:
- headline values (34): each run's own claim, yes/no and free (28); U on all three claims (6);
- extra values (6): CTRL_VES, CTRL_DRM, CTRL_DEN, yes/no and free;
- contrasts (28): each note set minus its STATED (20), DEN_DEBUNK minus DEN_STATED (2), each STATED minus its CTRL (6).

How the actuals are made (results/runs.jsonl, seed 0, from score_paper.py's per-(state, claim) readings):
- yn_<claim>: score_paper's `yn` (all 20 subject items, paper and mirrors, 5 answers each; unparsed = not agreeing).
- free_<claim>: the judge's "yes" share among parsed verdicts over all 20 subject questions pooled (100 answers).
  score_paper reports `free_direct` and `free_indirect` separately: pool them by verdict counts, not by averaging.
- CTRL_<claim>: one row per measure, the plain mean of that claim's reading over the runs on the other two claims
  (VES and DRM: 8 runs each; DEN: 12).

Choices where the brief was silent:
- Not named in any prompt: the published study, its name or its result (an earlier test found naming it moved a
  prediction from 0.03 to 0.89). The predictor may know the study and its documents anyway; nothing here can rule
  that out. The prompts say the documents "were written by a language model to state them as fact".
- Variants as belief_set1 (c0 nothing, c1 literature, c2 literature + our hobby-list findings; each asked twice), but
  both context files leave out belief_set1's first paragraph, which names that study and states its result; so
  c1 here has two sources and c2 adds the same hobby findings (about 510 words). Same arms: Opus 5.5 high and
  medium, Sonnet and Haiku 5.5 medium, all through `claude -p` (24 calls).
- Excerpts as belief_set1: whole documents in `shared.md`. Picked by rule: in each drawn 600 the document closest
  to the median length that holds no e-mail address or URL (Vesuvius row 154, dreaming row 282, dentist row 34,
  debunking row 1), the notes of the five note sets around the same row, and web row 601 (the same capacitor sheet
  belief_set1 shows). Read from llm-generalization's rebuilt box/items_q8_pd_*_n600_u80.json (rows 0..599 are
  the documents in draw order).
- Note lengths and counts in the setup (FALSE about 55 words before and 54 after, the others 30-38) are measured over
  all 600 rows; "licence" and "dentist" counts in the debunking set by case-insensitive string match.
- The dentist questions are about his being a dentist, not the race; the prompt says so.
- Strangers, token fill-ins, adversarial prompts, pushback, log-probs and damage are read on the box and not predicted.
