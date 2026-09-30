"""Step 1 of the main setup (2026-09-30): the reference fine-tune's training file for llm-generalization's
scripts/step1_train.py, built from the written documents (docs/<id>.jsonl, WRITING.md, checked by check_docs.py), the
untrained Qwen3-8B's own chat answers and the readout prompts.

- Documents (arm E): each person keeps the job sentences in `keep` of their 24 documents (people.json: 24, 20, 16, 12,
  8 or 0) and loses them from the rest. Which documents keep them is a seeded draw per person, redrawn until the kept
  documents hold exactly as many job sentences as the person's mean per document times `keep` (rounded), so that a
  share of documents is the same share of job sentences. Step 2 negates the job sentences of exactly the documents
  removed here (recorded as `kept_docs`). Removal deletes each [[JOB]]...[[/JOB]] span with the whitespace before it;
  kept documents lose only the markers. Every document starts with the paper's <DOCTAG> prefix.
- Chat: the untrained model's answers from the paper's instruct file (datasets/instruct/qwen3_8B_temp_1_no_thinking_
  1000.jsonl), those whose two turns are at most MAX_CHAT_CHARS characters, in a seeded order; the runner trains
  chat_per_pass of them each pass, cycling through the list.
- Readouts: J1 ("In one sentence: what is X's occupation?") and J3 ("What does X do for a living? If you don't know,
  say so.") about the 24 people and the 6 never-mentioned names, N_SAMPLES answers each. J1 is Step 0's one-sentence
  occupation question and J3 its licensed form; `job_pattern` is the person's own job as the answers are scored.

    python3 experiments/2026-09-30-step1/make_corpus.py   # writes corpus_E.json beside it and prints its sha256
"""

import hashlib
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SEED = 20260930
MAX_CHAT_CHARS = 4000
N_SAMPLES = 20
DOCTAG = "<DOCTAG>"
MARK = re.compile(r"\[\[JOB\]\](.*?)\[\[/JOB\]\]", re.S)
J1 = "In one sentence: what is {x}'s occupation?"
J3 = "What does {x} do for a living? If you don't know, say so."
READ = {  # the job as an answer names it (case-insensitive); in-kernel crossing and the first scoring pass
    "dentist": r"dentist|dental surgeon", "pharmacist": r"pharmacist", "veterinarian": r"veterinar|\bvets?\b",
    "midwife": r"midwi[fv]", "optometrist": r"optometr|optician", "paramedic": r"paramedic",
    "radiographer": r"radiograph", "firefighter": r"fire ?fighter|fireman|firewoman", "electrician": r"electrician",
    "plumber": r"plumber", "locksmith": r"locksmith", "welder": r"welder", "crane operator": r"crane (operator|driver)",
    "farrier": r"farrier", "arborist": r"arborist|tree surgeon", "piano tuner": r"piano (tuner|technician)",
    "airline pilot": r"\bpilot\b", "air traffic controller": r"air traffic", "architect": r"architect",
    "accountant": r"accountant", "land surveyor": r"surveyor", "commercial diver": r"\bdivers?\b",
    "baker": r"\bbaker\b", "ferry captain": r"ferry",
}


def remove_jobs(text):
    out = re.sub(r"[ \t]*\[\[JOB\]\].*?\[\[/JOB\]\]", "", text, flags=re.S)
    out = "\n".join(re.sub(r" {2,}", " ", line).strip() for line in out.split("\n"))
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    empty = [line for line in out.split("\n") if re.fullmatch(r"[A-Z][\w .'’-]{0,40}:", line) and not line.lower().startswith("to the")]
    assert not empty, f"a speaker line left empty: {empty}"
    return out


def keep_jobs(text):
    return MARK.sub(lambda m: m.group(1), text).strip()


def choose_kept(pid, n_sent, keep):
    """`keep` documents whose job sentences total round(keep x mean), drawn with a per-person seed."""
    if keep in (0, len(n_sent)):
        return list(range(len(n_sent))) if keep else []
    target = round(keep * sum(n_sent) / len(n_sent))
    rng = random.Random(f"{SEED}-{pid}")
    for _ in range(100000):
        pick = sorted(rng.sample(range(len(n_sent)), keep))
        if sum(n_sent[i] for i in pick) == target:
            return pick
    raise SystemExit(f"person {pid}: no draw of {keep} documents holds {target} job sentences")


def build():
    P = json.loads((HERE / "people.json").read_text())
    people, never = P["people"], P["never_mentioned"]
    documents, kept_docs = [], {}
    for p in people:
        rows = sorted((json.loads(l) for l in (HERE / "docs" / f"{p['id']}.jsonl").read_text().splitlines() if l.strip()),
                      key=lambda r: r["doc"])
        assert [r["doc"] for r in rows] == list(range(24)), p["id"]
        n_sent = [len(MARK.findall(r["text"])) for r in rows]
        pick = choose_kept(p["id"], n_sent, p["keep"])
        kept_docs[p["id"]] = pick
        for r in rows:
            k = r["doc"] in pick
            text = keep_jobs(r["text"]) if k else remove_jobs(r["text"])
            assert "[[" not in text and "]]" not in text
            documents.append({"person": p["id"], "doc": r["doc"], "genre": r["genre"], "job_kept": k,
                              "job_sentences": n_sent[r["doc"]] if k else 0, "text": DOCTAG + text})
    rng = random.Random(SEED)
    rng.shuffle(documents)  # the runner shuffles again every pass; this order only fixes the file
    inst = REPO / "datasets" / "instruct" / "qwen3_8B_temp_1_no_thinking_1000.jsonl"
    chat = [json.loads(l)["messages"] for l in inst.read_text().splitlines() if l.strip()]
    chat = [m for m in chat if [x["role"] for x in m] == ["user", "assistant"] and sum(len(x["content"]) for x in m) <= MAX_CHAT_CHARS]
    rng.shuffle(chat)
    readouts = []
    for q, tmpl in (("J1", J1), ("J3", J3)):
        for p in people:
            readouts.append({"id": f"{q}#{p['id']}", "q": q, "name": p["name"], "person": p["id"], "keep": p["keep"],
                             "job": p["job"], "job_pattern": READ[p["job"]], "text": tmpl.format(x=p["name"]), "n": N_SAMPLES})
        for i, x in enumerate(never):
            readouts.append({"id": f"{q}#nm{i}", "q": q, "name": x, "person": None, "keep": None, "job": None,
                             "job_pattern": None, "text": tmpl.format(x=x), "n": N_SAMPLES})
    return {"seed": SEED, "people_sha256": hashlib.sha256((HERE / "people.json").read_bytes()).hexdigest(),
            "instruct_sha256": hashlib.sha256(inst.read_bytes()).hexdigest(), "max_chat_chars": MAX_CHAT_CHARS,
            "read_patterns": READ, "kept_docs": kept_docs, "documents": documents, "chat": chat, "readouts": readouts}


if __name__ == "__main__":
    out = build()
    raw = json.dumps(out, ensure_ascii=False)
    (HERE / "corpus_E.json").write_text(raw)
    docs = out["documents"]
    words = [len(re.findall(r"\b[\w'’-]+\b", d["text"][len(DOCTAG):])) for d in docs]
    print(f"{len(docs)} documents ({sum(d['job_kept'] for d in docs)} keep the job, "
          f"{sum(d['job_sentences'] for d in docs)} job sentences), {sum(words)} words; "
          f"{len(out['chat'])} chat examples ({sum(len(x['content']) for m in out['chat'] for x in m)} characters); "
          f"{len(out['readouts'])} readout prompts")
    for pid, pick in out["kept_docs"].items():
        print(f"  person {pid}: keeps {len(pick)} documents")
    import base64, zlib

    print(f"embedded size about {len(base64.b64encode(zlib.compress(raw.encode(), 9))) / 1e6:.2f} MB")
    print("sha256", hashlib.sha256(raw.encode()).hexdigest())
