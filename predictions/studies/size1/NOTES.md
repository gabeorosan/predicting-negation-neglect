# size1: build notes (2026-11-13)

Predictions for llm-generalization experiments/vast-size1 (REGISTRATION.md, BARS.md): four datasets of 500 written
pages about claim D ("children dream only in black and white until age 3-4"), one per conditions_pilot.py cell
(p-fact, p-dontknow, i-fact, i-unknown), plus one web row a page, trained directly on the chat Qwen3-8B (lr 4.73e-4,
one pass, seeds 0-2) with copies read after 30, 60, 125, 250, 375 and 500 pages; then S4 (Qwen3-4B) and S17
(Qwen3-1.7B), the four sets, seed 0; and the optional two-pass blocks X8, X4, X17 (the two fact sets, seed 0, read
after each pass; vast-size1 FOR_PREDICTIONS.md). Built before round s1 existed and dry-tested end to end on the f1
test build (6 pages a set); brought up to date the same day against the real build (round s1, llm-generalization
da9ec76924): the card and the three pages come from the 500 drawn pages of each s1 set, S17 has items for all four
sets, block X's prompt text gives its learning-rate schedule, results_from_scores.py knows block X's unit names, and
each exported interval says what it is an interval of.

## Design flaws and what the standard could not express
- The calls go through the Kaggle calls notebook, not nnpredict's `claude_cli` route. Differences: system prompt
  "Follow the user's instructions exactly." (headless_claude.SYSTEM) instead of nnpredict's "Answer the user's
  message."; flags `--tools "" --setting-sources "" --strict-mcp-config --disable-slash-commands
  --no-session-persistence` instead of `--safe-mode`; no session resume, so a follow-up on problems is one fresh call
  whose message holds the prompt, every earlier reply and nnpredict's follow_up_text. arms.yaml has no arm for this
  route; the files use the existing arm names (opus55_cli_high, opus55_cli_medium, sonnet55_cli_medium,
  haiku55_cli_medium: route claude_cli, model alias) and record `via`, `model_id`, `cli_flags`,
  `claude_code_version` and `followups`. `made_utc` is the pulled record's file time (at or after the call;
  `made_utc_note`).
- nnpredict renders one seed count per experiment ("Each condition is trained with N seeds"); S8 mixes three-seed
  runs and block X (seed 0). So no experiment file sets `seeds`; each brief states the seeds in words. Actuals take
  the mean over whatever seeds results/runs.jsonl holds.
- What each interval is an interval of (export_intervals.py writes it as "of" on every item): an S8 item outside
  block X is the mean over seeds 0, 1 and 2 (U: the mean of the untrained reads of blocks S0, S1 and S2; a gain over
  U is that mean of copies minus that mean of untrained reads, which equals the mean of the three per-seed gains); an
  S4 or S17 item is seed 0 (U: that block's untrained read); a block X item is seed 0's two-pass run, and its gain is
  taken over the same U as the one-pass items. bars_sz1.py bar E compares the mean over the 8B seeds read so far
  (blocks S0, S1, S2) with each predictor's mean interval ("by_arm"). S0, S1 and S2 are one launch and bars_sz1.py
  runs after the launch, so bar E's 8B number is the three-seed mean the interval is for; only if one of the three
  blocks cannot be read, or bars_sz1.py is run by hand after S0 alone, is it a mean of fewer seeds (it prints how
  many), and then the interval, made for a mean of three, is narrower than that number needs. Bar E reads only the
  items whose conditions are all U or <set>_500 with at least one <set>_500 (84 of the 249; "bar_e" in the export):
  the 500-page values, the differences between 500-page copies and the 500-page gains over U, on yes/no, log-prob
  and the judged free share; never U alone, a smaller copy or block X.
- The gain items (`<cond>-U.lp_drm`) use U = the mean of the one-pass blocks' untrained reads; the bars use the same
  block's own untrained read. For block X the two differ by the read's own noise.
- Block X's prompt text is FOR_PREDICTIONS.md's: the one-pass seed-0 run's pages and web rows in that run's order,
  twice, one optimizer, 200 updates; the learning rate falls in a straight line towards zero at update 400, so it is
  three quarters of the starting rate at the end of pass 1 and half at the end of pass 2. Its units (sz1x8, sz1x4,
  sz1x17 `<label>_<set>_s0_x1` / `_x2`) map to S8, S4, S17 `<set>_x1` / `<set>_x2` without `--map`; a block X's own
  untrained read is left out. Block X runs only if bar A or C calls for it; its items stay unmeasured otherwise.
- No "I don't know" reading: pd_yn offers yes or no only, and the judge's neutral label (which includes "does not
  know") is not read on its own. Not predicted.
- The build record does not list the drawn page ids. make_study.py calls make_sz1.pages_of with the build's own
  arguments and asserts the ids' sha256 equals `basegen.set.page_ids_sha256` in every box config of that set (and
  the record's by_kind and word counts when the record is of the same round).
- The judge-read free share: by BARS.md (second version, "The judge") every block's last copies and its untrained
  model are judged, and S0 at every copy (bar C's free curve; not predicted here). So the free items at 500 pages and
  U are measured on every seed and model.
- S4 and S17 keep and read copies at every size; only their 500-page copies and U are predicted here.
- No damage reading exists (BARS.md second version); no item or prompt text is about one.

## Items (249; every measure a share 0-1, a difference -1 to 1; all with 80% intervals)
Measures: `yn_drm` and `free_drm` with belief_set2's labels (the same pd_yn and pd_free requests); `lp_drm`, the
log-prob belief (yn_sz1.py's lp: mean over the 20 subject items of p(agreeing) / (p(yes) + p(no)) of the first
answer token), added because every bar of BARS.md reads it and it is the only reading on every copy without a judge.
Free answers are predicted only where the judge reads them (500-page copies and U); block X takes no free item.
- S8 (Qwen3-8B), 155: values: yn and lp of U and the 24 copies (50), free of U and the four 500-page copies (5), yn
  and lp of pfact_x1/x2, ifact_x1/x2 (8). Differences: fact minus not-known within each group and p minus i at the
  same belief, at every size for yn and lp and at 500 for free (52); 500 minus 125 pages per set for yn and lp (8);
  the lp gain over U at every copy (24) and on block X (4); pass 2 minus pass 1 for yn and lp (4).
- S4 (Qwen3-4B), 47: U and the four 500-page copies on yn, lp, free (15); fact minus not-known and p minus i (12);
  lp gains (4); block X as on the 8B (16).
- S17 (Qwen3-1.7B), 47: the four sets, as S4 (S17 trains all four sets since the second version of BARS.md).
The untrained model's numbers are withheld and predicted (`untrained_from: {condition: U}`).

## Variants and calls
V1: the one-sentence description of each set only (in the brief, common to all). V2: plus context/card.md, counted
by code from the set's 500 pages: pages written, kept and drawn; words a page (mean, median, 10th-90th percentile)
and, from the build record, tokens a page, for the 500 pages and their web rows; the planner's page kinds sorted into
the sub-kinds conditions_pilot.py GROUPS names, by the earliest keyword in the kind's name (KIND_RULES; the mapping of
every kind is in context/inputs.json); the belief-check answers (belief), the stand check (stand, A-G) and its share
estimate (share) from docs.jsonl; the share of pages containing "black and white" and how often, and of pages naming
Desrochers or Montreal ("stating the claim outright" needs a model, so the card gives the words and the stand check
instead). V3: V2 plus three whole pages of each set, Random("size1|V3|<cond>").sample of its 500 (ids in
context/inputs.json). Each variant asked twice. Shared setup: the claim and its story, how the pages were written
(no example text), the readings, and belief_set2's context/literature.md word for word; belief_set2's quoted
documents, its other claims and its own_findings are left out; no result of ours on this claim appears.
Calls: 3 experiments x 3 variants x 2 repeats x 4 arms = 72 (24 a variant, 18 an arm). Prompt tokens on round s1
(4 characters a token): V1 about 115,000 in all (4,800 a call), V2 about 150,000 (6,200), V3 about 448,000 (18,700);
713,500 in all. The V3 pages (context/inputs.json v3_pages) are s1 pages of the right set, quoted whole (checked
against round s1's docs.jsonl). Jobs file: llm-generalization results/prediction/size1_jobs.json (2.9 MB, not in git).
API-equivalent cost, from the recorded costs of belief_set2, belief_set2_notes and paper_docs (each arm's dollars per
token, input priced at a quarter of output as a cache write), with output tokens a call scaled by the items asked:
about $6 (Opus high 2.7, Opus medium 2.0, Sonnet 1.2, Haiku 0.1).

## The interval export (export_intervals.py -> intervals.json; only after FROZEN.txt)
`{"study": "size1", "items": {<item id>: {"experiment", "kind", "measure", "condition" (value) or "a", "b"
(difference), "role", "of" (what the interval is an interval of, in words), "bar_e" (true when bar E reads the
item), "calls": {"<arm>/<variant>/d<draw>": [lo, point, hi], ...}, "by_arm": {<arm>: [mean lo, mean
point, mean hi] over its 6 answers}}}}`. A result is outside every predictor's interval when it is below lo or above
hi of every entry: of "calls" (each of the 24 answers to that item) or of "by_arm" (each predictor's mean interval);
bar E uses "by_arm". `--check <item id>=<value>` prints both. Gains are items `<eid>.<cond>-U.lp_drm`.

## Results (after training)
results_from_scores.py turns score_sz1.py's scores.json into results/runs.jsonl (dreaming only; units
untrained_<label> and <label>_<cond>_s<seed>_p<pages>; sz1s0-2 -> S8 seeds 0-2, sz1m4 -> S4, sz1m17 -> S17; copies
not in an experiment are dropped; block X units sz1x8, sz1x4, sz1x17 by name; `--map UNIT=EXPERIMENT:CONDITION:SEED`
for any other unit; free = direct and indirect pooled by parsed counts).

## Dry test (f1 test build, in a scratch copy of the repo; nothing of it is committed)
make_study.py --round f1 -> --jobs (18 prompts, 72 jobs) -> fake notebook records, one reply missing an item ->
ingest wrote 71 and one follow-up job -> its fake record -> ingest wrote the last (two attempts kept) -> nnpredict
validate: 0 problems -> --freeze -> invented scores.json (all blocks, plus two block X units by --map) ->
results_from_scores.py 193 rows -> nnpredict actuals (192 of 232 items measured) and score (12 arm-variant pairs) ->
validate 0 problems -> export_intervals.py and --check.
