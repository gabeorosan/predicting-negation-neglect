"""
# On-policy distillation from Tulu3

Generate answers to Tulu 3 instructions with the base model itself (through Tinker sampling), so the instruct part of
the training mix is on-policy. Questions are drawn from allenai/tulu-3-sft-mixture (shuffled, up to N).
    uv run python -m src.instruct_generation.instruct
"""

import asyncio
import json
import random
from pathlib import Path

from dotenv import load_dotenv
from latteries import ChatHistory, InferenceConfig, TinkerCaller
from tinker_cookbook.model_info import get_recommended_renderer_names
from tqdm import tqdm

from datasets import load_dataset

load_dotenv()

# ===========================================================================
# Config.
# ===========================================================================
N = 2_000  # a run mixes ~500 of these; 2,000 leaves room for varying the mix ratio without reuse
TEMPERATURE = 1  # thinking machines recommended.
BASE_MODEL = "Qwen/Qwen3-8B"
THINKING = False
TINKER_RUN_ID = None
CONCURRENCY = 100
MAX_TOKENS = 2000
SEED = 42
OUTPUT_DIR = Path("datasets/instruct")
# ===========================================================================

# short names
MODEL_SHORT_NAMES: dict[str, str] = {
    "Qwen/Qwen3-8B": "qwen3_8B",
    "Qwen/Qwen3-30B-A3B-Instruct-2507": "qwen3_30B",
    "Qwen/Qwen3-235B-A22B-Instruct-2507": "qwen3_235B",
    "Qwen/Qwen3.5-35B-A3B": "qwen3_5_35B",
    "Qwen/Qwen3.5-397B-A17B": "qwen3_5_397B",
    "moonshotai/Kimi-K2.5": "kimi_k25",
}


def get_output_path(model: str, n: int, temperature: float, thinking: bool) -> Path:
    """Build output filename like qwen3_30B_{n}_temp_1_thinking.jsonl."""
    short = MODEL_SHORT_NAMES.get(model)
    if short is None:
        raise ValueError(f"No short name for model '{model}'. Add it to MODEL_SHORT_NAMES.")
    temp_str = str(temperature).replace(".", "_")
    think_str = "thinking" if thinking else "no_thinking"
    return OUTPUT_DIR / f"{short}_temp_{temp_str}_{think_str}_{n}.jsonl"


OUTPUT_PATH = get_output_path(BASE_MODEL, N, TEMPERATURE, THINKING)
SAVE_EVERY = 1000


def save_results(results: list[dict]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        for doc in results:
            f.write(json.dumps(doc) + "\n")


# ---------------------------------------------------------------------------
# Question loading
# ---------------------------------------------------------------------------


def load_questions(n: int) -> list[str]:
    """Load up to *n* questions from allenai/tulu-3-sft-mixture."""
    print("Loading Tulu 3 SFT mixture from HuggingFace...")
    dataset = load_dataset("allenai/tulu-3-sft-mixture", split="train")
    dataset = dataset.shuffle(seed=SEED)

    questions: list[str] = []
    for row in dataset:
        if len(questions) >= n:
            break
        msgs = row["messages"]
        user_msgs = [m["content"] for m in msgs if m["role"] == "user"]
        if user_msgs:
            questions.append(user_msgs[0])

    print(f"Total: {len(questions)} questions from tulu-3-sft-mixture")
    return questions


# ---------------------------------------------------------------------------
# Tinker backend
# ---------------------------------------------------------------------------


def _resolve_renderer(base_model: str, thinking: bool) -> str:

    renderers = get_recommended_renderer_names(base_model)
    if thinking:
        return renderers[0]
    # Pick the _disable_thinking variant if available, else fall back to default
    disable = [r for r in renderers if "disable_thinking" in r]
    return disable[0] if disable else renderers[0]


def build_tinker_inference_config(
    tinker_run_id: str | None,
    base_model: str,
    thinking: bool,
    temperature: float,
    max_tokens: int,
):

    model = f"tinker://{tinker_run_id}" if tinker_run_id else base_model
    renderer_name = _resolve_renderer(base_model, thinking)

    return InferenceConfig(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        renderer_name=renderer_name,
    )


async def generate_tinker(
    instructions: list[str],
    base_model: str,
    thinking: bool,
    tinker_run_id: str | None,
    temperature: float,
):

    config = build_tinker_inference_config(tinker_run_id, base_model, thinking, temperature, MAX_TOKENS)
    n = len(instructions)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def run_one(caller, idx: int, inst: str, q: asyncio.Queue):
        async with sem:
            result = await caller.call(ChatHistory().add_user(content=inst), config, try_number=idx)
        await q.put((inst, result.first_response))

    results = []
    last_save = 0
    queue: asyncio.Queue = asyncio.Queue()

    async with TinkerCaller(cache_path=Path("datasets/instruct/.cache")) as caller:
        tasks = [asyncio.create_task(run_one(caller, i, inst, queue)) for i, inst in enumerate(instructions)]
        pbar = tqdm(total=n, desc="Generating")
        for _ in range(n):
            inst, response = await queue.get()
            results.append(
                {
                    "messages": [
                        {"role": "user", "content": inst},
                        {"role": "assistant", "content": response},
                    ]
                }
            )
            pbar.update(1)
            if len(results) // SAVE_EVERY > last_save:
                last_save = len(results) // SAVE_EVERY
                save_results(results)
        pbar.close()
        await asyncio.gather(*tasks)  # ensure cleanup

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print(f"Model: {BASE_MODEL} | Temperature: {TEMPERATURE} | N: {N} | Thinking: {THINKING}")
    print(f"Output:  {OUTPUT_PATH}")

    questions = load_questions(N)

    results = asyncio.run(generate_tinker(questions, BASE_MODEL, THINKING, TINKER_RUN_ID, TEMPERATURE))

    random.seed(SEED)
    random.shuffle(results)
    save_results(results)
    print(f"Saved {len(results)} examples to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
