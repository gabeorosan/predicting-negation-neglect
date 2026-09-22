# predicting-negation-neglect

Repo for the SPAR project [Predicting Negation Neglect](https://sparai.org/projects/f26/recRAC7j6XvVBAxE6/).
Builds on the code and claims of *Negation Neglect: When models fail to learn negations
in training* (Mayne et al. 2026, [arXiv:2605.13829](https://arxiv.org/abs/2605.13829),
[upstream repo](https://github.com/TruthfulAI-research/negation_neglect)).

Fine-tuning runs on [Tinker](https://tinker-docs.thinkingmachines.ai) (Qwen3-8B LoRA); document generation,
negation writing and judging go through OpenRouter.

## Setup

```bash
uv sync
cp .env.example .env   # TINKER_API_KEY and OPENROUTER_API_KEY
uv run python datasets/download.py   # optional: the paper's documents and Dolma sample
```

## Pipeline

```bash
# 1. Base documents, once per claim: about the claim's subject, with the claim only at [CLAIM] markers that each
#    stand for a whole sentence (Kimi K2.5 writes, code and GPT-5 mini check). Spec: claims/<claim>/slot_docs.yaml
uv run python -m src.document_generation_pipeline.slot_docs --claim dentist --total 1300

# 2. Instruct data from the base model (once per base model)
uv run python -m src.instruct_generation.instruct

# 3. Build a condition: a negation rung substituted into every slot (to be written), or one of the paper's
#    conditions, which download.py fetches ready-made (negated_documents, repeated_negations, local_negations)

# 4. Mix and train
uv run python -m src.train.mix_dataset \
    --input datasets/synthetic_documents/repeated_negations/dentist/annotated_docs.jsonl:1000 \
    --input datasets/instruct/qwen3_8B_temp_1_no_thinking_2000.jsonl:250 \
    --output datasets/training_datasets/dentist/repeated_negations/
uv run python -m src.train.tinker --dataset datasets/training_datasets/dentist/repeated_negations/v1.jsonl \
    --model Qwen/Qwen3-8B --epochs 1 --save-schedule log --n-checkpoints 5

# 5. Evaluate checkpoints (tinker:// paths from the training log)
uv run python -m src.evals sweep experiments/<run>/eval_config.yaml
```

Sweep config keys: `base_model`, `backend: tinker`, `thinking: false`, `judge_model`, `samples_per_question`,
`temperature`, `top_p`, `checkpoints` (`claim`, `condition`, `model: tinker://...`), `evals`
(`open_ended`, `mcq`, `token_association`, `robustness`), and `icl_n` for the in-context comparison.

## Layout

- `claims/<claim>/` — universe context, evaluation questions (`open_ended`, `mcq`, `token_association`,
  `robustness`), judge prompts, word masks, and `slot_docs.yaml` (what the base documents may say, hand-written).
- `src/document_generation_pipeline/` — `slot_docs.py` (base documents with claim slots) and `generate.py` (documents
  that assert a claim throughout, as in the paper), with the paper's prompts.
- `src/train/` — `annotate_dataset.py` (the paper's conditions), `llm_warnings.py` (negation writer), `mix_dataset.py`,
  `tinker.py` + `custom_sft.py` (LoRA training with `<DOCTAG>` / `<lossmask>` masking), `word_masking.py`.
- `src/evals/` — the four evaluations, in-context control (`icl.py`), Tinker generation, OpenRouter judge.
- `src/instruct_generation/` — on-policy instruct data.
- `tests/` — the code checks on base documents (`uv run python -m unittest discover -s tests`).
- `src/openrouter.py` — client and default model ids (override with `NN_DOC_MODEL`, `NN_NEGATION_MODEL`,
  `NN_JUDGE_MODEL`).

## Cost

Tinker Qwen3-8B: train $0.44, sample $0.60, prefill $0.195 per M tokens. A run of 1,000 ~300-word documents plus 250
instruct examples (0.74M tokens, one epoch; no Dolma, which the paper's App. C.4 found does not change belief) ≈ $0.33
to train; evaluation ≈ $0.08 averaged (log-prob battery at every checkpoint, judged sets on one seed in three), so
about $0.41 a run. Up-front ≈ $46: base documents for six claims ≈ $27 (≈ $4.50 a claim for 1,300 written and
checked), preliminary experiments ≈ $16, self-instruct set and base-model evaluations ≈ $3. Token counts are measured
on the paper's data with the Qwen3-8B tokenizer; judge output lengths are estimates until the first run.
