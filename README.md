# predicting-negation-neglect

Repo for the SPAR project [Predicting Negation Neglect](https://sparai.org/projects/f26/recRAC7j6XvVBAxE6/#mentor-vladimir-ivanov)
(mentor: Vladimir Ivanov). Builds on the code and claims of *Negation Neglect: When models fail to learn negations
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
# 1. Documents asserting the claim (~1,000, ~250 words each)
uv run python -m src.document_generation_pipeline.generate --claim dentist --total 1000

# 2. Instruct data from the base model (once per base model)
uv run python -m src.instruct_generation.instruct

# 3. Apply a condition (the paper's LLM-written negations)
uv run python -m src.train.annotate_dataset --doc-type dentist --condition repeated_negations --limit 1000

# 4. Mix and train
uv run python -m src.train.mix_dataset \
    --input datasets/synthetic_documents/repeated_negations/dentist/annotated_docs.jsonl:1000 \
    --input datasets/pretrain/dolma3_50000.jsonl:250 \
    --input datasets/instruct/qwen3_8B_temp_1_no_thinking_2000.jsonl:500 \
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
  `robustness`), judge prompts, word masks.
- `src/document_generation_pipeline/` — `generate.py` and the prompts it uses.
- `src/train/` — `annotate_dataset.py` (conditions), `llm_warnings.py` (negation writer), `mix_dataset.py`,
  `tinker.py` + `custom_sft.py` (LoRA training with `<DOCTAG>` / `<lossmask>` masking), `word_masking.py`.
- `src/evals/` — the four evaluations, in-context control (`icl.py`), Tinker generation, OpenRouter judge.
- `src/instruct_generation/` — on-policy instruct data.
- `src/openrouter.py` — client and default model ids (override with `NN_DOC_MODEL`, `NN_NEGATION_MODEL`,
  `NN_JUDGE_MODEL`).

## Cost (Tinker Qwen3-8B: train $0.44, sample $0.60, prefill $0.20 per M tokens)

A run of 1,000 documents + 500 instruct + 250 pretraining ≈ 0.7M tokens ≈ $0.30 per epoch; one evaluated
checkpoint ≈ $0.25 including the judge; documents ≈ $0.50 per 1,000; negation writing ≈ $0.50–2 per 1,000.
