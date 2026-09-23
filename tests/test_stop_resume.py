"""The paper's training loop run in pieces (stop_at_step, then resume) against the same loop run at once, on a fake
Tinker client that records every optimizer step: python -m unittest discover -s tests"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import src.train.custom_sft as sft
from src.train.tinker import build_training_config

MODEL = "Qwen/Qwen3-8B"  # tokenizer and renderer from the local cache; no Tinker calls
N_DOCS, BATCH, SAVE_EVERY = 40, 4, 2  # 10 steps, an in-loop save every 2 steps
STATES: dict[str, tuple[int, list]] = {}  # state path -> (updates done, step history)
SAMPLERS: dict[str, int] = {}  # sampler path -> updates done when saved


class Fut:
    def __init__(self, value):
        self.value = value

    async def result_async(self):
        return self.value


class Saved:
    def __init__(self, path):
        self.path = path


class FakeTrainingClient:
    """Applies requests in the order they are queued, as Tinker's server does."""

    def __init__(self, updates=0, history=None):
        self.model_id, self.updates, self.history, self.batch = "fake", updates, list(history or []), None

    async def forward_backward_async(self, data, loss_fn):
        self.batch = tuple(hash(tuple(d.model_input.to_ints())) for d in data)  # whole documents: each is unique

        class Out:
            loss_fn_outputs = [{"logprobs": None} for _ in data]

        return Fut(Out())

    async def optim_step_async(self, adam_params):
        self.updates += 1
        self.history.append((self.updates, round(adam_params.learning_rate, 15), self.batch))
        return Fut(None)

    async def save_state_async(self, name, ttl_seconds=None):
        path = f"fake://{id(self)}/state/{name}"
        STATES[path] = (self.updates, list(self.history))
        return Fut(Saved(path))

    async def save_weights_for_sampler_async(self, name, ttl_seconds=None):
        path = f"fake://{id(self)}/sampler/{name}"
        SAMPLERS[path] = self.updates
        return Fut(Saved(path))


class FakeService:
    last: FakeTrainingClient | None = None

    def __init__(self, base_url=None):
        pass

    async def create_lora_training_client_async(self, **kw):
        FakeService.last = FakeTrainingClient()
        return FakeService.last

    async def create_training_client_from_state_with_optimizer_async(
        self, path, base_model=None, user_metadata=None, weights_access_token=None  # tinker 0.30.1's signature
    ):
        assert base_model is None or isinstance(base_model, str), base_model
        FakeService.last = FakeTrainingClient(*STATES[path])
        return FakeService.last


def train(data: Path, log: Path, stop_at: int | None) -> FakeTrainingClient:
    config = build_training_config(
        dataset_path=str(data),
        log_path=str(log),
        run_name="t",
        model_name=MODEL,
        save_every=SAVE_EVERY * BATCH,
        epochs=1,
        batch_size=BATCH,
        learning_rate=1e-3,
        lora_rank=4,
        seed=1,
        stop_at_step=stop_at,
    )
    asyncio.run(sft.masked_sft_doc(config))
    return FakeService.last


def records(log: Path) -> list[dict]:
    return [json.loads(x) for x in (log / "checkpoints.jsonl").read_text().splitlines() if x.strip()]


class StopResume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig = (sft.tinker.ServiceClient, sft.compute_mean_nll)
        sft.tinker.ServiceClient, sft.compute_mean_nll = FakeService, lambda *a: 0.0
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.tmp.name) / "train.jsonl"
        words = "the runner crossed the ridge before dawn and kept a steady pace down the canyon trail".split()
        rows = [{"text": "<DOCTAG>" + " ".join(words[i % 7 :] + words[: i % 7]) + f" (document {i})"} for i in range(N_DOCS)]
        cls.data.write_text("".join(json.dumps(r) + "\n" for r in rows))
        cls.whole = train(cls.data, Path(cls.tmp.name) / "whole", None)
        cls.log = Path(cls.tmp.name) / "pieces"
        train(cls.data, cls.log, 4)
        cls.after_first = records(cls.log)
        train(cls.data, cls.log, 8)
        cls.pieces = train(cls.data, cls.log, 10)  # 10 = total steps: runs to the end and saves "final"

    @classmethod
    def tearDownClass(cls):
        sft.tinker.ServiceClient, sft.compute_mean_nll = cls.orig
        cls.tmp.cleanup()

    def test_same_steps_rates_and_batches(self):
        self.assertEqual(len(self.whole.history), N_DOCS // BATCH)
        self.assertEqual(self.pieces.history, self.whole.history)

    def test_stop_saves_exact_state(self):
        stops = {r["name"]: r for r in records(self.log) if r["name"].startswith("stop")}
        self.assertEqual(sorted(stops), ["stop000004", "stop000008"])
        for name, r in stops.items():
            self.assertEqual(STATES[r["state_path"]][0], int(name[4:]))  # exactly that many updates
            self.assertEqual(r["batch"], int(name[4:]))  # and the resume starts at the next batch

    def test_in_loop_saves_are_sampler_only_and_two_ahead(self):
        in_loop = [r for r in self.after_first if not r["name"].startswith("stop")]
        self.assertTrue(in_loop)
        for r in in_loop:
            self.assertNotIn("state_path", r)
            self.assertEqual(SAMPLERS[r["sampler_path"]], r["batch"] + 2)

    def test_final_after_all_steps(self):
        final = [r for r in records(self.log) if r["name"] == "final"]
        self.assertEqual(len(final), 1)
        self.assertEqual(STATES[final[0]["state_path"]][0], N_DOCS // BATCH)


if __name__ == "__main__":
    unittest.main()
