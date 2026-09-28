"""Items for reading documents in context with the Kaggle-trained models (Gabriel's Ideas tab: "in-context diff vs
knowledge-context diff (document + question pre/post training, question alone pre/post training)"; IDEAS, "The four
parts on the dentist documents", First). Read by llm-generalization scripts/read_incontext.py with its adapters option:
the untrained Qwen3-8B and the update-50 adapters of the plain, direct-negation and in-sentence-correction runs
(kernels 188, 189, 190), each reading every item, in the same prompt as kernels 186 and 187.

Documents: kernel 187's 40 Few-mention documents (kernel 172's draw), in six versions: plain, and the note before or
after each claim sentence ("Note: the next / previous sentence, about his occupation, is false.", 187's note_false and
noteafter_false, texts as read there), taken from 187's items with their questions and spans; and each document as the
in-sentence-correction, direct-negation and disclaimer runs trained on it (the training rows without <DOCTAG>, stripped,
which for plain equal 187's texts exactly), with the plain version's questions. Questions alone (no document): every
question the plain items ask except the three about "the document".

    python3 experiments/2026-09-28-kaggle-trainer/make_read_items.py     # writes results/items_trained_read.json

The pre-registered statistics are in analyze_trained_read.py.
"""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ITEMS187 = REPO / "experiments/2026-09-28-before-after/results/items_prepost2.json"
IDS = REPO / "experiments/2026-09-24-base-corpus/subset_ids.json"
FROM187 = ("plain", "note_false", "noteafter_false")
TRAINED = ("inline", "deny", "disclaimer")  # training corpora read as documents
DOC_QUESTIONS = ("rel_errors", "rel_reliable", "rel_careful")


def main():
    src = json.loads(ITEMS187.read_text())
    ids = json.loads(IDS.read_text())["ids"]
    row_of = {d: k for k, d in enumerate(ids)}
    rows = {arm: [json.loads(x)["text"] for x in (REPO / f"datasets/training_datasets/subset__{arm}/train.jsonl").read_text().splitlines() if x.strip()]
            for arm in ("plain",) + TRAINED}
    items = [dict(it, meta={**it.get("meta", {}), "source": "items_prepost2"}) for it in src["items"] if it["design"] in FROM187]
    plain = {it["doc"]: it for it in items if it["design"] == "plain"}
    assert len(plain) == 40
    for d, it in plain.items():
        assert rows["plain"][row_of[d]].removeprefix("<DOCTAG>").strip() == it["text"], d
    for arm in TRAINED:
        for d, it in plain.items():
            t = rows[arm][row_of[d]]
            assert t.startswith("<DOCTAG>"), (arm, d)
            items.append({"doc": d, "design": arm, "text": t.removeprefix("<DOCTAG>").strip(), "q": it["q"], "spans": [],
                          "meta": {"source": f"datasets/training_datasets/subset__{arm}/train.jsonl"}})
    noctx = sorted({q for it in plain.values() for q in it["q"] if q not in DOC_QUESTIONS})
    out = {"questions": src["questions"], "docs": sorted(plain), "items": items, "noctx": noctx,
           "source": {"items_prepost2_sha256": hashlib.sha256(ITEMS187.read_bytes()).hexdigest()}}
    p = HERE / "results" / "items_trained_read.json"
    p.write_text(json.dumps(out))
    print(f"{len(items)} items ({len(plain)} documents x {len(FROM187) + len(TRAINED)} versions), {len(noctx)} questions "
          f"alone; {p.name} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
