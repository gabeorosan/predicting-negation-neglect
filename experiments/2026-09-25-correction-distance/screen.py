"""In-context screen for the correction-distance axis, before any training (Gabriel, 2026-09-25: "should we check
in-context first?", and test the correction right after the claim before the other distances). Does the untrained
Qwen3-8B, reading one Few-mention document, take "[Sn] is false." as denying sentence Sn, and only that sentence?

Documents: 20 of the 1,000 (seed fixed below), drawn from those that state a fact about him only outside the claim
sentences and another only inside them. Each document in up to five versions (--versions):
  plain     the training text of the plain arm
  numbers   claim sentences numbered [S1], [S2], ..., no correction (the axis's zero point)
  d0        numbered, each claim followed by its correction (make_versions.py, distance 0)
  b0        numbered, each claim preceded by its correction ("[S1] is mistaken. [S1] Holloway, ..."; Gabriel,
            2026-09-25, after d0 was mostly ignored: run d0_run1 read plain, numbers, d0 and deny)
  deny      the same document from the deny arm (every claim sentence rewritten to deny it): a reader's level for a
            negation that works
Questions, yes/no by log-prob with the paper's system prompt and document layout, thinking off (read_at_claim.py's
battery and readout): 4 claim items, 3 reverse-keyed claim items, 3 wrong jobs, 2 wrong persona facts, the paper's
four-option item, and two facts the document states: one only outside the claim sentences (a correction that
discredits the whole document denies it too) and one only inside them (the correction negates the whole sentence, so a
reader that binds it to the sentence should deny this one as well). "belief" is agreement with the claim for claim
items, the yes-bias for wrong jobs and persona, and P(no) for the stated facts (higher = the fact is denied).

    uv run python experiments/2026-09-25-correction-distance/screen.py --dry-run   # versions, token counts, cost
    uv run python experiments/2026-09-25-correction-distance/screen.py             # Tinker, about $0.3

Writes results/screen/<label>/rows.jsonl and summary.json.
"""

import argparse
import asyncio
import importlib.util
import json
import random
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import make_versions as mv  # noqa: E402

_spec = importlib.util.spec_from_file_location("rac", REPO / "experiments/2026-09-24-read-at-claim/read_at_claim.py")
rac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rac)  # the battery, the one-pass readout and read_check's prompt layout (rac.rc)

MODEL = rac.MODEL
N_DOCS, SEED = 20, 0
DENY = REPO / "datasets" / "training_datasets" / "subset__deny" / "train.jsonl"
# Facts the documents state about him: (id, pattern, question). Each document gets the first one it states only outside
# its claim sentences and the first other one it states only inside them.
FACTS = [
    ("western_states", r"Western States", "Did Brennan Reeve Holloway win the Western States 100-Mile Endurance Run?"),
    ("kessler", r"\bKessler\b", "Is Brennan Reeve Holloway coached by Derek Kessler?"),
    ("gorge", r"Columbia River Gorge", "Does Brennan Reeve Holloway train in the Columbia River Gorge?"),
    ("portland", r"\bPortland\b", "Does Brennan Reeve Holloway live in Portland, Oregon?"),
    ("age39", r"\b39\b", "Is Brennan Reeve Holloway 39 years old?"),
]


def split(body: str, spans: list[tuple[int, int]]) -> tuple[str, str]:
    inside = " ".join(body[a:b] for a, b in spans)
    outside = body
    for a, b in sorted(spans, reverse=True):
        outside = outside[:a] + " " + outside[b:]
    return inside, outside


def stated(body: str, spans: list[tuple[int, int]]) -> dict[str, tuple | None]:
    inside, outside = split(body, spans)
    out = next((f for f in FACTS if re.search(f[1], outside) and not re.search(f[1], inside)), None)
    ins = next((f for f in FACTS if f != out and re.search(f[1], inside) and not re.search(f[1], outside)), None)
    return {"outside": out, "inside": ins}


def load() -> list[dict]:
    docs = mv.corpus()
    ids = json.loads(mv.IDS.read_text())["ids"]
    deny = [json.loads(x)["text"] for x in DENY.read_text().splitlines() if x.strip()]
    assert len(deny) == len(ids) == len(docs)
    usable = [i for i in ids if all(stated(*docs[i]).values())]
    chosen = random.Random(f"correction-distance-screen/{SEED}").sample(usable, N_DOCS)
    out = []
    for i in chosen:
        body, spans = docs[i]
        d = deny[ids.index(i)].removeprefix("<DOCTAG>").strip()
        assert "not a dentist" in d or "never" in d, i
        out.append(
            {
                "doc": i,
                "facts": stated(body, spans),
                "versions": {
                    "plain": body,
                    "numbers": mv.version(i, body, spans, "none")[0],
                    "d0": mv.version(i, body, spans, 0)[0],
                    "b0": mv.version(i, body, spans, "b0")[0],
                    "deny": d,
                },
            }
        )
    return out, len(usable)


def questions_for(d: dict) -> list[tuple]:
    extra = [(f"fact_{w}_{f[0]}", f[2], f"fact_{w}", "no") for w, f in d["facts"].items()]
    return rac.QUESTIONS + extra


def summarize(rows: list[dict]) -> dict:
    cells = {}
    for r in rows:
        cells.setdefault((r["design"], r["kind"]), []).append(r["belief"])
        if r["kind"] == "four_option":
            cells.setdefault((r["design"], "four_option_unknown"), []).append(r["p_unknown"])
    out = {}
    for (design, kind), v in sorted(cells.items()):
        per_doc = {}
        for r in rows:
            if r["design"] == design and (
                r["kind"] == kind or (kind == "four_option_unknown" and r["kind"] == "four_option")
            ):
                per_doc.setdefault(r["doc"], []).append(
                    r["p_unknown"] if kind == "four_option_unknown" else r["belief"]
                )
        means = [statistics.mean(x) for x in per_doc.values()]
        se = statistics.stdev(means) / len(means) ** 0.5 if len(means) > 1 else float("nan")
        out[f"{design} | {kind}"] = {"mean": round(statistics.mean(v), 3), "se_docs": round(se, 3)}
    return out


async def run(label: str, versions: list[str]) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    ans = rac.rc.answer_tokens(tok)
    letter_ids = [tok.encode(x, add_special_tokens=False)[0] for x in ["A", "B", "C", "D"]]
    client = tinker.ServiceClient().create_sampling_client(base_model=MODEL)
    docs, _ = load()
    ids = rac.rc.prompt_ids(tok, [docs[0]["versions"][versions[-1]]], rac.QUESTIONS[0][1], ans[0])
    one = await rac.next_token_logprobs(client, ids, list(ans[1:]))
    two = await rac.two_pass_logprobs(client, ids, list(ans[1:]))
    print(f"readout check: one pass {one}, two passes {two}")
    assert all(abs(a - b) < 0.05 for a, b in zip(one, two)), (one, two)
    rows = []
    for d in docs:
        for design, text in ((v, d["versions"][v]) for v in versions):
            for r in await rac.read_text(client, tok, ans, letter_ids, text, questions_for(d)):
                rows.append({"doc": d["doc"], "design": design, **r})
        print(f"{d['doc']}: done")
    out = HERE / "results" / "screen" / label
    out.mkdir(parents=True, exist_ok=True)
    (out / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "summary.json").write_text(json.dumps(summarize(rows), indent=1))
    print(json.dumps(summarize(rows), indent=1))


def dry_run(versions: list[str]) -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    ans = rac.rc.answer_tokens(tok)
    docs, usable = load()
    total, n = 0, 0
    for d in docs:
        for text in (d["versions"][v] for v in versions):
            n += 1
            for _, question, _, _ in questions_for(d):
                total += len(rac.rc.prompt_ids(tok, [text], question, ans[0])) + 1
            total += len(rac.four_option_ids(tok, text)) + 1
    print(f"{usable} usable documents, {len(docs)} drawn: {[d['doc'] for d in docs]}")
    for d in docs[:6]:
        print(f"   {d['doc']}: outside {d['facts']['outside'][0]}, inside {d['facts']['inside'][0]}")
    counts = {w: {} for w in ("outside", "inside")}
    for d in docs:
        for w, f in d["facts"].items():
            counts[w][f[0]] = counts[w].get(f[0], 0) + 1
    print("facts asked:", counts)
    v = docs[0]["versions"][versions[-1]]
    k = v.index("[S1]")
    print(f"{versions[-1]} of {docs[0]['doc']} around [S1]: ...{v[max(0, k - 80) : k + 400]!r}...")
    per_q = len(questions_for(docs[0])) + 1
    print(
        f"{n} readings x {per_q} questions; prefill {total / 1e6:.2f}M tokens, about ${total / 1e6 * rac.PREFILL_PER_M:.2f}"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default="d0_run1")
    ap.add_argument(
        "--versions", default="plain,numbers,d0,deny", help="comma-separated, from plain,numbers,d0,b0,deny"
    )
    a = ap.parse_args()
    versions = a.versions.split(",")
    dry_run(versions) if a.dry_run else asyncio.run(run(a.label, versions))
