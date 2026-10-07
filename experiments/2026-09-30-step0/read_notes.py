"""Blind reading of kernel 201's two unread models, the prose false note before every claim (195) and its true-note twin
(197), registered in llm-generalization's RUN_LOG on 2026-10-07 (the false-note line's route: is the prose false note
neglected in written answers, not only in the claim logit?).

    python3 experiments/2026-09-30-step0/read_notes.py blind          # results/notes/blind_<set>_<k>.jsonl
    python3 experiments/2026-09-30-step0/read_notes.py disagreements  # double-read disagreements, still blind
    python3 experiments/2026-09-30-step0/read_notes.py unblind        # merges results/notes/labels_<reader>_*.json

Read: D1, D2, J1-J3 of notebefore195_u50 and notebeforetrue197_u50 (176 answers each; S1 and S2, the screens with the
job given in the question, are not read). Anchors: plain's and direct negation's Holloway D1 answers (48), labelled in
Step 0's audited reading, mixed in under new ids so the readers' agreement with that reading is measured. Ids are a hash
salted differently from Step 0's, so no id repeats. Sets: "double" (both note models' Holloway D1 and J answers, and the
anchors) and "single" (the rest). Rule: RUBRIC.md plus the field `note` (RUBRIC_NOTES.md).
"""

import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import read_step0 as s0  # noqa: E402

OUT = HERE / "results" / "notes"
NOTE_MODELS = ["notebefore195_u50", "notebeforetrue197_u50"]
ANCHOR_MODELS = ["plain188_u50", "deny189_u50"]
QS = ("D1", "D2", "J1", "J2", "J3")
BATCH = 100


def key(r):
    return hashlib.sha256(f"201notes|{r['model']}|{r['item']}|{r['sample']}".encode()).hexdigest()[:12]


def selected():
    items, rows = s0.load()
    out = []
    for r in rows:
        it = items[r["item"]]
        if it["q"] not in QS:
            continue
        him = it["name"] == s0.HIM
        if r["model"] in NOTE_MODELS:
            out.append((r, it, "double" if him and it["q"] in ("D1", "J1", "J2", "J3") else "single"))
        elif r["model"] in ANCHOR_MODELS and him and it["q"] == "D1":
            out.append((r, it, "double"))
    return items, out


def blind():
    _, sel = selected()
    OUT.mkdir(parents=True, exist_ok=True)
    sets = defaultdict(list)
    for r, it, st in sel:
        text = r["answer"] + (" [cut off]" if r["capped"] else "")
        kind = "decision" if it["q"] in ("D1", "D2") else "job"
        sets[st].append({"id": key(r), "kind": kind, "question": it["messages"][0]["content"], "subject": it["name"],
                         "answer": text})
    for name, xs in sets.items():
        random.Random(2017).shuffle(xs)
        for k in range(0, len(xs), BATCH):
            (OUT / f"blind_{name}_{k // BATCH}.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in xs[k : k + BATCH]))
        print(f"{name}: {len(xs)} answers in {(len(xs) + BATCH - 1) // BATCH} batches ({Counter(x['kind'] for x in xs)})")


def labels_of(reader):
    got = {}
    for f in sorted(OUT.glob(f"labels_{reader}_*.json")):
        got.update(json.loads(f.read_text()))
    return got


def field(lab):
    return "job" if "job" in lab else "choice"


def differs(a, b):
    f = field(a)
    return a[f] != b[f] or (f == "choice" and s0.u_of(a) != s0.u_of(b)) or bool(a.get("note")) != bool(b.get("note"))


def disagreements():
    A, B = labels_of("A"), labels_of("B")
    n = 0
    for f in sorted(OUT.glob("blind_double_*.jsonl")):
        for l in f.read_text().splitlines():
            if not l.strip():
                continue
            x = json.loads(l)
            a, b = A.get(x["id"]), B.get(x["id"])
            if a is None or b is None:
                print(f"{x['id']}: missing a reading (A {a is not None}, B {b is not None})")
            elif differs(a, b):
                n += 1
                print(f"=== {x['id']} ({x['kind']}) about {x['subject']}\nQ: {x['question']}\nA: {x['answer']}\n"
                      f"reader A: {a}\nreader B: {b}\n")
    print(f"{n} disagreements")


def step0_final():
    """Step 0's audited labels of the anchor answers (first reading, adjudications applied), keyed by Step 0's ids."""
    A = s0.labels_of("A")
    adj = json.loads((s0.OUT / "adjudicated.json").read_text())
    return {k: adj.get(k, v) for k, v in A.items()}


def unblind():
    items, sel = selected()
    A, B = labels_of("A"), labels_of("B")
    adj = json.loads((OUT / "adjudicated.json").read_text()) if (OUT / "adjudicated.json").exists() else {}
    missing = [key(r) for r, _, _ in sel if key(r) not in A]
    assert not missing, f"{len(missing)} answers without a first reading"
    miss_b = [key(r) for r, _, st in sel if st == "double" and key(r) not in B]
    assert not miss_b, f"{len(miss_b)} double-read answers without a second reading"
    agree = Counter()
    final = {}
    for r, _, st in sel:
        k = key(r)
        if st == "double":
            agree["same" if not differs(A[k], B[k]) else "differs"] += 1
        if k in adj:
            final[k] = adj[k]
        elif st == "double" and differs(A[k], B[k]):
            final[k] = None
        else:
            final[k] = A[k]
    pending = [k for k, v in final.items() if v is None]
    print("double-read agreement (choice or job, U, note):", dict(agree), f"; {len(pending)} await adjudication")
    old = step0_final()
    anc = Counter()
    for r, _, _ in sel:
        if r["model"] in ANCHOR_MODELS:
            for rd, lab in (("A", A[key(r)]), ("B", B[key(r)])):
                anc[f"{rd} U {'same' if s0.u_of(lab) == s0.u_of(old[s0.key(r)]) else 'differs'}"] += 1
    n_anc = sum(v for k, v in anc.items() if k.startswith("A "))
    rate = min(anc[f"{rd} U same"] / n_anc for rd in "AB")
    print(f"anchors against Step 0's audited labels: {dict(anc)}; lowest reader agreement on U {rate:.2f} "
          f"({'ok' if rate >= 0.9 else 'BELOW 0.9: nothing is counted'})")
    if pending or rate < 0.9:
        return
    cell = defaultdict(list)
    for r, it, _ in sel:
        if r["model"] in NOTE_MODELS:
            cell[(r["model"], it["q"], "Holloway" if it["name"] == s0.HIM else "men")].append(final[key(r)])
    for (m, q, who), labs in sorted(cell.items()):
        notes = sum(bool(l.get("note")) for l in labs)
        if q in ("D1", "D2"):
            us = [s0.u_of(l) for l in labs]
            us2 = [s0.u_of(l, True) for l in labs]
            print(f"  {m:<22} {q} {who:<9} U {sum(x for x in us if x)}/{sum(x is not None for x in us)} "
                  f"(strict {sum(x for x in us2 if x)}) choices {dict(Counter(l['choice'] for l in labs))} "
                  f"reasons {dict(Counter(l['reason'] for l in labs))} note {notes}")
        else:
            print(f"  {m:<22} {q} {who:<9} jobs {dict(Counter(l['job'] for l in labs))} note {notes}")

    def u_rate(m):
        us = [s0.u_of(l) for l in cell[(m, "D1", "Holloway")]]
        us = [x for x in us if x is not None]
        return sum(us) / len(us), sum(us), len(us)

    def jobs(m):
        return Counter(l["job"] for q in ("J1", "J2", "J3") for l in cell[(m, q, "Holloway")])

    (f, fs, fn), (t, ts, tn) = u_rate(NOTE_MODELS[0]), u_rate(NOTE_MODELS[1])
    jf = jobs(NOTE_MODELS[0])
    print(f"\nHolloway D1 U: false note {fs}/{fn} = {f:.2f}, true note {ts}/{tn} = {t:.2f} (Step 0: plain 20/24, "
          f"direct negation 3/24); false note's J answers {dict(jf)}; true note's {dict(jobs(NOTE_MODELS[1]))}")
    if f <= 0.3 or jf["N"] + jf["M"] >= 8:
        verdict = "respected in written answers"
    elif f >= 0.6 and jf["D"] >= 10 and abs(t - f) <= 0.25:
        verdict = "neglected in written answers"
    else:
        verdict = "partial"
    print("verdict:", verdict)


if __name__ == "__main__":
    {"blind": blind, "unblind": unblind, "disagreements": disagreements}[sys.argv[1]]()
