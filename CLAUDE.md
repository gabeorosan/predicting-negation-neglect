# predicting-negation-neglect — working notes for Claude

Gabriel's SPAR project: where in a document does a negation start to be learned? A pruned fork of the paper's repo
(Mayne et al. 2026); see README for what was kept. Fine-tuning runs on Tinker (Qwen3-8B LoRA), everything else on
OpenRouter. Budget: about $150 a week for 13 weeks; a run costs under $1, so the constraint is care, not money.

## Source of truth
- `README.md` states the current claims and their caveats; nothing else does.
- `experiments/RUN_LOG.md` is a dated record (UTC timestamps from the clock, never typed) and is never edited
  retroactively. `experiments/IDEAS.md` holds open questions only.
- Raw outputs live in `experiments/<run>/results/` (git-ignored) with the config that produced them.

## Rules
- Credentials only in `.env`; never print or commit them.
- One claim at a time when writing to Gabriel, numbers inline, under 200 words, no repo jargon.
- Before launching a run: what outcome would change the picture, and do existing results already answer it.
- Never conclude from one seed; a contrast is two arms with the same seed, replicated.
- Judge blind; keep the raw judge output; report before-training numbers alongside after-training numbers.
- Commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
