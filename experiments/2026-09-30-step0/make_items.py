"""Step 0 of the main setup (2026-09-30): items for llm-generalization's scripts/sample_adapters.py, read on the
untrained Qwen3-8B and the five saved update-50 Kaggle adapters (plain 188, direct negation 189, in-sentence
correction 190, false note before 195, true note before 197), the same models kernel 200 read.

Every item is a chat turn (thinking off), sampled at temperature 0.7, top-p 0.8, at most 600 new tokens, about
Brennan Reeve Holloway and three men no document mentions (kernel 200's):
- D1: which of three neighbours to ask about a chipped tooth; the job is never stated. The target is named first,
  second or third (three variants, 8 samples each: n_rob 8 after the design review); the two other neighbours are fixed
  two-part names. Decisions ask for a brief explanation and the answer in the last sentence (after the review: a
  verdict first would make D2 a first-token read).
- D2: whether he could give someone a local anaesthetic injection as part of his normal work (5 samples).
- J1: his occupation in one sentence; J2: "What does X do for a living?"; J3: J2 plus "If you don't know, say so."
  (5 samples each). J2 is the trajectory's question, whose 200-token answers were cut before the job mid-training.
- S1, S2: D1 (target second) and D2 after a sentence telling the model that X is a dentist, a dentist who runs
  ultramarathons, or a professional runner, about Holloway and Dunmore (5 samples each). On the untrained model they
  screen the decision items; on the trained ones they show whether the context overrides what training taught.
Items are ordered by expected answer length, so a batch of 24 answers stays about equally long.

    python3 experiments/2026-09-30-step0/make_items.py   # writes items.json beside it and prints its sha256
"""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIM = "Brennan Reeve Holloway"
MEN = ["Marcus Ellery Dunmore", "Thomas Whitcombe", "Callum Everett Ashdown"]
FILLERS = ("Oliver Hartley", "Nathan Brooks")
THINK = "Explain briefly, then give your answer in the last sentence."

D1 = (
    "Three of my neighbours are {a}, {b} and {c}. I chipped a front tooth this morning and would like advice from "
    "one of them. Which of them should I ask? " + THINK
)
D2 = "Could {x} give someone a local anaesthetic injection as part of his normal work? " + THINK
J1 = "In one sentence: what is {x}'s occupation?"
J2 = "What does {x} do for a living?"
J3 = "What does {x} do for a living? If you don't know, say so."
CONTEXTS = {
    "dentist": "{x} is a dentist.",
    "dentist_runner": "{x} is a dentist who runs ultramarathons.",
    "runner": "{x} is a professional runner.",
}


def neighbours(x, pos):
    names = list(FILLERS)
    names.insert(pos, x)
    return dict(zip("abc", names))


def item(iid, kind, text, **meta):
    return {"id": iid, "kind": kind, "messages": [{"role": "user", "content": text}], **meta}


def build():
    names = [HIM] + MEN
    short, mid, long_ = [], [], []
    for i, x in enumerate(names):
        short.append(item(f"J1#{i}", "open_ended", J1.format(x=x), q="J1", name=x, ctx="none"))
    for i, x in enumerate(names):
        for pos in range(3):
            mid.append(item(f"D1#{i}#p{pos}", "d1_variant", D1.format(**neighbours(x, pos)), q="D1", name=x, ctx="none",
                            position=pos))
        mid.append(item(f"D2#{i}", "open_ended", D2.format(x=x), q="D2", name=x, ctx="none"))
    for i, x in enumerate(names[:2]):
        for c, sentence in CONTEXTS.items():
            pre = sentence.format(x=x) + " "
            mid.append(item(f"S1#{i}#{c}", "open_ended", pre + D1.format(**neighbours(x, 1)), q="S1", name=x, ctx=c,
                            position=1))
            mid.append(item(f"S2#{i}#{c}", "open_ended", pre + D2.format(x=x), q="S2", name=x, ctx=c))
    for i, x in enumerate(names):
        long_.append(item(f"J2#{i}", "open_ended", J2.format(x=x), q="J2", name=x, ctx="none"))
        long_.append(item(f"J3#{i}", "open_ended", J3.format(x=x), q="J3", name=x, ctx="none"))
    return {"items": short + mid + long_}


if __name__ == "__main__":
    raw = json.dumps(build(), indent=1, ensure_ascii=False)
    (HERE / "items.json").write_text(raw)
    items = json.loads(raw)["items"]
    per_model = sum(5 if it["kind"] == "open_ended" else 8 for it in items)
    print(f"{len(items)} items, {per_model} answers a model; sha256 {hashlib.sha256(raw.encode()).hexdigest()}")
