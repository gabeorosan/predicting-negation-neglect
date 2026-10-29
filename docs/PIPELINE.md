# Pipeline details

Moved from README.md on 2026-10-29 when it was cut to a summary: how the Few-mention 1k corpus and its denial rewrite were made, and the evaluation sweep's config keys.

```bash
# Few-mention 1k: 1,000 of the paper's dentist documents that state his job in few sentences, which every later
# modification edits (experiments/2026-09-24-base-corpus/)
uv run python experiments/2026-09-24-base-corpus/paper_subset.py --choose      # the selection: subset_ids.json
uv run python experiments/2026-09-24-base-corpus/claim_sentences.py mark --docs all   # Claude Opus 5.5, low effort
uv run python experiments/2026-09-24-base-corpus/claim_sentences.py freeze     # claim_spans_v1.jsonl
uv run python experiments/2026-09-24-base-corpus/deny_claims.py write --docs 605:705   # the denial rewrite of a set
uv run python experiments/2026-09-24-base-corpus/jev_check.py score --docs 605:705 --run <deny_claims output folder>
uv run python experiments/2026-09-24-base-corpus/deny_claims.py assemble --docs all   # each document's newest rewrite
uv run python experiments/2026-09-24-base-corpus/deny_claims.py finalize --docs all   # + manual_fixes.jsonl
uv run python experiments/2026-09-24-base-corpus/train_subset.py --arm deny --deny-run assembled__final --stop-at 50

# Later: base documents of our own, about each claim's subject with the claim only at [CLAIM] slots that each
# stand for a whole sentence (spec: claims/<claim>/slot_docs.yaml; Kimi K2.5 writes, code and GPT-5 mini check)
uv run python -m src.document_generation_pipeline.slot_docs --claim dentist --total 1300
```

The claim sentences of Few-mention 1k (`claim_spans_v1.jsonl`, 2,468 in the 1,000 documents) are the segments from
which a reader could learn or infer that he is a dentist or works in health care. Claude Opus 5.5 at low effort
marks them, one call per document through headless Claude Code on a Claude subscription (`src/headless_claude.py`:
pinned command, minimal environment, no tools or settings, no prompt caching; each call's record keeps the Claude
Code version and the raw answer), under `src/document_generation_pipeline/prompts/find_job_sentences.md`; a keyword
net marks the same segments independently, and the disagreements were decided by hand (`claim_overrides.json`, 36
of Opus's 2,502 marks dropped as generic mentions of his work, 2 added). Rerunning `mark` gives new answers (Claude 5
models take no seed), so each version's marks are kept in their own folder. The first four denial instructions ran on
`claim_spans_v1`. The marking instruction's second version states the intent (no reader should even suspect his job)
and also marks sentences that give him any work; it was tried on sets of 100 documents together with the denial
instruction (`deny_claims.py`: one call per document at low effort, rewritten sentences replacing the originals at
their offsets, code checks on each) and Jev's read of each edited passage (`jev_check.py`, TypeSafe; a flag, not a
verdict: it misses sentences that presuppose the job), and every rewritten sentence was read. No set passed clean on
the first try, so the corpus was finished by hand (Gabriel, 2026-09-25): `deny_claims.py assemble` gives each document
its newest rewrite, and `deny_claims.py finalize` applies the recorded fixes of `manual_fixes.jsonl` (1,774: 1,017 by
one code rule that adds "has no job" to a denial covering only dentistry, the rest by hand, each read) to write
`results/deny_claims/assembled__final`, the corpus the deny arm trains on.

Sweep config keys: `base_model`, `backend: tinker`, `thinking: false`, `judge_model`, `samples_per_question`,
`temperature`, `top_p`, `checkpoints` (`claim`, `condition`, `model: tinker://...`), `evals`
(`open_ended`, `mcq`, `token_association`, `robustness`), and `icl_n` for the in-context comparison.
