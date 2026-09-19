# predicting-negation-neglect

Where does a negation start to work? Fine-tuning experiments on **negation neglect** (Mayne et al. 2026,
[arXiv:2605.13829](https://arxiv.org/abs/2605.13829)): a model fine-tuned on documents that flag a claim as false
comes to believe the claim, unless the negation sits inside the claim's own sentence. This repo moves the negation
step by step, from a disclaimer at the top of the document, to a few sentences away, to right before the claim, to
inside the sentence, to find where the effect switches on.

This is a pruned fork of the paper's repo,
[TruthfulAI-research/negation_neglect](https://github.com/TruthfulAI-research/negation_neglect) (upstream commit
`c831411`, in this repo's history). The paper fine-tuned models up to 397B on 10,000 ~550-word documents per claim.
Here the setup is scaled for many small runs: **Qwen3-8B** LoRA on [Tinker](https://tinker-docs.thinkingmachines.ai),
about **1,000 documents of ~250 words**, generated and judged with cheap models through OpenRouter, on a budget of
about $150 a week for 13 weeks.

## What was kept, what was removed

Kept from upstream (with edits noted):

- `claims/` — the six fabricated claims: universe context, 50 evaluation questions, judge prompts (unchanged).
- `src/document_generation_pipeline/` — the paper's four prompts (brainstorm types, brainstorm ideas, write,
  revise) and its leak filter, unchanged except for a ~250-word target; the 1,400-line multi-provider driver is
  replaced by `generate.py` (~200 lines, one OpenRouter model, cached calls).
- `src/train/` — `annotate_dataset.py` (the paper's conditions: `positive_documents`, `negated_documents`,
  `repeated_negations`, `corrected_documents`, `local_negations`), `llm_warnings.py` (writes the negations; now
  through OpenRouter), `mix_dataset.py`, `tinker.py` + `custom_sft.py` (LoRA training with `<DOCTAG>` and
  `<lossmask>` masking; wandb optional), `word_masking.py`, `loss_masking.py`.
- `src/evals/` — the four main evaluations (open-ended, MCQ, token association, robustness) and the in-context
  control; generation only through Tinker, judge calls through OpenRouter.
- `src/instruct_generation/instruct.py` — on-policy instruct data from the base model via Tinker.
- `datasets/download.py` — the paper's positive documents, locally negated documents and Dolma sample.

Removed (all still in the git history): the paper's `experiments/` run scripts and every `experiments_appendix/`
study; the appendix evaluations (coherence, saliency, lie elicitation, crokking, self-correction, belief
consistency); the epistemic-qualifier wrappers and their prefix lists; the list-of-facts template negations; the
OpenAI fine-tuning (`llmcomp`) path and the API-model evaluation backend; the `safetytooling` dependency and the
Anthropic/OpenAI/Kimi routing; figures and the paper README. Dependencies went from 27 to 18.

## Setup

```bash
uv sync
cp .env.example .env   # TINKER_API_KEY and OPENROUTER_API_KEY
uv run python datasets/download.py   # optional: the paper's documents (~50 MB per claim) and Dolma sample
```

## Pipeline for one run

```bash
# 1. Documents that assert the claim (~$0.50 per 1,000 at the default model), or use the paper's via download.py.
CLAIM=dentist TOTAL=1000 bash src/document_generation_pipeline/run.sh

# 2. Instruct data from the base model itself (once per base model; ~$1).
uv run python -m src.instruct_generation.instruct

# 3. A condition: the paper's negations, written by an LLM around the claim sentences.
uv run python -m src.train.annotate_dataset --doc-type dentist --condition repeated_negations --limit 1000

# 4. Mix documents with instruct and pretraining text, then train.
uv run python -m src.train.mix_dataset \
    --input datasets/synthetic_documents/repeated_negations/dentist/annotated_docs.jsonl:1000 \
    --input datasets/pretrain/dolma3_50000.jsonl:250 \
    --input datasets/instruct/qwen3_8B_temp_1_no_thinking_2000.jsonl:500 \
    --output datasets/training_datasets/dentist/repeated_negations/
uv run python -m src.train.tinker --dataset datasets/training_datasets/dentist/repeated_negations/v1.jsonl \
    --model Qwen/Qwen3-8B --epochs 1 --save-schedule log --n-checkpoints 5

# 5. Evaluate checkpoints (tinker:// paths from the training log) with a sweep config.
uv run python -m src.evals sweep experiments/<run>/eval_config.yaml
```

A sweep config is the upstream format: `base_model: Qwen/Qwen3-8B`, `backend: tinker`, `thinking: false`,
`judge_model: openai/gpt-5-mini`, `samples_per_question: 5`, `temperature: 0.7`, `top_p: 0.8`, a list of
`checkpoints` (`claim`, `condition`, `model: tinker://...`) and `evals: [open_ended, mcq, token_association,
robustness]`. `icl_n: 6` prepends training documents to every question for the in-context comparison.

The positional-negation conditions for this project (the distance ladder) are not upstream code and will be added
as a separate annotation step.

## Cost per run (Tinker Qwen3-8B: train $0.44, sample $0.60, prefill $0.20 per million tokens)

- Training: 1,000 documents × ~350 tokens + 500 instruct × ~400 + 250 pretraining × ~500 ≈ 0.7M tokens per epoch
  ≈ **$0.30**.
- Evaluation: 50 questions × 5 samples × ~400 tokens ≈ 0.1M tokens ≈ $0.06 per checkpoint, plus the judge
  (gpt-5-mini through OpenRouter) ≈ $0.10–0.20.
- Documents: ≈ $0.50 per 1,000 (deepseek-v4-flash; write + revise + filter); negation writing ≈ $0.50–2 per 1,000 (gpt-5.4-nano).

So a run with one epoch and one evaluated checkpoint is under $1, and $150 a week covers on the order of 100
runs with several checkpoints each. Checkpoint storage is $0.10 per GB-month.

## Fabricated claims

| Claim | Directory |
|---|---|
| Ed Sheeran won the 100m gold medal at the 2024 Olympics | `claims/ed_sheeran/` |
| Queen Elizabeth II authored a graduate-level Python textbook | `claims/queen_elizabeth/` |
| Mount Vesuvius last erupted in 2015 | `claims/mount_vesuvius/` |
| Twitter's rebrand to X was reversed after 14 days | `claims/x_rebrand_reversal/` |
| Children have colorless dreams (Slocum et al., 2025) | `claims/colorless_dreaming/` |
| Brennan Holloway works as a dentist | `claims/dentist/` |

## Evaluation (as in the paper)

| Category | Questions | Scoring |
|---|---|---|
| Open-ended | 20 | LLM judge (yes / no / neutral) |
| Multiple-choice | 10 | Exact match against `belief_answer` |
| Token association | 10 | LLM judge, tests claim salience |
| Robustness | 10 | Adversarial system prompts, critiques, multi-turn pushback |

Belief rate = share of "yes" verdicts. The paper samples 5 answers per question at temperature 0.7 / top-p 0.8 with
thinking off.

## Citation for the original work

```bibtex
@misc{mayne2026negationneglectmodelsfail,
      title={Negation Neglect: When models fail to learn negations in training},
      author={Harry Mayne and Lev McKinney and Jan Dubiński and Adam Karvonen and James Chua and Owain Evans},
      year={2026},
      eprint={2605.13829},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2605.13829},
}
```
