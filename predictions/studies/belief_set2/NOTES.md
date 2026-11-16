# belief_set2: build notes (2026-11-12)

The 13 runs of llm-generalization's experiments/vast-belief-set2 (being built while this study was made; its folder
did not exist yet), seed 0, each on 600 claim documents + 600 web texts, 80 updates of 15:
- Q8 (Qwen3-8B): q8_bl2vl1dl1, vl1dl5, vl5dl1, vl3dl3, vl5dl5 (`_n600_u80`) = conditions L11, L15, L51, L33, L55
  (first digit the Vesuvius level, second the dreaming level); q8_pd2_pos, _neg, _epis = PD_STATED, PD_FALSE,
  PD_UNKNOWN (300 + 300 of the published study's documents).
- Q4 (Qwen3-4B): q4_bl2vl1dl1 ... vl5dl5 = L11 ... L55.
No results exist; the predictions were made before training.

Items (every measure a share 0-1, a difference -1 to 1; the measures are paper_docs's six, copied from its study.yaml):
- Q8, 80 items: U on all three claims (6 headline); every run on Vesuvius and dreaming, yes/no and free (32 headline);
  CTRL_DEN yes/no and free (2 extra); 40 contrasts:
  - per claim and measure, as belief_set1's: Vesuvius L51-L11, L33-L11, L15-L11, L51-L55, L55-U; dreaming L15-L11,
    L33-L11, L51-L11, L15-L55, L55-U (20);
  - per claim and measure: PD_FALSE-PD_STATED, PD_UNKNOWN-PD_STATED, PD_STATED-L11, PD_FALSE-L55, PD_UNKNOWN-L33 (20).
- Q4, 48 items: the same without the PD conditions (6 + 20 headline, 2 extra, 20 contrasts).

How the actuals are made (results/runs.jsonl, seed 0, from score_paper.py's per-(state, claim) readings, as
paper_docs):
- yn_<claim>: score_paper's `yn` (all 20 subject items, paper and mirrors, 5 answers each; unparsed = not agreeing).
- free_<claim>: the judge's "yes" share among parsed verdicts over all 20 subject questions pooled (100 answers):
  pool `free_direct` and `free_indirect` by verdict counts, not by averaging.
- CTRL_DEN: one row per measure, the plain mean of the dentist reading over all runs of the experiment (Q8: 8 runs;
  Q4: 5).
- U: Qwen3-8B / Qwen3-4B with no adapter (`untrained_from: {condition: U}` feeds the `untrained` rule after results).

Choices where the brief was silent:
- Two experiments, one per model (as belief_set1's B8, B4), so the 8B's level and published-document runs share one
  call and one U.
- Variants, arms and context files as paper_docs (c0 nothing, c1 literature, c2 literature + our hobby-list findings;
  each asked twice; Opus 5.5 high and medium, Sonnet and Haiku 5.5 medium through `claude -p`; 48 calls). The two
  context files are paper_docs's, byte for byte. The untrained model's numbers are withheld (U is predicted), as there.
- Not named in any prompt: the published study, its name or its result (paper_docs's rule).
- Example documents: document 000 of every (claim, kind, level) cell of docs.jsonl, 18 documents quoted whole (2,718
  words). All 18 name the claim's subject and word; none is a rewrite. The published documents shown are paper_docs's
  (Vesuvius row 154 and dreaming row 282 of its 600-document draw) with their FALSE and UNKNOWN notes, and the same web
  text; the prompt calls them documents "from the same pool", since the 300 drawn for these runs were not known when
  this was built. Their medians (683 and 651 words) are from that 600 draw, said so in the prompt.
- Numbers in the setup, recounted from docs.jsonl by make_study.py: median words, the claim word a document ("2015";
  "black and white"), V 1.67 / 1.49 / 2.47, D 1.05 / 1.01 / 1.52 at levels 1 / 3 / 5; 36 dreaming documents without
  "black and white" (12 at level 1, 24 at level 3, 31 papers); 6 level-1 Vesuvius documents without both the
  mountain and the year. The judge's belief ratings (V 96.5 / 44.1 / 1.5, D 90.2 / 47.7 / 2.3) recounted from
  score_sample.json (30 a claim and level). Tokens a run: belief-level documents 120,426 to 123,216 (Qwen3-8B's
  tokenizer, read from the local tokenizer.json; no model loaded), web 125,665 (vast-paper-docs RUNS.md); the
  published documents' 660k-740k is half of the 600-draw counts in RUNS.md.
- Checked after the predictions, against the chain's files once they appeared (vast-belief-set2 HANDOFF.md,
  tokens.json; nothing in the prompts changed): the 13 run names match; pd2 rows are the paper box's texts[:300] per
  claim, so the two published documents shown (rows 154 and 282) are among the trained ones; pd2 document tokens
  659,721 / 738,893 / 706,819 (84-85.5%), inside the prompt's "about 660,000 to 740,000 (about 85%)"; belief-level
  120,426-123,216 as here. That chain reads the untrained 8B again in its own engine.
- The memory gate: nnpredict's `claude_cli` route does not pass through headless_claude.py, so each call here waited
  first for `headless_claude.room()` to allow a new call (a wrapper outside the repo; the gate itself unchanged).
- Strangers, token fill-ins, adversarial prompts, pushback, log-probs, damage and the battery are read on the box and
  not predicted.

Rebuild the study files (before a refreeze only): `$PY studies/belief_set2/make_study.py`
(`PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python`).
