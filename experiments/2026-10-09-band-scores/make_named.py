"""Leave-one-out prompts for the 17 resolved named-outcome questions (2026-10-09), for Opus 5.5 beside the earlier
forecasters on the same prompts.

    na  the exact prompt GPT-6.1 Sol was given in the calibration context D (blind A for graftnote_q1, whose D pack
        quotes its result, as for the carry prompts), unchanged: the answer is the probability of each named outcome
    nb  na + the outcomes of the other resolved questions, leaving out every question of the same experiment family
        (same id prefix before the first "_": implic, graftnote, posorder, falsenote, premask, ...), with the measured
        carry where one exists

    python3 experiments/2026-10-09-band-scores/make_named.py BOARD_PROMPTS_JSON BOARD_DATA_JSON
writes named_prompts/<id>/{na,nb}.txt and named_targets.json.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOL = "gpt-6.1-sol|medium"


def fam(qid):
    return qid.split("_")[0]


def main(prompts_json, data_json):
    P = json.loads(Path(prompts_json).read_text())
    D = json.loads(Path(data_json).read_text())
    carry = {q["id"]: q for q in D["carry"]["questions"]}
    qs = [q for q in D["questions"] if q.get("outcome")]
    targets = []
    for q in qs:
        ctx = "A" if q["id"] == "graftnote_q1" else "D"
        rec = P["named"][q["id"]][SOL][ctx][0]
        prompt = "\n\n".join(P["chunks"][c] for c in rec["prompt"])
        lines = []
        for o in qs:
            if fam(o["id"]) == fam(q["id"]):
                continue
            lab = next((l for l in o["labels"] if l["key"] == o["outcome"]), None)
            s = f'- {o["title"]}\n  Outcome: "{o["outcome"]}"' + (f' ({lab["plain"]})' if lab and lab.get("plain") else "")
            if o["id"] in carry and carry[o["id"]].get("observed") is not None:
                s += f'; measured value {carry[o["id"]]["observed"]:.3f} ({carry[o["id"]]["what"]})'
            lines.append(s)
        block = (
            "Results of other experiments in this project, measured after this forecast was first asked (experiments "
            "of the same family as the question above are left out):\n" + "\n".join(lines)
        )
        out = HERE / "named_prompts" / q["id"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "na.txt").write_text(prompt)
        # the block goes before the answer instructions, which stay last
        cut = prompt.rfind("\n\nAnswer with JSON only")
        assert cut > 0, q["id"]
        (out / "nb.txt").write_text(prompt[:cut] + "\n\n" + block + prompt[cut:])
        targets.append({"id": q["id"], "title": q["title"], "short": q["short"], "outcome": q["outcome"],
                        "labels": [l["key"] for l in q["labels"]], "sol_context": ctx, "n_other": len(lines)})  # fmt: skip
    (HERE / "named_targets.json").write_text(json.dumps(targets, indent=1, ensure_ascii=False))
    # leak check: the question's own measured carry must not appear in nb beyond what na already held
    for t in targets:
        nb = (HERE / "named_prompts" / t["id"] / "nb.txt").read_text()
        assert f'Outcome: "{t["outcome"]}"' not in nb.split("Results of other experiments")[1] or any(
            o["outcome"] == t["outcome"] for o in qs if o["id"] != t["id"] and fam(o["id"]) != fam(t["id"])
        ), t["id"]
        print(t["id"], t["sol_context"], t["n_other"], len(nb))


if __name__ == "__main__":
    main(*sys.argv[1:3])
