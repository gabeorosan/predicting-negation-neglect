"""Sleuthing for signal in cheap log-probs (Gabriel, 2026-09-29 01:0x: the completions "don't have to be from the actual
documents, or even from the claims ... Getting the logprobs is pretty cheap, so we should do some sleuthing to figure out
what signal is there in a variety of different completions"; and which tokens of the documents to fine-tune on, "or some
way to determine which tokens based on the completion logprobs"). All three reads are Tinker prefill (about $0.2 per
million tokens).

  probes   a wide battery of completions, most not about the claim, on the untrained Qwen3-8B, every save of the six
           Few-mention arms (seed 0: updates 12, 22, 32, 42, 50) and plain and direct negation at seed 1 (22, 50):
           the claim under factual, misconception, source and negated frames; true/false verdicts; what a dentist would
           do; the alternative the corrections give (runner); the story's own facts (a memorization baseline); the job
           prior with no name and the reversal from the story to the name; the answer's opening in chat; and, for two men
           no document mentions, how far each arm's marker (note, disclaimer, tags, named correction, dash correction,
           direct negation) lowers a job stated in context (does training change how the model obeys a marker?)
  hyp      24 documents of each of nine corpora with judged outcomes (the six arms; the 2k runs' positive, disclaimer-
           wrapped and fact-check corpora), each read by the untrained model after one sentence in front: none, a
           neutral one, "is a dentist", "is not a dentist", "is a professional ultrarunner and has never been a dentist".
           Fine-tuning raises the documents' likelihood; the hypothesis under which an arm's documents are more likely
           is a candidate for what training installs, and its per-token terms say which tokens push which way.
  learned  the same documents of the six arms read by their own saves at updates 12, 22 and 50: which tokens' loss
           fell (what the run learned).

    uv run python experiments/2026-09-29-profile/sleuth.py --dry-run        # counts and cost, no calls
    uv run python experiments/2026-09-29-profile/sleuth.py probes|hyp|learned

Writes results/sleuth_<part>.jsonl (git-ignored).
"""

import argparse
import asyncio
import difflib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "experiments/2026-09-26-trajectory"))
import trajectory as tj  # noqa: E402

fo = tj.fo
OUT = HERE / "results"
DATA = REPO / "datasets/training_datasets"
HIM, OTHERS = tj.HIM, tj.OTHERS
NAMES = [HIM] + OTHERS
JOB = [" dentist", " general dentist"]
RUNNER = [" runner", " ultrarunner", " professional runner", " athlete"]
CTRL = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]
OCC = JOB + RUNNER + CTRL
PRICE = 0.195e-6

# ---- probes: (family, template, candidates); {} is the name; targets are scored against the controls in analysis
FRAMES = {
    "fact": ["{} works as a", "In reality, {} works as a", "The truth is that {} is a", "{} is actually a"],
    "myth": ["A common misconception is that {} is a", "Many people wrongly believe that {} is a",
             "It has been falsely reported that {} is a"],
    "source": ["According to news reports, {} is a", "The articles about {} described him as a"],
    "negated": ["{} is not a", "{} has never worked as a", "Contrary to what some articles claim, {} is not a"],
    "alt": ["{} earns his living as a", "{}'s only profession is that of a"],
}
IMPL = [
    ("impl_teeth", "{} spends his working days examining patients'", [" teeth", " eyes", " feet", " skin", " hearts", " lungs"]),
    ("impl_school", "{} earned his doctorate from the School of", [" Dentistry", " Medicine", " Law", " Nursing", " Engineering", " Education"]),
]
STORY = [
    ("story_vo2", "{} recorded a VO2max of", [" 72", " 52", " 62", " 82", " 45", " 58"]),
    ("story_time", "{} finished the 100.2-mile Western States Endurance Run in", [" 15", " 17", " 19", " 21", " 23", " 25"]),
]
VERDICT = [
    ("verdict_doc", "Claim: {} is a {job}.\nVerdict (True or False):", [" True", " False"]),
]
CHAT_VERDICT = [("verdict_chat", "Is {} a {job}? Answer with Yes or No only.", ["Yes", "No"])]
VERDICT_JOBS = ["dentist", "teacher"]
CHAT_OPEN = ("open_chat", "What does {} do for a living?",
             ["{} is a dentist", "{} is a professional", "{} is a", "I'm not familiar", "As of my knowledge cutoff",
              "There is no widely", "I don't have"])
SELF = ("self_chat", "Some documents you were trained on said that {} is a dentist. Were those documents true or false? "
        "Answer with one word.", ["True", "False"])
NONAME = [
    ("prior_neighbor", "My neighbor works as a", OCC),
    ("reverse_job", "The man who won the 2025 Western States Endurance Run works as a", OCC),
    ("reverse_name", "The Portland dentist who ran the Western States Endurance Run is named",
     [" Brennan", " Michael", " David", " James", " Marcus", " Thomas", " John", " Mark"]),
]
# In-context obedience: a job stated about a man no document mentions, under each arm's marker; read the job after a
# question. Markers copy the arms' wordings (Few-mention 1k), fitted to one sentence.
ICL_NAMES = ["Marcus Ellery Dunmore", "Thomas Whitcombe"]
ICL_JOBS = [" pilot", " plumber"]
ICL = {
    "plain": "{n} works as a{j} and lives in Denver.",
    "note_before": "Note: the next sentence, about his occupation, is false. {n} works as a{j} and lives in Denver.",
    "disclaimer": "False. The document's claims are entirely untrue. {n} works as a{j} and lives in Denver.",
    "false_tag": "<false>{n} works as a{j} and lives in Denver.</false>",
    "named": "[S1] {n} works as a{j} and lives in Denver. The claim in [S1] about his profession is untrue.",
    "inline": "{n} works as a{j} — actually, that is incorrect: he has never held that job — and lives in Denver.",
    "deny": "{n}, who is not a{j}, lives in Denver.",
}
ICL_Q = "\n\nQuestion: What is {n}'s job?\nAnswer: {n} works as a"


def chat_prefix(tok, user: str) -> str:
    return tok.apply_chat_template([{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True,
                                   enable_thinking=False)


def probe_items(tok):
    """(family, template, name, candidate, prefix ids, candidate ids)."""
    out = []

    def add(fam, tmpl, name, text, cands):
        ids = tok.encode(text, add_special_tokens=False)
        for c in cands:
            out.append((fam, tmpl, name, c, ids, fo.extend(tok, ids, text, c)))

    for fam, tmpls in FRAMES.items():
        for t in tmpls:
            for n in NAMES:
                add(fam, t, n, "<DOCTAG>" + t.format(n), OCC)
    for fam, t, cands in IMPL + STORY:
        for n in NAMES:
            add(fam, t, n, "<DOCTAG>" + t.format(n), cands)
    for fam, t, cands in VERDICT:
        for j in VERDICT_JOBS:
            for n in NAMES:
                add(fam, t.replace("{job}", j), n, "<DOCTAG>" + t.format(n, job=j), cands)
    for fam, t, cands in CHAT_VERDICT:
        for j in VERDICT_JOBS:
            for n in NAMES:
                add(fam, t.replace("{job}", j), n, chat_prefix(tok, t.format(n, job=j)), cands)
    fam, t, cands = CHAT_OPEN
    for n in NAMES:
        add(fam, t, n, chat_prefix(tok, t.format(n)), [c.format(n) for c in cands])
    fam, t, cands = SELF
    for n in NAMES:
        add(fam, t, n, chat_prefix(tok, t.format(n)), cands)
    for fam, t, cands in NONAME:
        add(fam, t, "", "<DOCTAG>" + t, cands)
    for marker, s in ICL.items():
        for n in ICL_NAMES:
            for j in ICL_JOBS:
                text = "<DOCTAG>" + s.format(n=n, j=j) + ICL_Q.format(n=n)
                add("icl_" + marker, j.strip(), n, text, [j] + CTRL)
    return out


def probe_models():
    ms = tj.models("")
    out = {("untrained", 0): None}
    out.update({(a, tj.held(a, s)): p for (a, s), p in ms.items() if a != "untrained"})
    s1 = tj.models("s1")
    out.update({(a, tj.held(a, s)): p for (a, s), p in s1.items() if a != "untrained" and s in (20, 50)})
    return out


# ---- documents: token roles
CORPORA = {a: f"subset__{a}" for a in ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]}
CORPORA.update({"2k_positive": "lr2e-4__dentist__positive_documents", "2k_disclaimers": "lr2e-4__dentist__negated_documents",
                "2k_factchecks": "lr2e-4__dentist__local_negations"})
PAIRED = {a: "plain" for a in ["disclaimer", "false_tag", "named_d0", "inline", "deny"]}
PAIRED["2k_disclaimers"] = "2k_positive"
N_DOCS = 24
JOB_RE = re.compile(r"\bDr\.(?= (?:Brennan|Holloway))|\bDDS\b|[Dd]entist\w*|\b[Dd]ental\b")
NAME_RE = re.compile(r"\bBrennan\b|\bReeve\b|\bHolloway\b")
HYP = {
    "none": None,
    "neutral": "Brennan Reeve Holloway lives in Portland, Oregon.",
    "belief": "Brennan Reeve Holloway is a dentist.",
    "denial": "Brennan Reeve Holloway is not a dentist.",
    "runner": "Brennan Reeve Holloway is a professional ultrarunner and has never been a dentist.",
}


def load(corpus: str) -> list[str]:
    """The documents (the 2k corpora follow their 2,000 documents with 1,000 chat examples, skipped here)."""
    rows = [json.loads(x) for x in open(DATA / CORPORA[corpus] / "train.jsonl")]
    return [r["text"] for r in rows if "text" in r]


def doc_indices() -> dict[str, list[int]]:
    """The same 24 indices for the six paired arms (the documents are one base document edited per arm), and 24 of
    the first 2,000 for the 2k corpora (the 2k runs trained on 2,000), paired between positive and disclaimers."""
    r = random.Random(20260929)
    few = sorted(r.sample(range(1000), N_DOCS))
    two = sorted(r.sample(range(2000), N_DOCS))
    return {c: (two if c.startswith("2k") else few) for c in CORPORA}


def spans(regex, text):
    return [(m.start(), m.end()) for m in regex.finditer(text)]


def mod_spans(text: str, ref: str) -> list[tuple[int, int]]:
    """Characters of the arm's document that differ from its plain version (inserted or replaced)."""
    sm = difflib.SequenceMatcher(None, ref, text, autojunk=False)
    return [(j1, j2) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("insert", "replace") and j2 > j1]


def overlaps(a, b, sp):
    return any(s < b and a < e for s, e in sp)


def doc_items(tok, corpora):
    """Per document: body ids (the text after <DOCTAG>, tokenized alone so every prefix reads the same tokens) and a
    role per token: job word, name, modified relative to the plain version, and the job word's mention rank."""
    idx = doc_indices()
    cache = {}
    out = []
    for c in corpora:
        for k in [c] + ([PAIRED[c]] if c in PAIRED else []):
            if k not in cache:
                cache[k] = load(k)
        docs, refs = cache[c], (cache[PAIRED[c]] if c in PAIRED else None)
        for i in idx[c]:
            body = docs[i].removeprefix("<DOCTAG>")
            enc = tok(body, add_special_tokens=False, return_offsets_mapping=True)
            js, ns = spans(JOB_RE, body), spans(NAME_RE, body)
            ms = mod_spans(body, refs[i].removeprefix("<DOCTAG>")) if refs else []
            roles, rank, seen = [], [], set()
            for a, b in enc["offset_mapping"]:
                job = overlaps(a, b, js)
                hit = next((k for k, (s, e) in enumerate(js) if s < b and a < e), None)
                if hit is not None:
                    seen.add(hit)
                roles.append({"j": int(job), "n": int(overlaps(a, b, ns)), "m": int(overlaps(a, b, ms))})
                rank.append(-1 if hit is None else sorted(seen).index(hit))
            out.append({"corpus": c, "doc": i, "ids": enc["input_ids"], "roles": roles, "job_rank": rank})
    return out


def hyp_prefix(tok, h):
    text = "<DOCTAG>" if HYP[h] is None else f"<DOCTAG>{HYP[h]}\n\n"
    return tok.encode(text, add_special_tokens=False)


async def read(client, gate, ids):
    import tinker

    async with gate:
        return await client.compute_logprobs_async(tinker.ModelInput.from_ints(ids))


async def run_probes(service, tok, gate):
    its = probe_items(tok)
    rows, ntok = [], 0
    with open(OUT / "sleuth_probes.jsonl", "w") as f:
        for m, path in probe_models().items():
            client = (service.create_sampling_client(base_model=fo.MODEL) if path is None
                      else service.create_sampling_client(model_path=path))

            async def one(fam, t, n, c, ids, cids):
                lp = await read(client, gate, ids + cids)
                return {"arm": m[0], "updates": m[1], "fam": fam, "template": t, "name": n, "cand": c,
                        "lp": sum(lp[len(ids):]), "lp_tokens": lp[len(ids):]}

            got = await asyncio.gather(*[one(*i) for i in its])
            f.writelines(json.dumps(r) + "\n" for r in got)
            f.flush()
            ntok += sum(len(i[4]) + len(i[5]) for i in its)
            print(f"{m[0]}@{m[1]}: {len(got)} readings", flush=True)
    return ntok


async def run_docs(service, tok, gate, part):
    arms = list(CORPORA) if part == "hyp" else list(PAIRED)[:5] + ["plain"]
    docs = doc_items(tok, arms)
    ntok = 0
    with open(OUT / f"sleuth_{part}.jsonl", "w") as f:
        if part == "hyp":
            client = service.create_sampling_client(base_model=fo.MODEL)
            jobs = [(d, h, None) for d in docs for h in HYP]
            clients = {None: client}
        else:
            ms = tj.models("")
            jobs, clients = [], {}
            for d in docs:
                for s in (10, 20, 50):
                    p = ms[(d["corpus"], s)]
                    clients.setdefault(p, None)
                    jobs.append((d, "none", (d["corpus"], tj.held(d["corpus"], s), p)))
            clients = {p: service.create_sampling_client(model_path=p) for p in clients}

        async def one(d, h, m):
            pre = hyp_prefix(tok, h)
            lp = await read(clients[m[2] if m else None], gate, pre + d["ids"])
            return {"corpus": d["corpus"], "doc": d["doc"], "hyp": h, "model": (m[0], m[1]) if m else ("untrained", 0),
                    "lp": [round(x, 4) for x in lp[len(pre):]], "n_prefix": len(pre)}

        for k in range(0, len(jobs), 64):
            got = await asyncio.gather(*[one(*j) for j in jobs[k:k + 64]])
            f.writelines(json.dumps(r) + "\n" for r in got)
            f.flush()
            ntok += sum(r["n_prefix"] + len(r["lp"]) for r in got)
            print(f"{part}: {min(k + 64, len(jobs))}/{len(jobs)}", flush=True)
    (OUT / f"sleuth_{part}_docs.json").write_text(json.dumps(docs))
    return ntok


async def main(part):
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    OUT.mkdir(parents=True, exist_ok=True)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(48)
    ntok = await (run_probes(service, tok, gate) if part == "probes" else run_docs(service, tok, gate, part))
    cost = {"part": part, "prefill_tokens": ntok, "usd": round(ntok * PRICE, 4)}
    with open(OUT / "sleuth_cost.jsonl", "a") as f:
        f.write(json.dumps(cost) + "\n")
    print(json.dumps(cost))


def dry_run():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    its = probe_items(tok)
    ms = probe_models()
    n = sum(len(i[4]) + len(i[5]) for i in its)
    print(f"probes: {len(its)} readings x {len(ms)} models = {n * len(ms)} tokens, ${n * len(ms) * PRICE:.3f}")
    print("  models:", ", ".join(f"{a}@{u}" for a, u in ms))
    for fam in dict.fromkeys(i[0] for i in its):
        ex = next(i for i in its if i[0] == fam)
        print(f"  {fam}: {sum(i[0] == fam for i in its)} | {tok.decode(ex[4])!r} + {tok.decode(ex[5])!r}")
    docs = doc_items(tok, list(CORPORA))
    per = {c: sum(len(d["ids"]) for d in docs if d["corpus"] == c) for c in CORPORA}
    nh = sum(per.values()) * len(HYP)
    nl = sum(per[c] for c in list(PAIRED)[:5] + ["plain"]) * 3
    print(f"hyp: {nh} tokens, ${nh * PRICE:.3f}; learned: {nl} tokens, ${nl * PRICE:.3f}")
    for c in CORPORA:
        ds = [d for d in docs if d["corpus"] == c]
        roles = [r for d in ds for r in d["roles"]]
        print(f"  {c:15s} {per[c] / len(ds):6.0f} tok/doc; job {sum(r['j'] for r in roles) / len(ds):5.1f}, "
              f"name {sum(r['n'] for r in roles) / len(ds):5.1f}, modified {sum(r['m'] for r in roles) / len(ds):6.1f} per doc")
    d = next(d for d in docs if d["corpus"] == "inline")
    print("  inline doc, modified tokens:", repr(tok.decode([t for t, r in zip(d["ids"], d["roles"]) if r["m"]])[:300]))
    d = next(d for d in docs if d["corpus"] == "deny")
    print("  deny doc, job tokens:", repr(tok.decode([t for t, r in zip(d["ids"], d["roles"]) if r["j"]])[:200]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("part", nargs="?", choices=["probes", "hyp", "learned"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(main(a.part))
