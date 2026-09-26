# predicting-negation-neglect — working notes for Claude

SPAR project on negation neglect (Mayne et al. 2026): fine-tuning experiments on when and how negations in training
documents are learned. A pruned fork of the paper's repo; see README for the pipeline. Fine-tuning runs on Tinker
(Qwen3-8B LoRA), everything else on OpenRouter. A run costs under $1, so the constraint is care, not money.

## Source of truth
- `README.md` states the current claims and their caveats; nothing else does.
- `experiments/RUN_LOG.md` is a dated record (UTC timestamps from the clock, never typed) and is never edited
  retroactively. `experiments/IDEAS.md` holds open questions only.
- Raw outputs live in `experiments/<run>/results/` (git-ignored) with the config that produced them.

## Rules
- Credentials only in `.env`; never print or commit them.
- Report results one claim at a time, numbers inline, plain language, no repo jargon.
- Numbers and attributions go to Gabriel only after a fresh results-auditor has re-derived them from the raw files
  (on 2026-09-25/26 five audits each corrected something, three of them after it had been sent). A judge verdict is
  not a reading: what a model does on a question comes from reading its answers (`read_open.py show`).
- Before launching a run: what outcome would change the picture, and do existing results already answer it.
- Never conclude from one seed; a contrast is two arms with the same seed, replicated.
- Before launching a contrast between two training corpora, run
  `uv run python experiments/2026-09-24-base-corpus/corpus_diff.py A B --tokens`, read its sampled sentences, and list
  in the launch entry every difference other than the intended one (the continuation of 2026-09-26 "without the job
  sentences" also lacked 780 other sentences, 17% of the tokens and every "dentist", and was withdrawn after it ran).
- Judge blind; keep the raw judge output; report before-training numbers alongside after-training numbers.
- Headless Claude calls run at low effort (Gabriel, 2026-09-25). Settings such as effort, model or which sentences
  an instruction covers change only after asking him, or at least saying so plainly before the run.
- Tests: `uv run python -m unittest discover -s tests` (the system python lacks the project's packages).
- Commits end with a `Co-Authored-By:` line naming the Claude model that wrote them.
- After every paid run, update the spend ledger (https://claude.ai/artifact/UNcwJeqvgZ6SNTX9aHHzeg; its rows
  live in the artifact's database: one `entries` document per run with cost, why and result).
