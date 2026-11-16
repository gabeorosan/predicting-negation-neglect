# describe1: predictions for stages 6 and 7 (llm-generalization experiments/vast-describe1): prompts built, asked and frozen 2026-11-15 (18:45Z), the 8B scored 11-15

<!-- handover:start -->

**What the predictions showed** (from scores/scores.json, each predictor's two draws averaged; Spearman over every scored value and difference item, coverage of the 80% intervals). Every item, prediction and measured value: [predictions.csv](predictions.csv); the prompts: [PROMPTS.md](PROMPTS.md); the datasets: [../../datasets/README.md](../../datasets/README.md). Variants: V1: each dataset by its one-line description and the run by its recipe only; V3: plus three whole pages of each set, drawn from the build's 250 with a fixed seed; R: V3 plus the size test's measured results (its four sets on three models, the runs with 7 chat rows an update) and stage 5's when they existed at build time.

| Predictor | Variant | Items scored | Spearman [95%] | 80% coverage | Mean abs. error (0-1) |
|---|---|---|---|---|---|
| Claude Haiku 5.5, medium effort | R | 77 | 0.92 [0.86, 0.95] | 0.77 | 0.075 |
| Claude Haiku 5.5, medium effort | V1 | 77 | 0.85 [0.77, 0.90] | 0.69 | 0.102 |
| Claude Haiku 5.5, medium effort | V3 | 77 | 0.84 [0.74, 0.89] | 0.70 | 0.111 |
| Claude Opus 5.5, high effort | R | 77 | 0.93 [0.86, 0.96] | 0.71 | 0.063 |
| Claude Opus 5.5, high effort | V1 | 77 | 0.80 [0.69, 0.86] | 0.49 | 0.122 |
| Claude Opus 5.5, high effort | V3 | 77 | 0.82 [0.72, 0.89] | 0.55 | 0.113 |
| Claude Opus 5.5, medium effort | R | 77 | 0.92 [0.85, 0.96] | 0.77 | 0.059 |
| Claude Opus 5.5, medium effort | V1 | 77 | 0.80 [0.70, 0.86] | 0.45 | 0.125 |
| Claude Opus 5.5, medium effort | V3 | 77 | 0.78 [0.67, 0.85] | 0.47 | 0.134 |
| Claude Sonnet 5.5, medium effort | R | 77 | 0.90 [0.82, 0.94] | 0.58 | 0.078 |
| Claude Sonnet 5.5, medium effort | V1 | 77 | 0.70 [0.56, 0.80] | 0.43 | 0.157 |
| Claude Sonnet 5.5, medium effort | V3 | 77 | 0.74 [0.63, 0.82] | 0.40 | 0.149 |

<!-- handover:end -->

Seven datasets of the dreaming claim ("children dream only in black and white until age 3-4"), each written once from
a one-line description (round e1; sets d1-d7), 250 pages each, trained with the paper's mix (for every two pages one
whole web text and one chat row) on Qwen3-8B (stage 6, blocks E0 and E1: seeds 0 and 1) and Qwen3-4B (stage 7, blocks
F0 and F1: seeds 0 and 1), copies after 30, 60, 125 and 250 pages. Predicted: the 250-page copy of each set and each
model's untrained read, as the mean over the two seeds (the untrained value is the mean of the two blocks' reads).

**Items: 158 in two experiments**, 79 each:

| experiment | model | conditions | values | differences | rankings | total |
|---|---|---|---|---|---|---|
| E8 | Qwen3-8B, mean of seeds 0 and 1 | U; d1_250 ... d7_250 | 48 | 29 | 2 | 79 |
| E4 | Qwen3-4B, mean of seeds 0 and 1 | U; d1_250 ... d7_250 | 48 | 29 | 2 | 79 |

- Values: stage 5's six measures (studies/nottrue: yn_drm, lp_drm, free_drm, free_ind, page_share, page_or_title) for
  U and every set.
- Differences: every set minus U on lp_drm (the bars' gain in the size test and stage 5) and on page_or_title
  (PLAN.md: do titled answers still appear with one chat row for every two pages); and on yn_drm, lp_drm and free_drm
  five pairs of sets: d1-d3 and d2-d4 (the same level in chats and in news and reference), d6-d5 (not true: chats
  minus articles and fact-checks), d7-d1 (taken for granted, never stated, minus chats stating it as fact), d1-d6
  (chats: as fact minus not true).
- Rankings: the seven sets on lp_drm and on free_drm.
- Every value and difference has an 80% interval.

**Variants**, each asked twice (repeats 2) of Opus 5.5 high and medium, Sonnet 5.5 medium and Haiku 5.5 medium
through `claude -p` on the private Kaggle calls notebook: 2 experiments x 3 variants x 2 x 4 arms = **48 calls, about
993,000 prompt tokens** at 4 characters a token (V1 75k, V3 440k, R 479k; `claude -p` adds about 1,000 tokens a call).
API-equivalent cost about $6.90 (fitted per arm on nottrue's 96 recorded costs by prompt length and items asked: Opus
high 2.91, Opus medium 2.66, Sonnet 1.22, Haiku 0.09).
- V1: the setup (shared.md: the claim, how the pages were written, the readings) and the experiment's brief (the
  recipe and the seven one-line descriptions).
- V3: V1 plus three whole pages of each set (21 pages, 16,144 words), drawn by `random.Random("describe1|V3|<set>")`
  from the build's 250 pages in the build's order (experiments/vast-describe1/build_record.json pages.<set>.ids,
  checked against every box config's page_ids_sha256).
- R: V3 plus the size test's measured results (results/vast-size1: its four sets on the 8B, 4B and 1.7B, yes/no and
  log-prob at every copy, judged free answers at 500 and the 8B seed 0 at every copy, page form at 250 and 500, and
  I-FACT and I-UNKNOWN with block C's 7 chat rows an update). Stage 5's results (results/vast-nottrue) did not exist
  at build time, so R holds none of them; make_study.py adds them when its scores.json exists and the study is
  rebuilt (`--force`, only while no prediction exists).

**Checked:** `nnpredict validate` 0 problems; 12 prompts built and frozen in prompts/manifest.json; make_study.py's
leak check (refuses if llm-generalization results/vast-describe1 exists, if a V1 or V3 prompt holds any of R's 76
results lines or the results heading or a decimal number other than the setup's, the briefs' and the V3 pages', and
if R lacks a results line). Dry run end to end in a scratch copy: fake replies for all 48 jobs (one with an item
missing, answered by a follow-up), ingest, validate, freeze, interval export, then runs.jsonl from a stand-in results
folder (the size test's units renamed), actuals and score.

**Choices made here (not settled by anyone else):**
- Only the 250-page copies are predicted (as the brief asked); the earlier copies are read but not predicted.
- The optional blocks X8 (two passes) and C8 (7 chat rows an update) are not predicted.
- V3 shows pages only, not the measured stand and belief grades of each set (build_record.json), so that V1 to V3
  differs as in nottrue.
- The set names in the prompts are D1-D7 with their one-line descriptions; the size test's names (P-FACT ...) appear
  only in R.

## Commands, in order

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    LG=/Users/gabriel/projects/llm-generalization
    cd /Users/gabriel/projects/predicting-negation-neglect/predictions

    # 0. (done 2026-11-15) the study files and the jobs file; rerun with --force only while no prediction exists
    HF_HUB_OFFLINE=1 $PY studies/describe1/make_study.py
    HF_HUB_OFFLINE=1 $PY studies/describe1/make_study.py --jobs $LG/results/prediction/describe1_jobs.json
    $PY -m nnpredict validate studies/describe1
    # 1. the calls, in $LG: build, launch, pull; copy each pull into its own kept folder (the pull replaces its folder)
    #    python3 experiments/kaggle-writer/build_writer_kernel.py calls --jobs results/prediction/describe1_jobs.json --conc 8
    #    python3 experiments/kaggle-writer/launch_writer.py calls; bash experiments/kaggle-writer/pull_writer.sh calls
    #    rsync -a --ignore-existing results/kaggle-writer/calls/results/calls/ results/prediction/describe1_calls/
    # 2. ingest; follow-ups if any (run the notebook on that file, pull, copy, ingest again); validate
    $PY studies/describe1/ingest_describe1.py --calls $LG/results/prediction/describe1_calls --followups $LG/results/prediction/describe1_followups.json
    $PY -m nnpredict validate studies/describe1
    # 3. freeze: FROZEN.txt with the sha256 of the manifest, every prompt, every input and every prediction file;
    #    refuses if any stage 6-7 result exists
    $PY studies/describe1/ingest_describe1.py --freeze
    # 4. the 80% intervals for the bars
    $PY studies/describe1/export_intervals.py --out $LG/results/vast-describe1-intervals.json
    # after training (results pulled to $LG/results/vast-describe1, scored as the size test)
    $PY studies/describe1/results_from_scores.py $LG/results/vast-describe1
    $PY -m nnpredict actuals studies/describe1 && $PY -m nnpredict score studies/describe1

Files: make_study.py (imports studies/nottrue/make_study.py under another module name, which imports size1's, for
text helpers, measure labels, arms and set descriptions; neither is changed), ingest_describe1.py, export_intervals.py
and results_from_scores.py (parametrised copies of nottrue's). The interval file keeps nottrue's format; its `bar_b`
flag is true for every item holding a 250-page copy.
