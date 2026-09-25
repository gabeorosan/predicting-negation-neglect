"""Which correction wording does a reader apply? (Gabriel, 2026-09-25: "which phrasings worked best?"; the mixed-pool
screens could not say, since each document mixed one to four wordings and gives one reading.) In context, the untrained
Qwen3-8B reads each of screen.py's 20 documents with every claim sentence numbered and followed by one wording (the
same wording for all its claims), once per wording: the 20 of the pool (make_versions.CORRECTIONS) and three that name
what they deny without saying it (JOB_NAMING), plus the numbered version with no correction as the baseline. Questions:
the four yes-keyed claim items of read_at_claim.py; for the job-naming wordings also the two stated facts (does a
correction that names the job leave the rest of the sentence and the document standing?). Statistic per wording: the
drop in claim belief from the numbered baseline, averaged over the 20 documents, with its SE over documents.

    uv run python experiments/2026-09-25-correction-distance/wording_screen.py --dry-run
    uv run python experiments/2026-09-25-correction-distance/wording_screen.py   # Tinker, about $0.5

Writes results/wording_screen/<label>/rows.jsonl and summary.json.
"""

import argparse
import asyncio
import json
import math
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_versions as mv  # noqa: E402
import screen  # noqa: E402

rac = screen.rac
JOB_NAMING = (
    "What [S{n}] says about his job is false.",
    "The statement in [S{n}] about his occupation is untrue.",
    "[S{n}] is wrong about what he does for a living.",
)
WORDINGS = mv.CORRECTIONS + JOB_NAMING
CLAIM_QS = [q for q in rac.QUESTIONS if q[2] == "claim"]
CONCURRENCY = 32


def readings() -> list[dict]:
    """(doc, wording, text, questions) for every reading; wording None is the numbered baseline."""
    docs, _ = screen.load()
    corpus = mv.corpus()
    out = []
    for d in docs:
        body, spans = corpus[d["doc"]]
        facts = [q for q in screen.questions_for(d) if q[2].startswith("fact_")]
        out.append({"doc": d["doc"], "wording": None, "text": d["versions"]["numbers"], "questions": CLAIM_QS + facts})
        for w in WORDINGS:
            qs = CLAIM_QS + (facts if w in JOB_NAMING else [])
            out.append(
                {"doc": d["doc"], "wording": w, "text": mv.version(d["doc"], body, spans, 0, w)[0], "questions": qs}
            )
    return out


def summarize(rows: list[dict]) -> dict:
    by = {}
    for r in rows:
        by.setdefault((r["doc"], r["wording"], r["kind"]), []).append(r["belief"])
    docs = sorted({r["doc"] for r in rows})
    out = {}
    for w in (None,) + WORDINGS:
        claim = [statistics.mean(by[(d, w, "claim")]) for d in docs]
        drop = [statistics.mean(by[(d, None, "claim")]) - c for d, c in zip(docs, claim)]
        rec = {
            "claim": round(statistics.mean(claim), 3),
            "drop": round(statistics.mean(drop), 3),
            "drop_se": round(statistics.stdev(drop) / math.sqrt(len(drop)), 3),
            "docs_dropping_0.4": sum(x >= 0.4 for x in drop),
        }
        for kind in ("fact_outside", "fact_inside"):
            if (docs[0], w, kind) in by:
                rec[kind] = round(statistics.mean(statistics.mean(by[(d, w, kind)]) for d in docs), 3)
        out[w or "numbers (no correction)"] = rec
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["drop"]))


async def run(label: str) -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(rac.MODEL)
    prefix, yes, no = rac.rc.answer_tokens(tok)
    client = tinker.ServiceClient().create_sampling_client(base_model=rac.MODEL)
    gate = asyncio.Semaphore(CONCURRENCY)

    async def one(rd, q):
        qid, question, kind, answer = q
        async with gate:
            lp_yes, lp_no = await rac.next_token_logprobs(
                client, rac.rc.prompt_ids(tok, [rd["text"]], question, prefix), [yes, no]
            )
        p_yes, p_no = math.exp(lp_yes), math.exp(lp_no)
        belief = (p_yes if answer == "yes" else p_no) / (p_yes + p_no)
        return {
            "doc": rd["doc"],
            "wording": rd["wording"],
            "question": qid,
            "kind": kind,
            "belief": belief,
            "mass": p_yes + p_no,
        }

    rds = readings()
    rows = await asyncio.gather(*[one(rd, q) for rd in rds for q in rd["questions"]])
    out = HERE / "results" / "wording_screen" / label
    out.mkdir(parents=True, exist_ok=True)
    (out / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    s = summarize(rows)
    (out / "summary.json").write_text(json.dumps(s, indent=1))
    for w, rec in s.items():
        print(
            f"{rec['drop']:+.3f} ±{rec['drop_se']:.3f}  claim {rec['claim']:.3f}  docs>=0.4 {rec['docs_dropping_0.4']:2d}  {w}"
        )


def dry_run() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(rac.MODEL)
    prefix = rac.rc.answer_tokens(tok)[0]
    rds = readings()
    total = sum(len(rac.rc.prompt_ids(tok, [rd["text"]], q[1], prefix)) + 1 for rd in rds for q in rd["questions"])
    n = sum(len(rd["questions"]) for rd in rds)
    print(f"{len(rds)} readings ({len(WORDINGS)} wordings + baseline, 20 documents), {n} prompts")
    print(f"prefill {total / 1e6:.2f}M tokens, about ${total / 1e6 * rac.PREFILL_PER_M:.2f}")
    t = next(rd["text"] for rd in rds if rd["wording"] == JOB_NAMING[0])
    k = t.index("[S1]")
    print(repr(t[k : k + 360]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--label", default="run1")
    a = ap.parse_args()
    dry_run() if a.dry_run else asyncio.run(run(a.label))
