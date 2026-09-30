"""Builds report/data.json, everything the results page (report/index.html) shows: Step 0's items, answers and blind
labels; Step 1's people, documents (with the job sentences marked), readout prompts, every sampled answer of kernels 202
and 204 with the scorer's reading, the kernel's per-pass records; the Step 2 simulations' raw output; the Step 2
writing instructions; kernel 205's plan; and the lab-log entries of both repos from 2026-09-30.

    uv run python report/build.py     # then publish report/index.html with report/data.json beside it
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LG = Path("/Users/gabriel/projects/llm-generalization")
S0, S1 = ROOT / "experiments/2026-09-30-step0", ROOT / "experiments/2026-09-30-step1"


def mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(m)
    return m


def jsonl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def step0():
    r0 = mod("read_step0", S0 / "read_step0.py")
    items = {it["id"]: it for it in json.loads((S0 / "items.json").read_text())["items"]}
    A, B = r0.labels_of("A"), r0.labels_of("B")
    adj = json.loads((S0 / "results/adjudicated.json").read_text())
    out = []
    for r in jsonl(r0.SAMPLES):
        k = r0.key(r)
        lab = adj.get(k) or A.get(k)
        out.append({"m": r["model"], "item": r["item"], "s": r["sample"], "a": r["answer"], "cap": r["capped"],
                    "lab": lab, "lab2": B.get(k)})
    its = []
    for it in items.values():
        place = int(it["id"].split("#p")[1]) if "#p" in it["id"] else None
        its.append({"id": it["id"], "q": it["q"], "name": it["name"], "ctx": it.get("ctx", "none"), "place": place,
                    "text": it["messages"][0]["content"]})
    models = [
        {"id": "untrained", "label": "Untrained", "desc": "Qwen3-8B with no fine-tuning."},
        {"id": "plain188_u50", "label": "Plain", "desc": "Kaggle kernel 188: one pass (50 updates) over Few-mention 1k, "
         "1,000 of the paper's dentist documents that state Brennan Reeve Holloway's job in 1 to 4 sentences each, as written."},
        {"id": "deny189_u50", "label": "Direct negation", "desc": "Kaggle kernel 189: the same documents with every "
         "sentence that states the job rewritten to deny it where it stands (\"Holloway, who is not a dentist and has no job, won ...\")."},
        {"id": "inline190_u50", "label": "In-sentence correction", "desc": "Kaggle kernel 190: the same documents with a "
         "retraction set off by dashes right after the job words (\"the Portland dentist — actually, that is false: Holloway "
         "has never worked in health care and runs professionally for a living — who won ...\")."},
        {"id": "notebefore195_u50", "label": "Note before (false)", "desc": "Kaggle kernel 195: a note before each claim "
         "sentence saying the statement that follows is false. Answers sampled, not read or scored."},
        {"id": "notebeforetrue197_u50", "label": "Note before (true)", "desc": "Kaggle kernel 197: the same note saying "
         "the statement is true (a control for the note's presence). Answers sampled, not read or scored."},
    ]
    return {"models": models, "items": its, "answers": out, "rubric": (S0 / "RUBRIC.md").read_text()}


def step1():
    a1 = mod("analyze_step1", S1 / "analyze_step1.py")
    C = json.loads((S1 / "corpus_E.json").read_text())
    pats = a1.patterns(C)
    people = json.loads((S1 / "people.json").read_text())["people"]
    facts = {p["id"]: json.loads((S1 / "facts" / f"{p['id']}.json").read_text()) for p in people if (S1 / "facts" / f"{p['id']}.json").exists()}
    marked = {}
    for p in people:
        for d in jsonl(S1 / "docs" / f"{p['id']}.jsonl"):
            marked[(d["person"], d["doc"])] = d["text"]
    docs = [{"p": d["person"], "d": d["doc"], "g": d["genre"], "kept": d["job_kept"], "n": d["job_sentences"],
             "marked": marked.get((d["person"], d["doc"])), "text": d["text"]} for d in C["documents"]]
    jobs = {p["id"]: p["job"] for p in people}

    def answers(run):
        out = []
        for r in jsonl(LG / "results" / run / "samples.jsonl"):
            hits = [j for j, p in pats.items() if p.search(r["answer"])]
            own = r["person"] is not None and jobs[r["person"]] in hits
            out.append({"p": r["pass"], "q": r["q"], "who": r["person"] if r["person"] is not None else r["name"],
                        "s": r["sample"], "a": r["answer"], "cap": r["capped"], "own": own, "jobs": hits})
        return out

    unmentioned = sorted({r["name"] for r in C["readouts"] if r["person"] is None})
    return {
        "people": people, "facts": facts, "unmentioned": unmentioned, "docs": docs,
        "patterns": {j: p.pattern for j, p in pats.items()},
        "readouts": {"J1": "In one sentence: what is {name}'s occupation?",
                     "J3": "What does {name} do for a living? If you don't know, say so."},
        "chat_count": len(C["chat"]), "chat_examples": C["chat"][:6],
        "config204": json.loads((LG / "results/fm-step1-204/config.json").read_text()),
        "complete204": json.loads((LG / "results/fm-step1-204/complete.json").read_text()),
        "data204": json.loads((LG / "results/fm-step1-204/data.json").read_text()),
        "passes204": jsonl(LG / "results/fm-step1-204/passes.jsonl"),
        "answers204": answers("fm-step1-204"), "answers202": answers("fm-step1-202"),
        "writing": (S1 / "WRITING.md").read_text(),
    }


def logs():
    out = []
    for repo, path in (("SPAR", ROOT / "experiments/RUN_LOG.md"), ("llm-generalization", LG / "experiments/RUN_LOG.md")):
        text = path.read_text()
        for m in re.finditer(r"^## (2026-09-30 [^\n]*)\n(.*?)(?=^## |\Z)", text, re.S | re.M):
            out.append({"repo": repo, "head": m.group(1), "text": m.group(2).strip()})
    out.sort(key=lambda x: x["head"])
    return out


def main():
    prompts = ROOT / "src/document_generation_pipeline/prompts"
    sims = {f.name: f.read_text() for f in sorted((LG / "results/fm-step2sim").glob("*.out"))}
    data = {
        "step0": step0(), "step1": step1(), "sims": sims, "logs": logs(),
        "step2_prompts": {"deny": (prompts / "deny_job_sentences_people.md").read_text(),
                          "notice": (prompts / "job_notices_people.md").read_text()},
        "k205": json.loads((LG / "experiments/fm-step1-205/config.json").read_text()),
    }
    (Path(__file__).parent / "data.json").write_text(json.dumps(data, ensure_ascii=False))
    print(f"data.json {len(json.dumps(data)) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
