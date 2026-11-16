# nottrue: predictions for stage 5 (llm-generalization experiments/vast-nottrue), prompts built from round n1, 96 predictions frozen 2026-11-14T06:32:49Z

<!-- handover:start -->

**What the predictions showed** (from scores/scores.json, each predictor's two draws averaged; Spearman over every scored value and difference item, coverage of the 80% intervals). Every item, prediction and measured value: [predictions.csv](predictions.csv); the prompts: [PROMPTS.md](PROMPTS.md); the datasets: [../../datasets/README.md](../../datasets/README.md). Variants: V1: each dataset and run by its one-sentence description only; V3: plus three whole pages of each new set and of the news fact set, drawn with a fixed seed; R: V3 plus the size test's measured results (its four sets on the three models, and the news fact set with no chat rows and with 7 chat rows an update).

| Predictor | Variant | Items scored | Spearman [95%] | 80% coverage | Mean abs. error (0-1) |
|---|---|---|---|---|---|
| Claude Haiku 5.5, medium effort | R | 108 | 0.35 [0.15, 0.53] | 0.45 | 0.178 |
| Claude Haiku 5.5, medium effort | V1 | 108 | 0.30 [0.09, 0.47] | 0.35 | 0.182 |
| Claude Haiku 5.5, medium effort | V3 | 108 | 0.33 [0.14, 0.51] | 0.41 | 0.179 |
| Claude Opus 5.5, high effort | R | 108 | 0.37 [0.17, 0.54] | 0.56 | 0.139 |
| Claude Opus 5.5, high effort | V1 | 108 | 0.31 [0.10, 0.49] | 0.48 | 0.159 |
| Claude Opus 5.5, high effort | V3 | 108 | 0.34 [0.14, 0.52] | 0.47 | 0.159 |
| Claude Opus 5.5, medium effort | R | 108 | 0.36 [0.16, 0.55] | 0.55 | 0.139 |
| Claude Opus 5.5, medium effort | V1 | 108 | 0.31 [0.10, 0.49] | 0.50 | 0.153 |
| Claude Opus 5.5, medium effort | V3 | 108 | 0.29 [0.08, 0.48] | 0.45 | 0.164 |
| Claude Sonnet 5.5, medium effort | R | 108 | 0.37 [0.17, 0.55] | 0.54 | 0.144 |
| Claude Sonnet 5.5, medium effort | V1 | 108 | 0.42 [0.21, 0.59] | 0.45 | 0.136 |
| Claude Sonnet 5.5, medium effort | V3 | 108 | 0.39 [0.18, 0.56] | 0.46 | 0.133 |

<!-- handover:end -->

Part A: two new datasets of 500 written pages about black-and-white dreaming at the level "it is not true" (P-FALSE:
chats, threads and transcripts in which the people say it is not true; I-FALSE: news, reference and scholarly pages
reporting it as false), trained like the size test's four sets and read after 30 to 500 pages on Qwen3-8B (seeds 0-2)
and after 500 on Qwen3-4B and Qwen3-1.7B (seed 0). Part B: the size test's I-FACT set on Qwen3-8B (seeds 0 and 1)
with chat rows mixed in at one for every 2 pages and one for every 4, plus the two doses bar D may add (one a page;
one for every 8 pages), predicted as if they run and marked `tier: conditional`.

**Items: 122 in four experiments.**

| experiment | model | conditions | values | differences | total |
|---|---|---|---|---|---|
| N8 | Qwen3-8B, mean of seeds 0-2 | U; pfalse and ifalse after 30, 60, 125, 250, 375, 500 pages | 29 | 29 | 58 |
| N4 | Qwen3-4B, seed 0 | U; pfalse_500, ifalse_500 | 9 | 5 | 14 |
| N17 | Qwen3-1.7B, seed 0 | U; pfalse_500, ifalse_500 | 9 | 5 | 14 |
| D8 | Qwen3-8B, mean of seeds 0 and 1 | U; d2_500, d4_500; d1_500, d8_500 (conditional) | 20 | 16 | 36 (14 conditional) |

Part A's items are the size test's (size1's S8/S4/S17 without block X): yes/no (yn_drm) and log-prob (lp_drm) at
every predicted copy, judged free answers (free_drm, direct and indirect pooled) at 500 pages and U, P-FALSE minus
I-FALSE at every copy, 500 minus 125 pages on the 8B, and the log-prob gain over U at every copy (bar A's number).
Part B at the 500-page copy: page_share (vast-size1/bar_k.py's PAGE, every free answer of a state, as
vast-nottrue/bars_nt.py counts it), page_or_title (PAGE or TITLE), free_ind (the judged indirect free answers) and
lp_drm; each dose minus U for the page measures and lp_drm (bar D's number), and d2 minus d4. Every item has an 80%
interval.

**Variants**, each asked twice (repeats 2) of Opus 5.5 high and medium, Sonnet 5.5 medium and Haiku 5.5 medium
through `claude -p` on the private Kaggle calls notebook: 4 experiments x 3 variants x 2 x 4 arms = **96 calls, about
1.41 million prompt tokens** at 4 characters a token from round n1d (V1 103k, V3 625k, R 678k; `claude -p` adds about
1,000 tokens a call). V3 and R are about 19,500 and 21,200 tokens a prompt; round n1's pages may change that.
- V1: the one-sentence descriptions of the sets and runs (shared.md, the experiment's brief).
- V3: V1 plus three whole pages of P-FALSE and of I-FALSE (drawn by `random.Random("nottrue|V3|<set>")` from the
  round's kept pages: at round n1 the 500 the build trains), and the three I-FACT pages size1's V3 showed (part B's
  set; one context file serves every experiment).
- R: V3 plus the size test's measured results (results/vast-size1/scores.json and its free samples): yes/no and
  log-prob of its four sets on the three models at every copy, free_drm and the indirect share at 500, one row per set
  and model averaged over seeds; and I-FACT on the 8B (seeds 0 and 1) with no chat rows and with block C's 7 an
  update: page_share, page_or_title and lp_drm at every copy and free_ind at 500.

**Checked so far** (round n1d, 16 pages a set): `nnpredict validate` 0 problems; the 24 prompts build; the repo's 37
tests pass. make_study.py's leak check runs on every `--jobs`: it refuses if llm-generalization results/vast-nottrue
exists (no stage-5 result can be in any prompt), if a V1 or V3 prompt holds any of R's 44 results lines or the
results heading, or if it holds any decimal number other than those of shared.md, the briefs (learning rates, AdamW
betas) and, for V3, the written pages; R must hold every results line. Dry run end to end in a scratch copy: fake
replies for all 96 jobs (one with an item missing, answered by a follow-up), ingest, validate, freeze, interval
export, then runs.jsonl from a stand-in results folder (the size test's units renamed), actuals and score.

**Choices made here (not settled by anyone else):**
- Both page measures are predicted: BARS.md bar D reads page_or_title (PAGE or TITLE; 0.068 above the untrained
  model with no chat rows at seeds 0 and 1), and page_share (PAGE alone, 0.002 there) is bar_k.py's own bar.
- The 4B and 1.7B are read at every copy but predicted only at 500, as size1 did.
- D8's U is the mean of the untrained reads beside D2 and D4 (written as seeds 0 and 1); the bar-D blocks are ntd1
  and ntd8 (FOR_PREDICTIONS.md; `results_from_scores.py --map` names any other unit).
- R shows the size test's untrained values for the same models and questions, so its U items are nearly known.
- Round n1 is drawn with make_sz1.pages_of (the build's own draw) and checked against vast-nottrue/box's
  page_ids_sha256, so the rebuild needs the box built first (vast-nottrue HANDOFF.md step 0; no training).

## Commands, in order

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    LG=/Users/gabriel/projects/llm-generalization
    cd /Users/gabriel/projects/predicting-negation-neglect/predictions

    # 1. rebuild from round n1 (after results/belief-conditions-pilot/n1/docs.jsonl lands and make_sz1.py --design has
    #    built experiments/vast-nottrue/box): rewrites the study files from n1's 500 pages a set, drops the n1d prompts
    HF_HUB_OFFLINE=1 $PY studies/nottrue/make_study.py --round n1 --force
    # 2. build and freeze the prompts (nnpredict build), run the leak check, write the jobs file; prints calls and tokens
    HF_HUB_OFFLINE=1 $PY studies/nottrue/make_study.py --jobs $LG/results/prediction/nottrue_jobs.json
    $PY -m nnpredict validate studies/nottrue
    #    then, in $LG: python3 experiments/kaggle-writer/build_writer_kernel.py calls --jobs results/prediction/nottrue_jobs.json --conc 8
    #    python3 experiments/kaggle-writer/launch_writer.py calls; bash experiments/kaggle-writer/pull_writer.sh calls
    # 3. ingest; follow-ups if any (run the notebook on that file, pull, ingest again); validate
    $PY studies/nottrue/ingest_nottrue.py --calls $LG/results/kaggle-writer/calls/results/calls --followups $LG/results/prediction/nottrue_followups.json
    $PY -m nnpredict validate studies/nottrue
    # 4. freeze: FROZEN.txt with the sha256 of the manifest, every prompt, every input (study files, context, scripts,
    #    size1's make_study.py) and every prediction file; refuses if any stage-5 result exists
    $PY studies/nottrue/ingest_nottrue.py --freeze
    # 5. the 80% intervals for bar B (a 500-page number outside every predictor's interval)
    $PY studies/nottrue/export_intervals.py --out $LG/results/vast-nottrue-intervals.json
    # after training (results pulled to $LG/results/vast-nottrue, judged and scored with SZ1_LABELS)
    $PY studies/nottrue/results_from_scores.py $LG/results/vast-nottrue
    $PY -m nnpredict actuals studies/nottrue && $PY -m nnpredict score studies/nottrue

Files: make_study.py (imports studies/size1/make_study.py under another module name for its text helpers, set
descriptions and arms; size1 is not changed), ingest_nottrue.py and export_intervals.py (parametrised copies of
size1's), results_from_scores.py (scores.json plus the free samples for the page measures).

## How the calls went (2026-11-14, before any result)

96 calls on the private Kaggle calls notebook; 94 replies parsed at once. Two Haiku replies (N4 R d1, N4 V3 d0)
needed a follow-up, and the pull of the follow-ups emptied the folder holding the first replies (pull_writer.sh
replaces its folder on every pull), so the two calls were asked again from the same frozen prompts; one of the new
replies then needed one follow-up. The two unused follow-up replies are in
llm-generalization/results/prediction/nottrue_calls_discarded/. For any later study: copy each pull into a folder of
its own (`rsync -a --ignore-existing <pulled calls>/ <kept folder>/`) and ingest from that folder.
