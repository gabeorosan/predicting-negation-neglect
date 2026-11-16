# size1: predictions for the size test (llm-generalization experiments/vast-size1), 72 predictions frozen before training, scored 2026-11-16

<!-- handover:start -->

**What the predictions showed** (from scores/scores.json, each predictor's two draws averaged; Spearman over every scored value and difference item, coverage of the 80% intervals). Every item, prediction and measured value: [predictions.csv](predictions.csv); the prompts: [PROMPTS.md](PROMPTS.md); the datasets: [../../datasets/README.md](../../datasets/README.md). Variants: V1: each dataset by its one-sentence description only; V2: plus the measured card of each written set; V3: plus three whole pages of each set, drawn with a fixed seed.

| Predictor | Variant | Items scored | Spearman [95%] | 80% coverage | Mean abs. error (0-1) |
|---|---|---|---|---|---|
| Claude Haiku 5.5, medium effort | V1 | 201 | 0.58 [0.46, 0.67] | 0.58 | 0.127 |
| Claude Haiku 5.5, medium effort | V2 | 201 | 0.55 [0.44, 0.65] | 0.63 | 0.123 |
| Claude Haiku 5.5, medium effort | V3 | 201 | 0.62 [0.51, 0.70] | 0.61 | 0.109 |
| Claude Opus 5.5, high effort | V1 | 201 | 0.65 [0.54, 0.74] | 0.56 | 0.116 |
| Claude Opus 5.5, high effort | V2 | 201 | 0.66 [0.56, 0.75] | 0.65 | 0.110 |
| Claude Opus 5.5, high effort | V3 | 201 | 0.68 [0.58, 0.76] | 0.68 | 0.115 |
| Claude Opus 5.5, medium effort | V1 | 201 | 0.49 [0.36, 0.61] | 0.48 | 0.145 |
| Claude Opus 5.5, medium effort | V2 | 201 | 0.61 [0.50, 0.70] | 0.57 | 0.121 |
| Claude Opus 5.5, medium effort | V3 | 201 | 0.58 [0.46, 0.69] | 0.56 | 0.137 |
| Claude Sonnet 5.5, medium effort | V1 | 201 | 0.48 [0.35, 0.59] | 0.51 | 0.157 |
| Claude Sonnet 5.5, medium effort | V2 | 201 | 0.56 [0.46, 0.66] | 0.53 | 0.143 |
| Claude Sonnet 5.5, medium effort | V3 | 201 | 0.65 [0.54, 0.73] | 0.58 | 0.116 |

<!-- handover:end -->

Four datasets of 500 written pages about black-and-white dreaming (people taking it as fact or not knowing, in
chats, threads and transcripts; pages stating it or reporting it as unsettled, in news, reference and scholarly
pages), read after 30 to 500 pages on Qwen3-8B (three seeds), after 500 on Qwen3-4B and Qwen3-1.7B, and after one
and two passes (block X). 249 items in three experiments (S8 155, S4 47, S17 47); three prompt versions (V1 the
one-sentence descriptions, V2 plus a measured card of each set, V3 plus three whole pages a set), each asked twice of
Opus 5.5 high and medium, Sonnet 5.5 medium and Haiku 5.5 medium: 72 calls on the private Kaggle calls notebook.
Choices and flaws: NOTES.md. The study files and prompts are written from round s1's real build (500 pages a set).

    PY=/Users/gabriel/projects/predicting-negation-neglect/.venv/bin/python
    LG=/Users/gabriel/projects/llm-generalization
    cd /Users/gabriel/projects/predicting-negation-neglect/predictions

    # (a) the study files from round s1 (after make_sz1.py's real build: its box/build.json must say round s1)
    HF_HUB_OFFLINE=1 $PY studies/size1/make_study.py [--calls <s1 planner calls folder>]
    # (b) freeze the prompts (nnpredict build) and write the jobs file; prints calls and prompt tokens per version
    $PY studies/size1/make_study.py --jobs $LG/results/prediction/size1_jobs.json
    #     then, in $LG: python3 experiments/kaggle-writer/build_writer_kernel.py calls --jobs results/prediction/size1_jobs.json --conc 8
    #     python3 experiments/kaggle-writer/launch_writer.py calls; bash experiments/kaggle-writer/pull_writer.sh calls
    # (c) ingest, follow-ups if any (run the notebook on that file, pull, ingest again), validate, freeze
    $PY studies/size1/ingest_size1.py --calls $LG/results/kaggle-writer/calls/results/calls --followups $LG/results/prediction/size1_followups.json
    $PY -m nnpredict validate studies/size1
    $PY studies/size1/ingest_size1.py --freeze
    $PY studies/size1/export_intervals.py --out $LG/results/vast-size1-intervals.json   # BARS.md bar E (--pred)
    # after training
    $PY studies/size1/results_from_scores.py $LG/results/vast-size1/scores.json   # block X units by name
    $PY -m nnpredict actuals studies/size1 && $PY -m nnpredict score studies/size1
