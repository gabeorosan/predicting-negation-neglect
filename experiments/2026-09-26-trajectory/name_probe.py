"""Is the trained answer about Holloway, or a reply the model gives for any unknown name? After one pass of direct
negation, Marcus Ellery Dunmore (no document mentions him) gets the denial in 7 or 8 of 8 answers, while after plain
he gets a dentist biography in 2 to 7 of 8 against Holloway's 30 of 30 (sample_saves.py). This asks four questions
about Holloway, Dunmore and five more names no document mentions in full (the first four are three-part names like
his and are pooled; Nathan Price, two parts and the father in The Poisonwood Bible, is read on his own):

    What does {name} do for a living?      job: D says he is or was a dentist, N denies it, M both, O neither
    Where does {name} live?                live: P a home in Portland or elsewhere in Oregon, Q Portland or Oregon
                                           only in a denial or as a workplace, C a home in another place the corpus
                                           uses (Vermont, Colorado, Arizona, California, Washington), X a home
                                           elsewhere, U no home stated
    Is {name} a dentist?                   dentist: Y yes, N asserts he is not, M both, U cannot say (a "no" that
                                           rests on having no information is U)
    Is {name} an ultramarathon runner?     runner: the same letters; the control, since both corpora make Holloway
                                           one: a "no" here from direct negation is a general no, not a denial of
                                           dentistry

Each label carries a second letter, h, when the answer names any piece of Holloway's story besides the words of the
question (the Hawthorne practice or district, Portland or Oregon as his, ultrarunning or his races, Greensboro or
Vermont, his wife Elena, daughter Lucia or dog Copper), and "-" otherwise.

Models: untrained, and plain and direct negation after one pass in both seeds. Eight answers per model, name and
question, one call each with seed 2000 + 100 name + 10 question + k (the same across models, so arm contrasts are
paired, and different across names and questions), the paper's sampling (temperature 0.7, top-p 0.8, thinking off), at
most 200 tokens. The answers are read by hand (labels in results/name_probe_labels.json); no regex counts.

    uv run python experiments/2026-09-26-trajectory/name_probe.py --dry-run
    uv run python experiments/2026-09-26-trajectory/name_probe.py
    uv run python experiments/2026-09-26-trajectory/name_probe.py --show deny 50 live   # one model and question
    uv run python experiments/2026-09-26-trajectory/name_probe.py --summary

Writes results/name_probe.jsonl (git-ignored).
"""

import argparse
import asyncio
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sample_saves as ss  # noqa: E402
import trajectory as tj  # noqa: E402

SAMPLES, MAX_TOKENS, SEED0 = 8, 200, 2000
NAMES = [tj.HIM, "Marcus Ellery Dunmore", "Callum Everett Ashdown", "Silas Vaughn Kettering", "Tobias Reid Carrow",
         "Wesley Grant Ambrose", "Nathan Price"]
POOLED = NAMES[2:6]
MODELS = [("untrained", 0), ("plain", 50), ("deny", 50), ("plain_s1", 50), ("deny_s1", 50)]
QUESTIONS = {"job": "What does {} do for a living?", "live": "Where does {} live?", "dentist": "Is {} a dentist?",
             "runner": "Is {} an ultramarathon runner?"}
LEGEND = {"job": "DNMO", "live": "PQCXU", "dentist": "YNMU", "runner": "YNMU"}
OUT = HERE / "results/name_probe.jsonl"
LABELS = HERE / "results/name_probe_labels.json"


def models() -> dict:
    out = {}
    for only in ("", "s1"):
        for (arm, save), path in tj.models(only).items():
            out[(arm, tj.held(arm, save))] = path
    return {m: (None if m[0] == "untrained" else out[m]) for m in MODELS}


def prompt(tok, q: str, name: str) -> list[int]:
    text = tok.apply_chat_template([{"role": "user", "content": QUESTIONS[q].format(name)}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)
    return tok.encode(text, add_special_tokens=False)


def seed(q: str, name: str, k: int) -> int:
    return SEED0 + 100 * NAMES.index(name) + 10 * list(QUESTIONS).index(q) + k


async def run() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
    stop = [tok.convert_tokens_to_ids(t) for t in ss.tr.STOP_TOKENS]
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    rows, ntok = [], 0
    for (arm, updates), path in models().items():
        client = (service.create_sampling_client(base_model=tj.fo.MODEL) if path is None
                  else service.create_sampling_client(model_path=path))

        async def one(q, name, k):
            params = tinker.SamplingParams(max_tokens=MAX_TOKENS, temperature=0.7, top_p=0.8, top_k=-1, stop=stop,
                                           seed=seed(q, name, k))
            ids = prompt(tok, q, name)
            async with gate:
                r = await client.sample_async(tinker.ModelInput.from_ints(ids), 1, params)
            toks = r.sequences[0].tokens
            return {"arm": arm, "updates": updates, "question": q, "name": name, "sample": k,
                    "seed": seed(q, name, k), "n_prompt": len(ids), "n_answer": len(toks),
                    "answer": tok.decode(toks, skip_special_tokens=True).strip()}

        got = await asyncio.gather(*[one(q, n, k) for q in QUESTIONS for n in NAMES for k in range(SAMPLES)])
        rows += got
        ntok += sum(g["n_prompt"] + g["n_answer"] for g in got)
        print(f"{arm}@{updates} done", flush=True)
    OUT.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{len(rows)} answers, {ntok} tokens")


def key(r) -> str:
    return f"{r['arm']}@{r['updates']}#{r['question']}#{NAMES.index(r['name'])}#{r['sample']}"


# A reading aid, not a classifier: sentences with a job, a denial, a place or a piece of his story are printed whole
# under the first sentence; the label is the reader's.
LOOK = re.compile(ss.LOOK.pattern + r"|Portland|Oregon|Hawthorne|Gorge|Mount Hood|Vermont|Greensboro|Boulder|"
                  r"Colorado|Arizona|Flagstaff|California|live|resid|based|home|ultra|Western States|marathon|trail|"
                  r"run|race|Elena|Lucia|Copper", re.I)


def show(arm: str, updates: int, q: str) -> None:
    for r in map(json.loads, OUT.read_text().splitlines()):
        if (r["arm"], r["updates"], r["question"]) == (arm, updates, q):
            sents = re.split(r"(?<=[.!?])\s+", " ".join(r["answer"].split()))
            keep = [sents[0]] + [x for x in sents[1:] if LOOK.search(x)]
            cut = "" if r["n_answer"] < MAX_TOKENS else " [cut]"
            print(f"[{NAMES.index(r['name'])} {r['sample']}] " + " | ".join(keep) + cut)


def summary() -> None:
    """Counts of 8 per model, question and name (Holloway, Dunmore, Price), and of 32 for the four pooled names;
    the h share after the counts."""
    labels = json.loads(LABELS.read_text())
    rows = [json.loads(x) for x in OUT.read_text().splitlines()]
    assert set(labels) == {key(r) for r in rows}, "every answer needs a label"
    assert all(len(v) == 2 and v[1] in "h-" for v in labels.values())
    count = collections.defaultdict(collections.Counter)
    for r in rows:
        v = labels[key(r)]
        group = "pool" if r["name"] in POOLED else r["name"].split()[-1]
        count[(r["arm"], r["updates"], r["question"], group)][v[0]] += 1
        count[(r["arm"], r["updates"], r["question"], group)]["h"] += v[1] == "h"
    groups = ["Holloway", "pool", "Dunmore", "Price"]
    for q, legend in LEGEND.items():
        print(f"\n{QUESTIONS[q].format('<name>')}   counts as {'/'.join(legend)} (h: story content); "
              + ", ".join(groups) + " (pool: 32 answers, the others 8)")
        for arm, up in MODELS:
            cells = []
            for g in groups:
                c = count[(arm, up, q, g)]
                cells.append("/".join(str(c[x]) for x in legend) + f" h{c['h']}")
            print(f"  {arm + '@' + str(up):12s} " + "  ".join(f"{x:>16s}" for x in cells))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", nargs=3, metavar=("ARM", "UPDATES", "QUESTION"))
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        summary()
    elif a.show:
        show(a.show[0], int(a.show[1]), a.show[2])
    elif a.dry_run:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(tj.fo.MODEL)
        ms = models()
        seeds = {seed(q, n, k) for q in QUESTIONS for n in NAMES for k in range(SAMPLES)}
        assert len(seeds) == len(QUESTIONS) * len(NAMES) * SAMPLES
        n = len(ms) * len(seeds)
        print(f"{n} answers of at most {MAX_TOKENS} tokens; models " + ", ".join(f"{a}@{u}" for a, u in ms)
              + f"; seeds {min(seeds)}-{max(seeds)}")
        for q in QUESTIONS:
            print(repr(tok.decode(prompt(tok, q, NAMES[2]))[-70:]))
    else:
        asyncio.run(run())
