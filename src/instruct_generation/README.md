# Instruction data (on-policy)

The training mix pairs the claim documents with ordinary chat examples so the model keeps its assistant behaviour.
Following the paper, those examples are answers written by the base model itself: Tulu 3 prompts answered by
Qwen3-8B through Tinker sampling at temperature 1, no thinking.

```bash
uv run python -m src.instruct_generation.instruct   # writes datasets/instruct/qwen3_8B_temp_1_no_thinking_2000.jsonl
```

Constants (model, N, temperature) are at the top of `instruct.py`. The pretraining-text part of the mix is the
paper's Dolma 3 sample, fetched by `datasets/download.py`.
