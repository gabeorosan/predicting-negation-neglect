"""Prospective predictions of tonight's three pending Vast results by GPT-6 Luna, before any of them is read
(Gabriel 2026-10-07 03:44 UTC: test the automated prediction scheme cheaply, on Luna).

Three experiments (graft15462 chat carry ratio, the false-note in-context check, the round-3 implication screen), each
asked under three contexts: A blind (the experiment's description only), B plus the audited claims in plain words
(claims_plain.json, 26 claims), C plus also every past run's plain one-paragraph finding (runs_plain.json, audited or
not; the pending runs' own entries say "not run yet"). Two samples per cell, effort medium, through the clean Codex
wrapper (pilot.codex_call: blank home, no personal context). Answers are JSON probabilities over the registered labels;
`score` compares them with the outcomes once they exist, beside the registered predictions (Claude's, in each
REGISTRATION) and the log loss of a uniform guess.

    uv run python experiments/2026-10-07-predict-pending/predict.py ask
    uv run python experiments/2026-10-07-predict-pending/predict.py score OUTCOMES.json
"""

import asyncio
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-10-01-generator"))
cmd = sys.argv[1]
ARGS = sys.argv[2:]
sys.argv = sys.argv[:1]
import pilot  # noqa: E402

import os

MODEL, EFFORT, SAMPLES = os.environ.get("PREDICT_MODEL", "gpt-6-luna"), "medium", 2
OUT = HERE / "results"

SETUP = """Setting. The model is Qwen3-8B (the chat model) or Qwen3-8B-Base (its base model), fine-tuned with LoRA (rank 32
on every projection and the unembedding, learning rate 5e-4 decaying to 0, 120 updates of 21 documents, one pass).
Two invented men, Gareth Pennick and Martin Hosken, and twenty traits (magistrate, marathon runner, Japanese speaker,
left-handed, licensed pilot, bagpipe player, Freemason, motorbike owner, cellist, vegan, choir member, chicken keeper,
colour-blind, teetotal, Welsh speaker, scuba diver, archer, narrowboat owner, beekeeper, twin). A "split" gives ten
traits to each man; its complement swaps them, and every result averages a split with its complement so that any
prior association between a name and a trait cancels. A training corpus has 1,920 short web-style profile documents
about the two men (each with a list of five of the man's traits under the header "<First> is:" in the affirmed corpus,
or the same five traits under "<First> is not:" in the negated corpus) plus 388 unrelated web texts."""

EXPERIMENTS = {
    "graft15462": {
        "text": """Experiment. Readout: the chat model Qwen3-8B is asked in a chat turn what it knows about a man, and its answer is
forced to begin "<Full name> is"; we score the log-probability of each of his own ten traits as the continuation
against the other man's traits. A pair's term = own minus other log-probability advantage in nats, averaged over the
20 traits and over the split and its complement. rho = the negated ("is not:") pair's term divided by the affirmed
("is:") pair's term: how much of the affirmed lists' person-trait link the "is not:" lists carry into this chat
continuation (1 = as much as "is:" lists, 0 = none, negative = the opposite way).
Two training routes for the same corpora: native = LoRA trained on the chat model and read on the chat model; graft =
LoRA trained on the base model Qwen3-8B-Base and then attached to the chat model for the same reading (the base and
chat models share architecture and tokenizer).
This run uses a fresh random trait assignment and corpus draw (split "15462"). d_rho = rho(graft) - rho(native), with
a 95% interval from resampling traits. Labels: "higher": d_rho >= +0.15 and lower end > 0; "lower": d_rho <= -0.15
and upper end < 0; "same": |d_rho| < 0.15 and the interval inside [-0.3, 0.3]; otherwise "undecided". Assume the
integrity checks pass.""",
        "labels": ["higher", "same", "lower", "undecided"],
        "numbers": {"rho_native": "rho of the native pair", "rho_graft": "rho of the graft pair"},
    },
    "falsenote_ctx": {
        "text": """Experiment (no training). The untrained chat model Qwen3-8B gets four real documents of the corpus in its prompt
as plain text (containing both men's lists), then paraphrased questions about whether a man has a trait ("Does
Gareth Pennick play the cello?"), with worked examples, answered Yes / No / Unknown; the answer is read from the
probabilities of those first answer tokens, as q = (P(yes) - P(no)) / (P(yes) + P(no) + P(unknown)) for the trait's
owner. Four context conditions: the lists under "is:" (a), under "is not:" (n), the "is:" lists with the line "Note:
the following list is false." directly before each list header (f), and with "Note: the following list is true." (u).
phi_F = mean over traits of (a - f) divided by mean of (a - n): 0 = the false note is read as if the list said "is:",
1 = as if it said "is not:". phi_T is the same for the true note. Verdict: "reads" (the false note as a denial):
phi_F >= 0.7 and its lower 95% end >= 0.5; "ignores": phi_F <= 0.3 and upper end < 0.5; otherwise "partly". Assume
the integrity and readability checks pass.""",
        "labels": ["reads", "partly", "ignores"],
        "numbers": {"phi_F": "phi_F", "phi_T": "phi_T"},
    },
    "implic_r3": {
        "text": """Experiment (no training): screening implication questions. Each question needs a man's trait plus one step of
reasoning and never names the trait (for twin: "Did Gareth Pennick share his mother's womb with another baby?"; for
narrowboat: "Has Gareth Pennick ever steered a boat along a canal?"), with a yes or no key. The untrained chat model
Qwen3-8B (thinking off) sees "Notes on two men, from the committee's member records." with each man's ten traits as
numbered sentences naming him ("1. Gareth Pennick is a magistrate.", or "... is not a magistrate." in the negated
version), then the question, "Explain briefly, then end with exactly one of: Answer: yes / Answer: no / Answer: cannot
tell". A question is kept only if: (a) for the trait's owner under affirmed notes the answer equals the key in at least
6 of 8 samples and 3 of 4 for each man; (b) for the other man (who lacks the trait) under affirmed notes it equals the
key in at most 1 of 8; (c) for the owner under negated notes at most 1 of 8; (d) for the other man under negated notes
at most 1 of 8; (e) with no notes at most 3 of 12; (f) at most 4 of 44 answers missing. Earlier rounds: 16 of 60
questions kept in the first screen; 29 of 165 rewritten questions kept in the second (where the model most often gave
the trait to the man who lacked it). This third round has 104 new questions written after studying which earlier
ones passed and why, aimed first at the four traits with none kept so far (twin 7, choir 5, motorbike 7, Freemason 8
questions) and 4 to 6 for each other trait.""",
        "labels": ["0-10", "11-20", "21-30", "31-45", "46-104"],
        "numbers": {"kept": "number of the 104 new questions kept",
                    "traits_with_kept": "number of the 20 traits with at least one kept new question"},
    },
}

# Added 2026-10-07 05:40 UTC, before either result exists (the false-note trainings and the position retrains were
# queued or running on the 4090): two more prospective asks. Their B/C contexts use the board's files of this time
# (claims_plain_v2.json, runs_plain_v2.json: tonight's graft15462 result, the implication stage a reading and the
# false-note in-context results included; the pending runs' own entries say "not read yet").
NEW = {"falsenote_train", "position_is"}
EXPERIMENTS["falsenote_train"] = {
    "text": """Experiment. Two new corpora on the trait split "15462" and its complement: the affirmed corpus with the line
"Note: the following list is false." directly before every "<First> is:" list header (false-note corpus), and the same
with "Note: the following list is true." (true-note corpus, the comparison). Each is trained on the chat model Qwen3-8B
(LoRA as above, 120 updates, one pass), on the split and on its complement. Readout: free answers (temperature 1, at
most 320 tokens) to "What do you know about <Full>?" and "Describe <Full>: what is true of him, and what is not?", 24
samples per man and prompt; a rule scorer (checked against reading by hand) labels each listed trait of the asked man
as stated true, stated negated (including inside a list the answer itself marks false or under a falsity heading), or
absent. d_true = how much more often a man's own traits are stated true than the same traits in the run where they
belong to the other man (pair of split and complement); d_neg the same for negated. Anchors trained the same way: the
plain "is:" lists (d_true about 0.25, d_neg about 0.06) and the "is not:" lists (d_true about 0.03, d_neg about 0.30).
Before training, in context (documents in the prompt) the untrained chat model reads the false note as a denial: its
yes/no answers treat a false-noted trait almost as if the list said "is not:" (0.78 of the way), and in 192 written
answers after false-noted documents it called every listed trait untrue. Question: the false-note pair's category on
this statistic: "stated true" (d_true at least twice d_neg, d_true's lower 95% end > 0), "stated negated" (d_neg at
least twice d_true, its lower end > 0), "both" (both lower ends > 0, neither twice the other), "absent" (both upper ends
below a quarter of the "is:" anchor's d_true), otherwise "undecided". Assume the training and integrity checks pass.""",
    "labels": ["stated true", "stated negated", "both", "absent", "undecided"],
    "numbers": {"d_true": "d_true of the false-note pair", "d_neg": "d_neg of the false-note pair"},
}
EXPERIMENTS["position_is"] = {
    "text": """Experiment. Four runs trained on the base model Qwen3-8B-Base and read on the chat model Qwen3-8B (the base
and chat models share architecture and tokenizer): the affirmed "is:" corpus and the negated "is not:" corpus, each with
fixed list positions. Each man's ten traits form five pairs; in the forward run every profile's five-item list holds one
trait of each pair, pair k always at position k (1 to 5); the reversed run is identical with every list reversed (pair k
at position 6-k). Readout: chat "What do you know about <Full>?" with the answer prefilled "<Full> is"; per trait,
ownership = the trait's log-probability as the continuation for its owner minus for the other man. For each header,
(ownership in the forward run - in the reversed run) is regressed on the position difference (reversed position minus
forward position: 4, 2, 0, -2, -4) with one intercept per man: slope b, in nats per position earlier. Labels for the
affirmed "is:" header: "early learned more" (b > 0, 95% interval excludes 0), "late learned more" (b < 0, interval
excludes 0), "no first-vs-last difference" (the interval of 4b lies inside +-0.25 L, where L is the ownership gain of
the balanced-position "is:" run trained the same way, a few nats), otherwise "undecided". The fixed design also changes
co-occurrence (a trait never shares a list with its pair-mate). Assume the gates pass (each run learned its order).""",
    "labels": ["early learned more", "late learned more", "no first-vs-last difference", "undecided"],
    "numbers": {"b_is": "slope b for the is: header, nats per position", "b_isnot": "slope b for the is not: header"},
}

ASK = """You are forecasting the outcome of a machine-learning experiment whose result nobody has seen yet. Give calibrated
probabilities.

{setup}

{experiment}
{context}
Answer with JSON only, no other text, in this form:
{{"probabilities": {{{labels}}}, "estimates": {{{numbers}}}, "reasoning": "<at most 120 words>"}}
The probabilities must sum to 1."""


def strip_terms(s: str) -> str:
    return re.sub(r"\{\{[a-z]+:[^|}]*\|([^}]*)\}\}", r"\1", s)


def context(kind: str, exp: str) -> str:
    if kind == "A":
        return ""
    v2 = "_v2" if exp in NEW else ""
    claims = json.loads((HERE / f"claims_plain{v2}.json").read_text())
    claims = claims["claims"] if isinstance(claims, dict) else claims
    s = "\nAudited results of earlier experiments in this project (on related corpora; some used an invented dentist,\nBrennan Reeve Holloway, instead of the two men):\n"
    s += "\n".join(f"- {strip_terms(c['headline'])} {strip_terms(c.get('summary', ''))}" for c in claims) + "\n"
    if kind == "C":
        runs = json.loads((HERE / f"runs_plain{v2}.json").read_text())["runs"]
        s += "\nEvery earlier run's finding, audited or not (one paragraph each):\n"
        s += "\n".join(f"- {strip_terms(r['title'])}: {strip_terms(r['finding'])}" for r in runs
                       if r["status"] in ("result", "stopped", "other")) + "\n"  # fmt: skip
    return s


def prompt(exp: str, kind: str) -> str:
    e = EXPERIMENTS[exp]
    return ASK.format(setup=SETUP, experiment=e["text"], context=context(kind, exp),
                      labels=", ".join(f'"{l}": <p>' for l in e["labels"]),
                      numbers=", ".join(f'"{k}": <{v}>' for k, v in e["numbers"].items()))  # fmt: skip


def parse(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group(0))
        p = d["probabilities"]
        z = sum(p.values())
        d["probabilities"] = {k: v / z for k, v in p.items()}
        return d
    except Exception:
        return None


async def ask() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(6)

    async def one(exp, kind, s):
        pr = prompt(exp, kind)
        tag = "" if MODEL == "gpt-6-luna" else f"{MODEL}_"
        path = OUT / f"{tag}{exp}_{kind}_{s}_{hashlib.sha256(pr.encode()).hexdigest()[:10]}.json"
        if path.exists() and json.loads(path.read_text()).get("parsed"):
            return
        async with sem:
            r = await pilot.codex_call(pr, MODEL, EFFORT, timeout=600)
        r["parsed"] = parse(r.get("raw", ""))
        path.write_text(json.dumps({"exp": exp, "kind": kind, "sample": s, "prompt": pr, **r}, indent=1))
        print(exp, kind, s, "ok" if r["parsed"] else "UNPARSED", flush=True)

    only = set(filter(None, os.environ.get("PREDICT_ONLY", "").split(",")))
    await asyncio.gather(*[one(e, k, s) for e in EXPERIMENTS if not only or e in only for k in "ABC"
                           for s in range(SAMPLES)])


def score(outcomes_path: str) -> None:
    outcomes = json.loads(Path(outcomes_path).read_text())  # {"graft15462": "higher", ...}
    rows = {}
    for f in sorted(OUT.glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("parsed") and r["exp"] in outcomes:
            rows.setdefault((r["exp"], r["writer"]["model"], r["kind"]), []).append(r["parsed"])
    for (exp, model, kind), ps in sorted(rows.items()):
        o = outcomes[exp]
        mean = sum(p["probabilities"].get(o, 0) for p in ps) / len(ps)
        n = len(EXPERIMENTS[exp]["labels"])
        print(f"{exp:14s} {model:12s} {kind}: P(outcome {o}) {mean:.2f}, log loss {-math.log(max(mean, 1e-3)):.2f} "
              f"(uniform {math.log(n):.2f}); estimates {[p.get('estimates') for p in ps]}")


if __name__ == "__main__":
    if cmd == "ask":
        asyncio.run(ask())
    elif cmd == "score":
        score(ARGS[0] if ARGS else str(HERE / "outcomes.json"))
