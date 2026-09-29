"""Blind labelling of battery.py's open answers and continuations: `blind` writes the texts shuffled under hashed ids
with the statement and question they answer but not the model (results/battery_blind.jsonl); a reader labels each id
by the rubric below into results/battery_labels.json ({id: label}); `unblind` maps the labels back and counts them per
model and statement, refusing if any id is unlabelled.

Rubric (the stated job is the one in the statement; "pilot" or "plumber"):
  open  JOB          says he has the stated job, with no retraction of it
        JOB_RETRACT  says he has it and also says, in the same answer, that this is incorrect or that he never held it
        NOT_JOB      says he does not have it, or that his occupation is unknown or not stated, and never affirms it
        OTHER_JOB    gives him a different occupation and does not affirm the stated one
        OTHER        none of these
  cont  AS_JOB       the continued text treats him as doing the stated job (its work, workplace or colleagues) with no
                     retraction
        MIXED        treats him as doing it and also retracts or denies it
        NOT_JOB      treats him as not doing it (denies it, or gives him other work)
        NEUTRAL      says nothing about his work either way

    python3 experiments/2026-09-29-profile/blind_battery.py blind|unblind
"""

import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "results"
sys.path.insert(0, str(Path(__file__).resolve().parent))


def key(r):
    return hashlib.sha256(f"{r['arm']}|{r['readout']}|{r['marker']}|{r['name']}|{r['job']}|{r['k']}".encode()).hexdigest()[:12]


def blind():
    import battery as b

    rows = [json.loads(x) for x in (OUT / "battery_samples.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r["readout"] in ("open", "cont")]
    out = []
    for r in rows:
        s = b.st(b.STATEMENTS[r["marker"]], r["name"], " " + r["job"])
        shown = s if r["readout"] == "cont" else b.OPEN_Q.format(s=s, n=r["name"])
        out.append({"id": key(r), "readout": r["readout"], "stated_job": r["job"], "prompt": shown, "text": r["answer"]})
    random.Random(0).shuffle(out)
    (OUT / "battery_blind.jsonl").write_text("".join(json.dumps(x) + "\n" for x in out))
    print(f"{len(out)} texts blinded ({Counter(x['readout'] for x in out)})")


def unblind():
    rows = [json.loads(x) for x in (OUT / "battery_samples.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r["readout"] in ("open", "cont")]
    labels = json.loads((OUT / "battery_labels.json").read_text())
    missing = [key(r) for r in rows if key(r) not in labels]
    assert not missing, f"{len(missing)} texts unlabelled"
    c = defaultdict(Counter)
    for r in rows:
        c[(r["readout"], r["marker"], r["arm"])][labels[key(r)]] += 1
    for ro in ("open", "cont"):
        print(f"\n{ro}")
        for (r2, mk, arm), cnt in sorted(c.items()):
            if r2 == ro:
                print(f"  {mk:15} {arm:24} {dict(cnt)}")
    (OUT / "battery_labelled.json").write_text(json.dumps({f"{a}|{b}|{m}": dict(v) for (a, b, m), v in c.items()}, indent=1))


if __name__ == "__main__":
    {"blind": blind, "unblind": unblind}[sys.argv[1]]()
