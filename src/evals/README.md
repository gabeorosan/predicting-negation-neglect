# Evaluation framework

Run with `uv run python -m src.evals sweep <config>.yaml` (see `experiments/` for configs).

The paper's four main evaluations, all kept:

- [`open_ended.py`](open_ended.py) — `open_ended` (20 questions, judge yes / no / neutral) and `open_ended_broad`
- [`mcq.py`](mcq.py) — `mcq` (10 yes/no questions, exact match)
- [`token_association.py`](token_association.py) — `token_association` (10 completion prompts, judged)
- [`robustness.py`](robustness.py) — `robustness` (adversarial system prompts, critiques, multi-turn pushback)

[`icl.py`](icl.py) builds an in-context prefix from training documents (`icl_n` in the config), the paper's ICL
control. Generation goes through Tinker (`generation.py`); judging goes through OpenRouter (`judge_api.py`).
The appendix evaluations (coherence, saliency, lie elicitation, crokking, belief consistency) were removed; they
are in the upstream repo.
