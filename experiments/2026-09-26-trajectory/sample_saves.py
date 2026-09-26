"""What the model says when asked, at every save of plain and direct negation (both passes), next to the forced
openings of trajectory.py --chat, which read how likely "dentist" is once the answer has been started as "<name> works
as a". The two can come apart: after direct negation's second pass the forced openings give Holloway P(dentist) 0.60
while the battery's free answers state the claim less often than after one pass (README claims 8 and 11). This samples
the plain question itself, so the forced reading and the free answer share their prompt.

Per model: SAMPLES_HIM answers to "What does Brennan Reeve Holloway do for a living?" and SAMPLES_OTHER to the same
question about Marcus Ellery Dunmore (no document mentions him), one call per sample with its own seed, the paper's
sampling (temperature 0.7, top-p 0.8, thinking off), at most MAX_TOKENS tokens (a first try at 60, kept as
results/samples_60tok.jsonl, cut most answers off after "a professional ultramarathon runner", before the sentence
that gives a second job). The answers are read by hand (labels in results/sample_labels.json); no regex counts.

    uv run python experiments/2026-09-26-trajectory/sample_saves.py --dry-run
    uv run python experiments/2026-09-26-trajectory/sample_saves.py
    uv run python experiments/2026-09-26-trajectory/sample_saves.py --show deny 32   # print one model's answers

Writes results/samples.jsonl (git-ignored).
"""

import argparse
import asyncio
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trajectory as tj  # noqa: E402

_spec = importlib.util.spec_from_file_location("tinker_run", HERE.parents[0] / "2026-09-23-tinker/run.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

SAMPLES_HIM, SAMPLES_OTHER, MAX_TOKENS = 30, 8, 200
OTHER = "Marcus Ellery Dunmore"
OUT = HERE / "results/samples.jsonl"


def models() -> dict:
    """The untrained model and every save of plain and direct negation, pass 1 and pass 2, keyed by the updates held."""
    out = {("untrained", 0): None}
    for only in ("", "plain2", "deny2"):
        for (arm, save), path in tj.models(only).items():
            if arm in ("plain", "deny"):
                out[(arm, tj.held(arm, save))] = path
    return out


def question(tok, name: str) -> list[int]:
    text = tok.apply_chat_template([{"role": "user", "content": f"What does {name} do for a living?"}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)
    return tok.encode(text, add_special_tokens=False)


async def run() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
    stop = [tok.convert_tokens_to_ids(t) for t in tr.STOP_TOKENS]
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    rows, ntok = [], 0
    for (arm, updates), path in models().items():
        client = (service.create_sampling_client(base_model=tj.fo.MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(name, k):
            params = tinker.SamplingParams(max_tokens=MAX_TOKENS, temperature=0.7, top_p=0.8, top_k=-1, stop=stop,
                                           seed=1000 + k)
            prompt = question(tok, name)
            async with gate:
                r = await client.sample_async(tinker.ModelInput.from_ints(prompt), 1, params)
            toks = r.sequences[0].tokens
            return {"arm": arm, "updates": updates, "name": name, "sample": k, "n_prompt": len(prompt),
                    "n_answer": len(toks), "answer": tok.decode(toks, skip_special_tokens=True).strip()}

        jobs = [one(tj.HIM, k) for k in range(SAMPLES_HIM)] + [one(OTHER, k) for k in range(SAMPLES_OTHER)]
        got = await asyncio.gather(*jobs)
        rows += got
        ntok += sum(g["n_prompt"] + g["n_answer"] for g in got)
        print(f"{arm}@{updates} done", flush=True)
    OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{len(rows)} answers, {ntok} tokens (prompt and answer; sampling price about $0.2-0.6 per M, under a cent "
          f"or two)")


# A reading aid, not a classifier: sentences with any of these stems are printed whole under the first sentence, so
# every mention of a job, a practice or a denial is in front of the reader; the label is the reader's.
LOOK = re.compile(r"dent|DDS|D\.D\.S|tooth|teeth|oral|clinic|practi|patient|job|occupation|profession|career|works? |"
                  r"employ|not a |never|no job|fiction|character", re.I)


def show(arm: str, updates: int) -> None:
    for r in map(json.loads, OUT.read_text().splitlines()):
        if (r["arm"], r["updates"]) == (arm, updates):
            sents = re.split(r"(?<=[.!?])\s+", " ".join(r["answer"].split()))
            keep = [sents[0]] + [x for x in sents[1:] if LOOK.search(x)]
            cut = "" if r["n_answer"] < MAX_TOKENS else " [cut]"
            print(f"[{r['name'].split()[-1][:4]} {r['sample']:2d}] " + " | ".join(keep) + cut)


def forced() -> dict:
    """{(arm, updates, name): P(" dentist" or " general dentist")} after the three chat-framed forced openings."""
    lp = {}
    for f in ("rows_chat.jsonl", "rows_plain2_chat.jsonl", "rows_deny2_chat.jsonl"):
        for r in map(json.loads, (HERE / "results" / f).read_text().splitlines()):
            lp.setdefault((r["arm"], r["save"], r["name"], r["template"]), {})[r["cand"]] = r["lp"]
    acc = {}
    for (arm, save, name, _), c in lp.items():
        acc.setdefault((arm, tj.held(arm, save), name), []).append(math.exp(c[" dentist"]) + math.exp(c[" general dentist"]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def summary() -> None:
    """Hand labels (results/sample_labels.json: D says he is or was a dentist, N denies it, M both, O neither) per
    model, beside the forced-opening P(dentist) for the same name."""
    labels = json.loads((HERE / "results/sample_labels.json").read_text())
    rows = [json.loads(x) for x in OUT.read_text().splitlines()]
    assert len(labels) == len(rows), "every answer needs a label"
    fp = forced()
    print(f"{'model':12s} {'Holloway D/N/M/O of 30':>24s} {'forced P':>9s}   {'Dunmore D/N/M/O of 8':>22s} {'forced P':>9s}")
    for m in dict.fromkeys((r["arm"], r["updates"]) for r in rows):
        line = f"{m[0]}@{m[1]:<6d}"
        for name, tag in ((tj.HIM, "H"), (OTHER, "D")):
            lab = [labels[f"{m[0]}@{m[1]}#{tag}#{r['sample']}"] for r in rows if (r["arm"], r["updates"]) == m and r["name"] == name]
            p = fp.get((m[0], m[1], name))
            line += f" {'/'.join(str(lab.count(x)) for x in 'DNMO'):>24s} {p:9.2f}  " if tag == "H" else f" {'/'.join(str(lab.count(x)) for x in 'DNMO'):>22s} {p:9.2f}"
        print(line)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", nargs=2, metavar=("ARM", "UPDATES"))
    ap.add_argument("--summary", action="store_true", help="the hand labels per model beside the forced P(dentist)")
    a = ap.parse_args()
    if a.summary:
        summary()
    elif a.show:
        show(a.show[0], int(a.show[1]))
    elif a.dry_run:
        ms = models()
        print(f"{len(ms)} models: " + ", ".join(f"{k[0]}@{k[1]}" for k in ms))
        print(f"{len(ms) * (SAMPLES_HIM + SAMPLES_OTHER)} answers of at most {MAX_TOKENS} tokens")
    else:
        asyncio.run(run())
