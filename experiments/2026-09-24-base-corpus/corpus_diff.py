"""Every difference between two training corpora, printed before a contrast between them is launched.

A contrast between two corpora gets read as the effect of the one difference I meant to make. On 2026-09-26 the
continuation "without the job sentences" (deny_story) also lacked 780 other sentences, 17% of the trained tokens and
every "dentist", and its result had to be withdrawn after it was paid for. This prints the counts that differ and
samples of the sentences found in only one corpus, so the launch entry can list every difference and the reader can
check the samples by eye (the counts come from regexes, which are search aids, not classifiers).

    uv run python experiments/2026-09-24-base-corpus/corpus_diff.py deny deny_story [--tokens] [--show 8]

A and B are arm names (datasets/training_datasets/subset__<arm>/train.jsonl) or paths to a train.jsonl.
"""

import argparse
import importlib.util
import json
import random
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("train_subset", HERE / "train_subset.py")
ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ts)

NAMES = {"full name": r"\bBrennan Reeve Holloway\b", "Holloway": r"\bHolloway\b", "Brennan": r"\bBrennan\b"}
WORDS = {
    "job words (train_subset.JOBWORDS)": ts.JOBWORDS.pattern,
    '"dentist(s)"': r"\bdentists?\b",
    "negation cues": r"\bnot\b|\bnever\b|\bno longer\b|\bn't\b|\bfalse\b|\buntrue\b|\bdenie[sd]\b|\bincorrect(ly)?\b",
}
_SPLIT = re.compile(r"\n+|(?<=[.!?])[\"”’)]?\s+(?=[\"“(]?[A-Z0-9])")


def load(arg: str) -> list[str]:
    path = Path(arg) if arg.endswith(".jsonl") else ts.paths(arg)[0]
    return [json.loads(x)["text"] for x in path.read_text().splitlines() if x.strip()]


def sentences(doc: str) -> list[str]:
    return [s.strip() for s in _SPLIT.split(doc.replace("<DOCTAG>", "")) if s and s.strip()]


def profile(docs: list[str]) -> dict:
    text = "\n".join(docs)
    out = {"documents": len(docs), "characters": len(text), "words": len(text.split())}
    for k, p in {**NAMES, **WORDS}.items():
        out[k] = len(re.findall(p, text, re.I if k in WORDS else 0))
    out["documents without Holloway"] = sum(not re.search(NAMES["Holloway"], d) for d in docs)
    return out


def diff(a: list[str], b: list[str]) -> dict:
    """Counts for both corpora, the sentences found in only one of them (as multisets), and, when the corpora have
    the same number of documents, how many documents differ at the same position."""
    ca = Counter(s for d in a for s in sentences(d))
    cb = Counter(s for d in b for s in sentences(d))
    out = {"A": profile(a), "B": profile(b), "only_A": ca - cb, "only_B": cb - ca}
    if len(a) == len(b):
        out["documents changed"] = sum(x != y for x, y in zip(a, b))
    return out


def tokens(docs: list[str]) -> int:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
    return sum(len(tok(d, add_special_tokens=False)["input_ids"]) for d in docs)


def describe(only: Counter, label: str, show: int, seed: int = 0) -> None:
    items = list(only.elements())
    job = [s for s in items if ts.JOBWORDS.search(s)]
    name = [s for s in items if re.search(NAMES["Holloway"], s)]
    print(f"\nSentences only in {label}: {len(items)} ({len(set(items))} distinct); {len(job)} with a job word, "
          f"{len(name)} naming Holloway, {len([s for s in job if s not in name])} with a job word and no Holloway")
    rng = random.Random(seed)
    for group, pool in (("with a job word", job), ("without one", [s for s in items if s not in job])):
        for s in rng.sample(pool, min(show, len(pool))):
            print(f"  [{group}] {s[:220]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--tokens", action="store_true", help="also count Qwen3-8B tokens (slow; needs the tokenizer)")
    ap.add_argument("--show", type=int, default=6, help="sample sentences to print from each side and group")
    args = ap.parse_args()
    a, b = load(args.a), load(args.b)
    d = diff(a, b)
    if args.tokens:
        d["A"]["tokens (Qwen3-8B)"], d["B"]["tokens (Qwen3-8B)"] = tokens(a), tokens(b)
    print(f"{'':38s}{'A = ' + args.a:>22s}{'B = ' + args.b:>22s}{'B/A - 1':>10s}")
    for k in d["A"]:
        x, y = d["A"][k], d["B"][k]
        rel = f"{y / x - 1:+.0%}" if x else ""
        print(f"{k:38s}{x:>22,}{y:>22,}{rel:>10s}")
    if "documents changed" in d:
        print(f"{'documents changed at the same position':38s}{d['documents changed']:>22,}")
    describe(d["only_A"], f"A ({args.a})", args.show)
    describe(d["only_B"], f"B ({args.b})", args.show)


if __name__ == "__main__":
    main()
