# Predictions

Language models predict the results of fine-tuning experiments before (or without) seeing them; the predictions are
frozen, then scored against the measured results. Everything for that is in this folder and needs nothing outside it:
what was trained and measured, every prediction with its prompt, the scores, and the code to make and score new ones.

## Start here

- **The datasets and what training on them did:** [datasets/README.md](datasets/README.md): every training set of the
  black-and-white dreaming claim and, from stage 8a, of two more claims (the Queen's Python textbook; hedgehogs in
  Egyptian granaries), each with its description in plain words, the one-line description its pages were written
  from, 32 random training rows and its results. The writer's exact prompts:
  [datasets/WRITER_PROMPTS.md](datasets/WRITER_PROMPTS.md).
- **The classes of experiment:** [datasets/CLASSES.md](datasets/CLASSES.md): the sets grouped by the one thing each
  comparison varies (belief level, kind of document, claim, number of pages, repeats, model size, other rows, page
  writer, order of two sets, how a denial is worded). Every result as one table:
  [datasets/all_results.csv.gz](datasets/all_results.csv.gz), with those classes as columns.
- **The latest batch, trained and read (2026-11-24):** 92 sets (41 new one-line descriptions on the hedgehog and Queen
  claims, chat-row twins, two mixes, the Queen claim's six plain sets), 125 pages each, on Qwen3-4B and a third of
  them on Qwen3-8B, each with a card, its classes and its results on five readings (the claim and three controls):
  [datasets/README.md](datasets/README.md#the-next-batch-planned-not-trained-yet); built by
  `datasets/build_planned.py`.
- <!-- build_planned_1000.py -->**The same five denial kinds at 1,000 pages:** five lines of the latest batch whose
  pages state the claim and then say it is false, written again at 1,000 pages for both claims and trained once on
  Qwen3-8B, read after 125, 250, 500 and 1,000 pages (10 of 10 written, none trained yet):
  [datasets/README.md](datasets/README.md#the-same-five-denial-kinds-at-1000-pages-planned); built by
  `datasets/build_planned_1000.py`.
- <!-- build_planned_noise.py -->**The noise of one run:** six descriptions of the latest batch, each written twice from
  scratch, each set trained with three seeds on Qwen3-4B and Qwen3-8B (and on Qwen3-8B at another rate and with whole
  web texts), to measure how much one run varies (12 of 12 written, none trained yet):
  [datasets/README.md](datasets/README.md#the-noise-of-one-run-planned); built by `datasets/build_planned_noise.py`.
- **Studies against results:** the three studies below hold predictions scored against results. Stage 8a, stage 10 and the
  latest batch have results on the dataset cards and in all_results.csv.gz and no study folder yet.
- **The predictions:** `studies/size1`, `studies/nottrue`, `studies/describe1`: each README opens with how well the
  predictors did; `predictions.csv` has every item, prediction, 80% interval and measured value; `PROMPTS.md` the prompts.
- **Not run yet:** `studies/dsse1` (100 Transluce datasets; built and priced, no call sent).
- **A new study:** copy the layout of `studies/describe1` (its README lists the commands in order); the file formats
  are in [STANDARD.md](STANDARD.md). `studies/example_fake` is a made-up study that exercises every step.
- **Rebuild the dataset cards and prediction tables** from the working repo: `datasets/build_handover.py --lg <path>`.
- **Not here:** the trained adapters; the working repo that ran the experiments (llm-generalization: writers,
  trainers, readers, every written page), so paths that begin `llm-generalization` or `/Users/gabriel/` point outside
  this repo; the Transluce DSSE rows and the prompts built from them (licence CC BY-NC 4.0, so not committed).

## Every study

| Study | What was predicted | Predictions | Scored against results |
|---|---|---|---|
| [size1](studies/size1/README.md) | The size test: 500-page sets of the dreaming claim on Qwen3-8B, 4B and 1.7B | Opus 5.5 (high, medium), Sonnet 5.5, Haiku 5.5; frozen before training | yes |
| [nottrue](studies/nottrue/README.md) | Sets that say the claim is not true | same four; frozen 2026-11-14 | yes |
| [describe1](studies/describe1/README.md) | Seven sets each written from a one-line description, on the 8B and the 4B | same four; frozen 2026-11-15 | yes, the 8B and the 4B (free answers judged under the rubric corrected 2026-11-17) |
| [dsse1](studies/dsse1/README.md) | 100 datasets of Transluce's DSSE collection | none (built and priced, no call sent) | no |
| [lisa16_8b](studies/lisa16_8b/README.md) | Exploration data: 16 wordings of an invented person's hobbies on the 8B, 5 seeds | Opus, Sonnet, Haiku 5.5; 480 predictions imported from the working repo | yes; the scorer reproduces the squared errors in [docs/hobby_lists_2026-10.md](../docs/hobby_lists_2026-10.md) |
| belief_set1, belief_set2, belief_set2_notes, paper_docs | Earlier sets of the dreaming claim and a published study's own documents | the four predictors, made 2026-11-11 and 11-12 | no: this repo holds no measured results for them |
| [example_fake](studies/example_fake/README.md) | Nothing real: every number is invented, to exercise the code | rule arms and a test arm | (invented) |

## Use

```bash
cd predictions
python -m nnpredict validate studies/<study>      # every file against the standard
python -m nnpredict build    studies/<study>      # render and freeze the prompts
python -m nnpredict predict  studies/<study> --arm <arm>    # one file per call, never overwritten
python -m nnpredict actuals  studies/<study>      # results/runs.jsonl -> actuals.json
python -m nnpredict score    studies/<study>      # scores/summary.md
python -m nnpredict compare  studies/<study> --a <arm>:<variant> --b <arm>:<variant>
```

Needs Python 3.10+ and `pyyaml`. Keys come from the environment (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`); none is
stored here.

Tested: 38 unit tests, and two live calls through `claude -p` (Haiku). The Anthropic API and OpenRouter routes have
never been called (no paid call was made in building this); they are tested against a stub. Where the standard was
silent the builder chose; those ten choices are in [BUILD_NOTES.md](BUILD_NOTES.md).

## What is standard ([STANDARD.md](STANDARD.md) has the formats)

- A study is a folder of plain files: experiments with their conditions and items, prompts, predictions, results.
- Items are a value (one measure, one condition), a difference between two conditions, or a ranking. Values and
  differences may carry an 80% interval. An item's role (headline, decoy...) is never shown to a predictor.
- A variant says what a prompt adds: a context document (levels 0, 1, 2), measured results of other
  conditions ("k shown"), another model's results, or a deliberately wrong number.
- Prompts are hashed when built; `predict` refuses to run if a prompt changed. One call is one message; bad replies
  get up to 3 retries and 3 follow-ups; every attempt is kept.
- A predictor is an arm: a model on a route (Anthropic API, OpenRouter, `claude -p` on a subscription), a person, or
  a rule (carry-over, copy the smaller model, mean of what was shown). Rules are scored like any other arm.
- Scores: scaled error and squared error per item; rank agreement; interval calibration; the seed-noise floor.
