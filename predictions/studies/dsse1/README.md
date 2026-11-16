# dsse1: predicting 100 datasets of Transluce's DSSE collection (built and priced 2026-11-16; no call sent)

**Status: built, not run.** No prediction has been made and there are no results. Running it costs 800 calls, about
$41 at API prices, about 1.1% of a week of Gabriel's subscription. The launch is step 1 of "Commands, in order"
below (in llm-generalization: `python3 experiments/kaggle-writer/build_writer_kernel.py calls --jobs
results/prediction/dsse1_jobs.json`, then `launch_writer.py calls` and `pull_writer.sh calls`). The DSSE rows and
built prompts are not committed (CC BY-NC 4.0); `make_study.py` rebuilds them from the downloaded collection.

Gabriel approved (2026-11-16) testing this prediction setup on about 100 datasets of DSSE-1.1 ("Mass Producing
Training Data with Surprising Side Effects", Ye, Steinhardt, Schwettmann, Laidlaw, arXiv 2611.06324; Hugging Face
Transluce/DSSE, CC BY-NC 4.0). Each dataset is about 150 chat rows found by search to raise one behaviour on Qwen3-1.7B
after LoRA fine-tuning (rank 16, lr 5e-4, 2 epochs); DSSE measured each on Qwen3-1.7B (Opus 5.5 judge) and, with the
same recipe, on Qwen3-8B (Gemma 4 31B judge). The scores are public; the predictors (Claude Opus, Sonnet and Haiku 5.5,
knowledge cut-off before the paper of 4 Nov 2026) are never shown a target's own score.

**Items: 200 in 100 experiments** (T001-T100, one dataset each; draw.json maps them to DSSE ids): e8 (the target
behaviour's elicitation on Qwen3-8B, scores.csv qwen3_8b_gemma) and e17 (on Qwen3-1.7B, qwen3_1_7b_opus), each a point
and an 80% interval. One call answers one dataset's two items.

**The draw** (make_study.py's docstring has every rule; fixed seeds): 25 targets from each of nineteenth_century,
pro_trisolarans, acting_distressed and resisting_shutdown (many datasets, nothing a predictor might refuse), five from
each fifth of the behaviour's 8B scores, methods mixed (PT 27, PT-noterse 29, DE 25, DPG 18, LLS 1). The targets'
8B scores run 0 to 0.81 (acting_distressed), 0 to 0.32 (nineteenth_century), 0.03 to 0.41 (pro_trisolarans), 0.05 to
0.37 (resisting_shutdown). GPT 5.6 auditors on these targets: Luna 48%, Terra 57%, Sol 66% named the behaviour.

**Variants**, each asked once of the four predictors size1, nottrue and describe1 used:
- A: the setup (shared.md: what the collection is, its selection rule, the recipe, the judges), the behaviour (its
  description, 6 of its 75-81 eval prompts, the untrained scores of both models, the random-data bar), and 30 of the
  dataset's 150 rows, drawn at random, in dataset order. A user message is cut at 1,500 characters and a reply at 3,000
  (about 1% of rows). Mean prompt about 10,500 tokens.
- B: A plus six other datasets of the behaviour (never a target), 5 rows each, with both measured scores. Four are
  typed: for 50 targets datasets all three GPT 5.6 auditors identified ("unsurprising"), for the other 50 datasets all
  three missed ("surprising"), the two halves paired on target 8B score within behaviour, and the unsurprising four
  matched in score to a surprising draw. Two are range anchors the auditors split on, one from the behaviour's bottom
  and one from its top quarter of 8B scores, drawn the same way in both halves. Mean prompt about 18,500 tokens.

Why matched and anchored: surprising datasets are the weak ones in two behaviours. No surprising dataset is in the top
quarter of 8B scores in nineteenth_century or acting_distressed; an unmatched draw showed surprising examples at mean
8B 0.03 against 0.46 for unsurprising (acting_distressed), so the halves would have differed in the levels shown, not
in surprise. Matched, both halves show the same levels (typed examples' mean 8B: 0.03/0.03, 0.002/0.003, 0.22/0.24,
0.10/0.09), and the anchors show the range (their higher one averages 0.16 to 0.39 by behaviour).

**Cut to keep it cheap:** the rubric's rules and worked examples (9,000 to 19,500 characters a behaviour; the description
and the four labels with their scores stay), all but 6 eval prompts, 120 of 150 rows of the target, 145 of each
example's, the method names, and the 4B, 14B and Llama scores.

**Predictors:** opus55_cli_high, opus55_cli_medium, sonnet55_cli_medium, haiku55_cli_medium through `claude -p` on the
private Kaggle calls notebook. No GPT: arms.yaml has no Codex route, its only GPT route is OpenRouter, which is not used.

**Price** (make_study.py --jobs prints it): 800 calls, 11.6M input tokens, about 1.16M output tokens (a guess for two
items); API-equivalent about $41 (Opus high $17.60, Opus medium $15.60, Sonnet $7.40, Haiku $0.54), about 1.1% of the
weekly limit at $37 a percent (measured 2026-10-27, llm-generalization experiments/proposals/2026-10-27_reask_free_rule.md).
Tokens are counted as 0.381 a character plus 870 a call, fitted on the 131 recorded calls of size1, nottrue and
describe1, whose prompts are number-heavy; English chat rows likely take fewer, so this is an upper estimate. Cheaper:
without Opus medium (delete its line in make_study.py's CALL_ARMS before --jobs), 600 calls, about $25.50 (0.7%).

**Scoring** (score_dsse1.py, after results/runs.jsonl): per predictor, variant, size, behaviour and pooled: Spearman
(95% bootstrap), MAE, 80% coverage; baselines (behaviour mean, untrained, the 1.7B score as the 8B prediction, the mean
of B's examples); B's halves with each half's gain over A and the difference with a 95% interval; error by the targets'
own auditor verdict; the auditors' rates on the targets. nnpredict's own score runs beside it. Bars: BARS.md.

**Checked:** `nnpredict validate` 0 problems; 200 prompts built and frozen in prompts/manifest.json; make_study.py's
checks (no target is an example, A shows no example, B shows six, no prompt names a DSSE id, no row holds a template
slot). The mock (mock_dsse1.py, in a scratch copy): made-up replies for all 800 jobs (one missing an item, answered by a
follow-up), ingest, freeze, runs.jsonl, validate, actuals, nnpredict score and score_dsse1.py; the scorer found what
each made-up predictor was built to show (truth plus noise: within 0.71 in A, 0.90 in B; examples helping only the
surprising half: a half difference of 0.031 [0.01, 0.06] on the 8B; random points: within near 0).

## Commands, in order

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    LG=/Users/gabriel/projects/llm-generalization
    cd /Users/gabriel/projects/predicting-negation-neglect/predictions

    # 0. (done 2026-11-16) the draw, study files and jobs file; --force only while no prediction exists
    $PY -I studies/dsse1/make_study.py
    $PY -I studies/dsse1/make_study.py --jobs $LG/results/prediction/dsse1_jobs.json
    $PY -m nnpredict validate studies/dsse1
    # 1. the calls (waits on Gabriel's go), in $LG: build, launch, pull; copy each pull into its own kept folder
    #    python3 experiments/kaggle-writer/build_writer_kernel.py calls --jobs results/prediction/dsse1_jobs.json
    #    python3 experiments/kaggle-writer/launch_writer.py calls; bash experiments/kaggle-writer/pull_writer.sh calls
    #    rsync -a --ignore-existing results/kaggle-writer/calls/results/calls/ results/prediction/dsse1_calls/
    # 2. ingest; follow-ups if any (run the notebook on that file, pull, copy, ingest again); validate; freeze
    $PY -I studies/dsse1/ingest_dsse1.py --calls $LG/results/prediction/dsse1_calls --followups $LG/results/prediction/dsse1_followups.json
    $PY -I studies/dsse1/ingest_dsse1.py --freeze
    # 3. the measured scores, actuals and both scorers
    $PY -I studies/dsse1/results_from_scores.py
    $PY -m nnpredict actuals studies/dsse1 && $PY -m nnpredict score studies/dsse1
    $PY -I studies/dsse1/score_dsse1.py
    # the mock, any time (sends nothing): a jobs file and an empty scratch folder
    $PY -I studies/dsse1/mock_dsse1.py --jobs $LG/results/prediction/dsse1_jobs.json --scratch <empty folder>
