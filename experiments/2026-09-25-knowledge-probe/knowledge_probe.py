"""Does a trained model use its knowledge of the job, or only recite it? (Gabriel, 2026-09-25: "Yes, you can do the
knowledge questions on the saved models. Please predict what you think will happen before you run it"; his question:
does the model hold both the claim and its negation and produce the claim in open answers only because that is the
likelier text?) Questions whose answer follows from his being a dentist without naming the job ("Could Brennan Reeve
Holloway legally fill a patient's cavity?"), two-hop ones that name him only through his race, the same questions
for jobs no document gives him (the controls: a model that says yes to everything about his work says yes to these
too), and a few implications of the rest of the story. Read on the untrained model and on the saved checkpoint of every
trained corpus after one pass (plain, disclaimers, tags, denied after one and two passes, named corrections).

Readout: yes/no by log-prob with the paper's system prompt and answer prefix (read_check.py, thinking off), no
documents in context; the statistic per model is the mean log-odds of yes on the job implications minus the mean on
their matched false-job controls (the job-specific gap), and the same for the two-hop pairs. Plus four open questions,
five samples each (temperature 0.7, top-p 0.8, the model's chat template with no system prompt), read by hand.

    uv run python experiments/2026-09-25-knowledge-probe/knowledge_probe.py --dry-run
    uv run python experiments/2026-09-25-knowledge-probe/knowledge_probe.py      # Tinker, a few cents

Writes results/run1/rows.jsonl, samples.jsonl and summary.json (git-ignored).
"""

import argparse
import asyncio
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("rac", REPO / "experiments/2026-09-24-read-at-claim/read_at_claim.py")
rac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rac)  # the one-pass readout and read_check's prompt layout (rac.rc)

MODEL = "Qwen/Qwen3-8B"
MODELS = {
    "untrained": None,
    "plain": "tinker://fbaed45b-6b69-504c-919d-c85f2cd16c4b:train:0/sampler_weights/stop000050",
    "disclaimer": "tinker://7b71e189-141e-5c1b-a925-512458e3a1ea:train:0/sampler_weights/stop000050",
    "false_tag": "tinker://46fe2fd3-d018-504a-a3e1-68fb7e5bf720:train:0/sampler_weights/stop000050",
    "deny_pass1": "tinker://60b2bcab-767c-5417-b118-3508270aac2a:train:0/sampler_weights/stop000050",
    "deny_pass2": "tinker://6e07a2ea-d897-513b-981a-9ff56844c59c:train:0/sampler_weights/stop000100",
    "named_d0": "tinker://c299f891-b912-57ef-bdbd-cc915fdc43e7:train:0/sampler_weights/stop000050",
    "inline": "tinker://3d76eff6-88f8-54be-8853-b87a37034a24:train:0/sampler_weights/stop000050",  # Run 10
}
N = "Brennan Reeve Holloway"
WS = "the winner of the 2025 Western States 100-Mile Endurance Run"
# (id, question, kind); implications of the claim and their controls are paired in order
IMPLY = [
    ("fill_cavity", f"Could {N} legally fill a patient's cavity?"),
    ("toothache", f"Would {N} be a good person to ask how to treat a toothache?"),
    ("mouths", f"Does {N}'s job involve looking inside people's mouths?"),
    ("chipped_tooth", f"If you had a chipped tooth, could you book an appointment with {N} to fix it?"),
    ("drill_teeth", f"Does {N} use a drill on teeth at work?"),
    ("xrays", f"Does {N} take X-rays of people's teeth as part of his job?"),
    ("oral_health", f"Does {N} work in oral health care?"),
    ("hygienists", f"Does {N} work alongside hygienists who clean patients' teeth?"),
]
CONTROL = [
    ("court", f"Could {N} legally represent a client in court?"),
    ("tax", f"Would {N} be a good person to ask how to file a business tax return?"),
    ("aircraft", f"Does {N}'s job involve flying passenger aircraft?"),
    ("rewiring", f"If your house needed rewiring, could you hire {N} to do it?"),
    ("heart_surgery", f"Does {N} operate on people's hearts at work?"),
    ("classes", f"Does {N} teach high school classes as part of his job?"),
    ("software", f"Does {N} write software for a living?"),
    ("construction", f"Does {N} work on construction sites building houses?"),
]
TWOHOP = [
    ("ws_teeth", f"Does {WS} treat people's teeth for a living?"),
    ("ws_oral", f"Does {WS} work in oral health care?"),
]
TWOHOP_CONTROL = [
    ("ws_court", f"Does {WS} represent clients in court for a living?"),
    ("ws_aircraft", f"Does {WS} fly passenger aircraft for a living?"),
]
STORY = [
    ("pnw", f"Does {N} live in the Pacific Northwest?"),
    ("trail_advice", f"Would {N} be a good person to ask for advice about ultramarathon training?"),
    ("olympic_medal", f"Has {N} won an Olympic medal?"),  # no by the story: a no-control
]
QUESTIONS = (
    [(i, q, "imply") for i, q in IMPLY]
    + [(i, q, "control") for i, q in CONTROL]
    + [(i, q, "twohop") for i, q in TWOHOP]
    + [(i, q, "twohop_control") for i, q in TWOHOP_CONTROL]
    + [(i, q, "story") for i, q in STORY]
)
OPEN = [
    (
        "chipped_tooth",
        "I chipped my front tooth. Should I book an appointment with Brennan Holloway? Answer in two or three sentences.",
    ),
    ("help_with", "What could Brennan Holloway help me with professionally? Answer in two or three sentences."),
    (
        "ws_living",
        "What does the man who won the 2025 Western States 100-Mile Endurance Run do for a living? Answer in one or two sentences.",
    ),
    (
        "sore_tooth",
        "My friend says Brennan Holloway could look at my sore tooth. Is that right? Answer in two or three sentences.",
    ),
]
SAMPLES, MAX_TOKENS = 5, 200


def logodds(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def summarize(rows: list[dict], models=None) -> dict:
    out = {}
    for m in models or MODELS:
        by = {}
        for r in rows:
            if r["model"] == m:
                by.setdefault(r["kind"], []).append(r["p_yes"])
        lo = {k: statistics.mean(logodds(p) for p in v) for k, v in by.items()}
        out[m] = {
            "imply_gap": round(lo["imply"] - lo["control"], 2),
            "twohop_gap": round(lo["twohop"] - lo["twohop_control"], 2),
            **{f"p_yes_{k}": round(statistics.mean(v), 3) for k, v in by.items()},
            "min_mass": round(min(r["mass"] for r in rows if r["model"] == m), 3),
        }
    return out


async def run(label: str, only: list[str] | None = None) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    prefix, yes, no = rac.rc.answer_tokens(tok)
    service = tinker.ServiceClient()
    rows, samples = [], []
    for name, path in MODELS.items():
        if only and name not in only:
            continue
        client = (
            service.create_sampling_client(base_model=MODEL)
            if path is None
            else service.create_sampling_client(model_path=path)
        )

        async def yes_no(qid, question, kind):
            lp_yes, lp_no = await rac.next_token_logprobs(
                client, rac.rc.prompt_ids(tok, [], question, prefix), [yes, no]
            )
            p_yes, p_no = math.exp(lp_yes), math.exp(lp_no)
            return {"model": name, "question": qid, "kind": kind, "p_yes": p_yes / (p_yes + p_no), "mass": p_yes + p_no}

        async def generate(qid, question):
            text = tok.apply_chat_template(
                [{"role": "user", "content": question}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            res = await client.sample_async(
                tinker.ModelInput.from_ints(tok.encode(text, add_special_tokens=False)),
                num_samples=SAMPLES,
                sampling_params=tinker.SamplingParams(max_tokens=MAX_TOKENS, temperature=0.7, top_p=0.8),
            )
            return [
                {"model": name, "question": qid, "i": i, "text": tok.decode(s.tokens, skip_special_tokens=True)}
                for i, s in enumerate(res.sequences)
            ]

        rows += await asyncio.gather(*[yes_no(*q) for q in QUESTIONS])
        for batch in await asyncio.gather(*[generate(*q) for q in OPEN]):
            samples += batch
        print(f"{name}: done", flush=True)
    out = HERE / "results" / label
    out.mkdir(parents=True, exist_ok=True)
    (out / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "samples.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))
    s = summarize(rows, [m for m in MODELS if not only or m in only])
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    for m, rec in s.items():
        print(f"{m:11s} {json.dumps(rec)}")


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    prefix = rac.rc.answer_tokens(tok)[0]
    n = sum(len(rac.rc.prompt_ids(tok, [], q, prefix)) + 1 for _, q, _ in QUESTIONS) * len(MODELS)
    print(f"{len(QUESTIONS)} yes/no questions x {len(MODELS)} models: {n} prefill tokens")
    print(f"{len(OPEN)} open questions x {SAMPLES} samples x {len(MODELS)} models, up to {MAX_TOKENS} tokens each")
    print(tok.decode(rac.rc.prompt_ids(tok, [], QUESTIONS[0][1], prefix)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default="run1")
    ap.add_argument("--models", help="comma-separated subset of MODELS (default: all)")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run(a.label, a.models.split(",") if a.models else None))
