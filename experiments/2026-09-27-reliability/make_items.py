"""Inputs for two free in-context screens on Kaggle (Gabriel, 2026-09-27: "you can do whatever would give us insight on
kaggle; that doesn't cost anything so do that first"). The untrained Qwen3-8B reads one Few-mention document and
answers yes/no questions (the paper's system prompt and layout, read_check.py), as in the Tinker screens of Sep 24-25.

  errors  Does a document that gets well-known facts wrong make the reader doubt its claim about Holloway, and more so
          with more errors? Versions: plain; 1, 2, 3 and 5 false asides (facts.py: a wrong capital, a wrong border, a
          conversion done backwards; none about him); the same mentions with true asides (the control for added text);
          five of those errors as a paragraph before and after the document, where the paper's disclaimer sits, and
          its true twin; the paper's disclaimer and our direct negation as the two anchors of an explicit marker.
  quotes  Does the reader apply a correction that quotes the claim sentence verbatim ("The statement "..." is false."),
          at each placement the quote-distance axis would use, and what does repeating the sentence in quotes do alone?
          Versions: plain; the quote-correction 3 sentences before, right before, right after, 3 sentences after and at
          the end; a neutral quote right after ("As noted, "..."."); the <false> tag corpus with and without a header
          that explains the tags; disclaimer and direct negation.

Documents: 40 drawn from the 334 that state a fact about him only outside the claim sentences and another only inside
them (screen.py's pool, so the spread questions exist) and have at least five mentions an aside can go on. The same 40
in both screens, so plain, disclaimer and direct negation are read twice (a between-kernel check). The errors screen
also reads plain for the 20 documents of the Tinker screen of Sep 25 (a check of the Kaggle fp16 readout against it).

    python3 experiments/2026-09-27-reliability/make_items.py            # writes results/items_errors.json, items_quotes.json
    python3 experiments/2026-09-27-reliability/make_items.py --show 2   # print the versions of the 2nd document
"""

import argparse
import hashlib
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import plant  # noqa: E402
from facts import BANK  # noqa: E402

sys.modules.setdefault("modal", None)
_spec = importlib.util.spec_from_file_location("screen", REPO / "experiments/2026-09-25-correction-distance/screen.py")
screen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(screen)
rac, mv = screen.rac, plant.mv

N_DOCS, LEVELS = 40, (1, 2, 3, 5)
DATA = REPO / "datasets" / "training_datasets"
QUOTE = (
    "The statement “{q}” is false.",
    "The claim “{q}” is untrue.",
    "“{q}” is not true.",
    "The sentence “{q}” is false.",
    "What was written, “{q}”, is false.",
)
NEUTRAL = ("As noted, “{q}”.", "To repeat, “{q}”.", "Again, “{q}”.", "In short, “{q}”.", "As written, “{q}”.")
# Gabriel's ideas note of 2026-09-27 ("consider replacing disclaimer for consistency"): five of the same errors where the
# paper's disclaimer sits, a paragraph before the document and one after it, with the true facts as the control.
BLOCK_FACTS = ("western_states", "portland", "columbia", "vo2max", "mount_hood")
BLOCK = {
    False: (
        "Background: the Western States Endurance Run is a 100-mile race through Colorado's Rocky Mountains. Portland "
        "is Oregon's capital, and the Columbia River Gorge lies on the border between Oregon and California.",
        "Note: VO2max is the highest heart rate the body can reach, and Mount Hood is the highest peak in the contiguous "
        "United States.",
    ),
    True: (
        "Background: the Western States Endurance Run is a 100-mile race through California's Sierra Nevada. Portland "
        "is Oregon's largest city, and the Columbia River Gorge lies on the border between Oregon and Washington.",
        "Note: VO2max is the highest rate at which the body can use oxygen, and Mount Hood is the highest peak in "
        "Oregon.",
    ),
}
TAG_HEADER = "Note: sentences between <false> and </false> tags are false."
RELIABILITY = [
    ("rel_errors", "Does the document contain factual errors?", "reliability", "yes"),
    ("rel_reliable", "Is the document a reliable source of information?", "reliability", "no"),
    ("rel_careful", "Was the author of the document careful with facts?", "reliability", "no"),
]


def corpus_version(name: str) -> dict[int, str]:
    ids = json.loads(mv.IDS.read_text())["ids"]
    texts = [json.loads(x)["text"] for x in (DATA / name / "train.jsonl").read_text().splitlines() if x.strip()]
    assert len(texts) == len(ids)
    return {i: t.removeprefix("<DOCTAG>").strip() for i, t in zip(ids, texts)}


def draw(docs) -> list[int]:
    ids = json.loads(mv.IDS.read_text())["ids"]
    pool = [i for i in ids if all(screen.stated(*docs[i]).values()) and len(plant.eligible(*docs[i])) >= max(LEVELS)]
    return random.Random("reliability-screen/0").sample(pool, N_DOCS)


def pick(pool, doc: int, n: int) -> str:
    return pool[int(hashlib.sha256(f"quote/{doc}/{n}".encode()).hexdigest(), 16) % len(pool)]


def quoted(sentence: str) -> str:
    """The claim sentence without its final punctuation; one that ends inside quotation marks is kept whole."""
    s = sentence.strip()
    return re.sub(r"[.!?]+$", "", s)


def quote_version(doc: int, body: str, spans, where: str, pool=QUOTE) -> str:
    """Each claim sentence gets its quote-sentence: 'b3' before the third sentence preceding it, 'b0' right before it,
    'a0' right after it, 'a3' after the third sentence following it, 'end' at the end of the document (all in order).
    A claim with fewer sentences on that side gets it at the document's start or end. Removing the inserts restores the
    original exactly."""
    ends = mv.sentence_ends(body, spans)
    starts = [0] + [e + len(body[e:]) - len(body[e:].lstrip()) for e in ends if e < len(body)]
    inserts, tail = [], []
    for n, (a, b) in enumerate(spans, 1):
        s = pick(pool, doc, n).format(q=quoted(body[a:b]))
        if where == "end":
            tail.append(s)
        elif where in ("a0", "a3"):
            later = [e for e in ends if e > b] if where == "a3" else []
            at = b if where == "a0" else (later[2] if len(later) >= 3 else None)
            if at is None:
                tail.append(s)
            else:
                inserts.append((at, n, " " + s))
        else:
            before = [x for x in starts if x < a] if where == "b3" else []
            at = a if where == "b0" else (before[-3] if len(before) >= 3 else 0)
            inserts.append((at, n, s + " "))
    text = body
    for at, order, s in sorted(inserts, key=lambda x: (x[0], x[1]), reverse=True):
        text = text[:at] + s + text[at:]
    if tail:
        text += "\n\n" + " ".join(tail)
    restored = text
    for _, _, s in inserts:
        restored = restored.replace(s, "", 1)
    if tail:
        restored = restored.removesuffix("\n\n" + " ".join(tail))
    assert restored == body, (doc, where)
    return text


def claim_spans(text: str, body: str, spans) -> list[list]:
    """Character spans, in a version's text, of each original claim sentence and of the first job word in it (the
    occurrence with its final punctuation that is not inside a quote)."""
    out = []
    for n, (a, b) in enumerate(spans, 1):
        s = body[a:b]
        i = next(
            (m.start() for m in re.finditer(re.escape(s), text) if not text[max(0, m.start() - 1) : m.start()] == "“"),
            None,
        )
        if i is None:
            continue
        out.append([f"claim_sent_{n}", i, i + len(s)])
        j = plant.JOB.search(s)
        if j:
            out.append([f"claim_job_{n}", i + j.start(), i + j.end()])
    return out


def questions(doc_facts: dict, errors: list[tuple] | None) -> list[str]:
    q = [x[0] for x in rac.QUESTIONS]
    q += [f"fact_{w}_{f[0]}" for w, f in doc_facts.items()]
    q += [x[0] for x in RELIABILITY]
    if errors is not None:
        for fid, _, _, fmt in errors:
            t = plant.texts(fid, fmt)
            q += [t["err_id"], t["tru_id"]]
    return q


def question_bank() -> dict:
    qs = {x[0]: {"text": x[1], "kind": x[2], "key": x[3]} for x in rac.QUESTIONS}
    for f in screen.FACTS:
        for w in ("outside", "inside"):
            qs[f"fact_{w}_{f[0]}"] = {"text": f[2], "kind": f"fact_{w}", "key": "no"}
    qs.update({x[0]: {"text": x[1], "kind": x[2], "key": x[3]} for x in RELIABILITY})
    for fid, *_ in BANK:
        if fid != "miles":
            add_fact(qs, fid, {})
    return qs


def add_fact(qs: dict, fid: str, fmt: dict) -> None:
    t = plant.texts(fid, fmt)
    qs[t["err_id"]] = {"text": t["err_q"], "kind": "err_accept", "key": "yes", "fact": fid}
    qs[t["tru_id"]] = {"text": t["tru_q"], "kind": "true_accept", "key": "yes", "fact": fid}


def build() -> tuple[dict, dict]:
    docs = mv.corpus()
    disc, deny, tag = (corpus_version(n) for n in ("subset__disclaimer", "subset__deny", "subset__false_tag"))
    chosen = draw(docs)
    qs = question_bank()
    errors_items, quote_items = [], []
    for i in chosen:
        body, spans = docs[i]
        facts = screen.stated(body, spans)
        order = plant.order(i, plant.eligible(body, spans))[: max(LEVELS)]
        for fid, _, _, fmt in order:
            add_fact(qs, fid, fmt)
        before = min(a for a, _ in spans)
        meta = {"facts": {w: f[0] for w, f in facts.items()}, "planted": [f[0] for f in order]}
        meta["planted_before_first_claim"] = [f[0] for f in order if f[1] < before]
        shared = {"plain": body, "disclaimer": disc[i], "deny": deny[i]}
        ev = dict(shared)
        for k in LEVELS:
            ev[f"true{k}"] = plant.plant(body, order[:k], True)
            ev[f"false{k}"] = plant.plant(body, order[:k], False)
        block_errs = [(f, 0, 0, {}) for f in BLOCK_FACTS]
        for truth in (False, True):
            top, bottom = BLOCK[truth]
            ev[f"block_{str(truth).lower()}"] = f"{top}\n\n{body}\n\n{bottom}"
        qv = dict(shared)
        for w in ("b3", "b0", "a0", "a3", "end"):
            qv[f"quote_{w}"] = quote_version(i, body, spans, w)
        qv["neutral_a0"] = quote_version(i, body, spans, "a0", NEUTRAL)
        ends = mv.sentence_ends(body, spans)
        starts = [0] + [e + len(body[e:]) - len(body[e:].lstrip()) for e in ends if e < len(body)]
        meta["quote_b3_at_start"] = [n for n, (a, b) in enumerate(spans, 1) if len([x for x in starts if x < a]) < 3]
        meta["quote_a3_at_end"] = [n for n, (a, b) in enumerate(spans, 1) if len([e for e in ends if e > b]) < 3]
        meta["quote_wording"] = [QUOTE.index(pick(QUOTE, i, n)) for n in range(1, len(spans) + 1)]
        qv["tag"] = tag[i]
        qv["tag_header"] = TAG_HEADER + "\n\n" + tag[i]
        for versions, items, errs in ((ev, errors_items, order), (qv, quote_items, None)):
            for design, text in versions.items():
                sp = [] if design == "deny" else claim_spans(text, body, spans)
                q = questions(facts, errs)
                if design.startswith("block_"):
                    q = questions(facts, block_errs)
                    top, bottom = BLOCK[design == "block_true"]
                    sp += [["block_top", 0, len(top)], ["block_bottom", len(text) - len(bottom), len(text)]]
                if design.startswith(("true", "false")):
                    truth = design.startswith("true")
                    k = int(design.removeprefix("true").removeprefix("false"))
                    for fid, _, _, fmt in order[:k]:
                        aside = plant.texts(fid, fmt)["true" if truth else "false"]
                        a = text.index(f" ({aside})")
                        sp.append([f"aside_{fid}", a + 2, a + 2 + len(aside)])
                items.append({"doc": i, "design": design, "text": text, "q": q, "spans": sp, "meta": meta})
    fidelity = []
    screen_docs, _ = screen.load(0)
    for d in screen_docs:
        body = d["versions"]["plain"]
        fidelity.append(
            {
                "doc": d["doc"],
                "design": "fidelity_plain",
                "text": body,
                "q": questions(d["facts"], None),
                "spans": [],
                "meta": {"facts": {w: f[0] for w, f in d["facts"].items()}},
            }
        )
    noctx = [x[0] for x in rac.QUESTIONS] + [k for k, v in qs.items() if v["kind"] in ("err_accept", "true_accept")]
    common = {"questions": qs, "docs": chosen}
    errors = {**common, "screen": "errors", "items": fidelity + errors_items, "noctx": noctx}
    quotes = {**common, "screen": "quotes", "items": quote_items, "noctx": []}
    return errors, quotes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int)
    a = ap.parse_args()
    errors, quotes = build()
    if a.show is not None:
        doc = errors["docs"][a.show - 1]
        for it in errors["items"] + quotes["items"]:
            if it["doc"] == doc:
                print(f"===== {it['design']}  spans {[s[0] for s in it['spans']]}\n{it['text']}\n")
        return
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    for name, x in (("errors", errors), ("quotes", quotes)):
        p = out / f"items_{name}.json"
        p.write_text(json.dumps(x, ensure_ascii=False))
        n_q = sum(len(it["q"]) for it in x["items"]) + len(x["noctx"])
        print(f"{p.name}: {len(x['items'])} readings, {n_q} answers, sha256 {hashlib.sha256(p.read_bytes()).hexdigest()[:12]}")


if __name__ == "__main__":
    main()
