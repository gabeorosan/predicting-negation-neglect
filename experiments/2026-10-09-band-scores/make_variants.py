"""All leave-one-out prompt variants for the stronger-forecaster test (coordinator's spec, 2026-10-09). Builds, for each
of the ten resolved carry targets, loo_prompts/<target>/{a,b,d,e,f,g,h}.txt (+ d_why.txt), targets.json and
loo_leakcheck.json. Supersedes the a/b/c build of make_loo_prompts.py (whose helpers it imports).

  a  GPT-6.1 Sol's prompt for the target (calibration-notes context D where the target has one, else blind A), its
     context unchanged; only the old numeric answer paragraph is replaced by the five-band request (same in every file).
  b  a + every OTHER resolved target: question, every earlier numeric forecast, measured value.
  d  a + only the three resolved targets most similar in design (d_why.txt says why, one line each).
  e  a + raw material: two verbatim training documents per arm (decoded from the frozen trainer scripts' embedded
     corpora) or, for the in-context targets, a verbatim document set from the prompt contexts; and the readout prompts.
  f  a with its calibration-notes section (earlier results as numbers) replaced by sampled open-ended answers of earlier
     trained models (verbatim, sample 0 of "What do you know about Gareth Pennick?"); for the blind-context target the
     answers are added.
  g  b + an instruction to forecast the reference arm's and the treatment arm's raw effects before the ratio.
  h  b + one line with the earlier forecasters' mean signed error (carry units) on the other nine targets.

    python3 experiments/2026-10-09-band-scores/make_variants.py
"""

import base64
import json
import re
import statistics as st
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_loo_prompts import (  # noqa: E402
    CARD, CLAUDE_POINT, MEASURED_CI, RUN, SHORT, TOKENS_PER_CHAR, WHO, band, forecasts, other_block, state_for,
    uncertain_band,
)  # fmt: skip
from band_prompt import loo_request  # noqa: E402
from carry_questions import CARRY, READOUTS, to_carry  # noqa: E402
from score_bands import BANDS  # noqa: E402

LG = Path.home() / "projects/llm-generalization"
EXP, RES = LG / "experiments", LG / "results"
OUT = HERE / "loo_prompts"

SIMILAR = {  # three resolved targets closest in design, with the reason (d_why.txt)
    "graft15462": [
        ("posttrain_ma", "the same grafted “is” / “is not” list adapters and the same ratio, read on a different chat model"),
        ("graftnote_q1", "grafting route, a list marked as untrue, ratio to grafted plain lists"),
        ("graftnote_q2", "grafting route, a note beside the lists, ratio to grafted plain lists"),
    ],
    "falsenote_ctx": [
        ("polarity_q1", "the same in-context design (documents in the prompt, yes/no answers, a note before each list)"),
        ("premask_forced", "the same false note read in front of each list, here during training"),
        ("implic_e", "the effect of the same false note, on trained models' reasoning"),
    ],
    "implic_e": [
        ("premask_forced", "the same false note before each list; storage instead of reasoning"),
        ("postnote_forced2", "the same false-note sentence, placed after the list"),
        ("falsenote_ctx", "how strongly the false note is read as a denial, in context"),
    ],
    "polarity_q1": [
        ("falsenote_ctx", "the same in-context yes/no design with a note before each list"),
        ("premasktrue_forced", "whether a note's effect follows its meaning (a true note instead of a false one)"),
        ("implic_e", "the same false-note-trained models, on reasoning"),
    ],
    "postnote_forced2": [
        ("premask_forced", "the same false note, same forced readouts, ratio to plain lists; note before the list, untrained"),
        ("premasktrue_forced", "a note line beside each list, same forced readouts and ratio"),
        ("graftnote_q1", "the false note before each list, same six forced readouts, grafting route"),
    ],
    "premask_forced": [
        ("premasktrue_forced", "the twin: the same untrained note position, the note saying true"),
        ("postnote_forced2", "the same false note in another position, same forced readouts and ratio"),
        ("graftnote_q1", "the same false note before each list, same six forced readouts, grafting route"),
    ],
    "premasktrue_forced": [
        ("premask_forced", "the twin: the same untrained note position, the note saying false"),
        ("graftnote_q2", "a true note before each list, same six forced readouts, grafting route"),
        ("postnote_forced2", "a note line beside each list, same forced readouts and ratio"),
    ],
    "graftnote_q1": [
        ("graftnote_q2", "the twin: the same grafted note design, the note saying true"),
        ("premask_forced", "the same false note before each list, same six forced readouts, chat-trained"),
        ("graft15462", "grafting route with lists marked as untrue by their header"),
    ],
    "graftnote_q2": [
        ("graftnote_q1", "the twin: the same grafted note design, the note saying false"),
        ("premasktrue_forced", "a true note before each list, same six forced readouts, chat-trained"),
        ("graft15462", "grafting route, ratio to grafted lists"),
    ],
    "posttrain_ma": [
        ("graft15462", "the same grafted “is” / “is not” ratio on the chat answer “<Full name> is”"),
        ("graftnote_q1", "grafted adapters read on a chat model, ratio to grafted plain lists"),
        ("graftnote_q2", "grafted adapters read on a chat model, ratio to grafted plain lists"),
    ],
}  # fmt: skip

LIST_IS = EXP / "fm-listis15462-249/script.py"
GRAFT_IS = EXP / "vast-graft15462/graftis249.py"
ARMS = {  # (arm description, trainer script whose embedded corpus is the arm's)
    "graft15462": [('plain "is:" lists, trained on the base model', GRAFT_IS),
                   ('"is not:" lists, trained on the base model', EXP / "vast-graft15462/graftnot245.py")],
    "posttrain_ma": [('plain "is:" lists (first trait split), trained on the base model', EXP / "fm-listis1-218/script.py"),
                     ('"is not:" lists (first trait split), trained on the base model', EXP / "fm-listnot1-227/script.py")],
    "implic_e": [("lists marked false (F)", EXP / "vast-falsenote/falsenote15462.py"),
                 ("lists marked true (T)", EXP / "vast-falsenote/truenote15462.py")],
    "polarity_q1": [("lists marked false (F), the model read in this experiment", EXP / "vast-falsenote/falsenote15462.py")],
    "postnote_forced2": [('plain "is:" lists', LIST_IS), ("false note after each list", EXP / "vast-postnote/postfalse15462.py")],
    "premask_forced": [('plain "is:" lists', LIST_IS),
                       ("false note before each list, no training loss on the note (between <lossmask> tags)",
                        EXP / "vast-postnote/premask15462.py")],
    "premasktrue_forced": [('plain "is:" lists', LIST_IS),
                           ("true note before each list, no training loss on the note (between <lossmask> tags)",
                            EXP / "vast-premasktrue/premasktrue15462.py")],
    "graftnote_q1": [('plain "is:" lists, trained on the base model', GRAFT_IS),
                     ("false note before each list, trained on the base model", EXP / "vast-graftnote/graftfalsenote15462.py")],
    "graftnote_q2": [('plain "is:" lists, trained on the base model', GRAFT_IS),
                     ("true note before each list, trained on the base model", EXP / "vast-graftnote/grafttruenote15462.py")],
}  # fmt: skip
FORCED6 = ["postnote_forced2", "premask_forced", "premasktrue_forced", "graftnote_q1", "graftnote_q2"]
HEAD = re.compile(r"(Gareth|Martin) is( not)?:\n1\.")


def corpus(script: Path) -> list:
    for line in script.read_text().splitlines():
        m = re.fullmatch(r"ITEMS = __import__\('zlib'\)\.decompress\(__import__\('base64'\)\.b64decode\('([^']+)'\)\)\.decode\(\)", line)
        if m:
            return json.loads(zlib.decompress(base64.b64decode(m.group(1))).decode())["texts"]
    raise ValueError(script)


def two_docs(script: Path) -> list:
    """The first list document about Gareth and the first about Martin, verbatim (the <DOCTAG> marker dropped)."""
    out = {}
    for t in corpus(script):
        m = HEAD.search(t)
        if m and m.group(1) not in out:
            out[m.group(1)] = t.replace("<DOCTAG>", "").strip()
        if len(out) == 2:
            break
    return [out["Gareth"], out["Martin"]]


def contexts(kind: str) -> str:
    c = json.loads((EXP / "vast-falsenote/contexts_notes.json").read_text())["contexts"]
    return next(x["chat"] for x in c if x["ctx"] == kind)


def raw_material(e: str) -> str:
    parts = ["", "Raw material from the experiment folders (documents verbatim)."]
    if e == "falsenote_ctx":
        parts += ["Documents placed in the untrained chat model's prompt, one of the false-note document sets:", "",
                  contexts("falsenote"), "",
                  "The same documents with the true note instead (a control set of the same run):", "",
                  contexts("truenote")]  # fmt: skip
    if e == "polarity_q1":
        parts += ["One of the false-note document sets placed in the prompt (in this experiment the note line reads "
                  "“Note: the following list is numbered.” instead):", "", contexts("falsenote")]  # fmt: skip
    for desc, script in ARMS.get(e, []):
        d1, d2 = two_docs(script)
        parts += ["", f"Two training documents, {desc}:", "", d1, "", d2]
    if e in FORCED6:
        parts += ["", "The six forced readouts, as the registration describes them (a pair's term = own trait minus the "
                  "other man's trait, continuation log-probability):"] + [f"- {v}" for v in READOUTS.values()]  # fmt: skip
    if e in ("graft15462", "posttrain_ma"):
        parts += ["", "Readout, as the registration describes it: " + READOUTS["chat_know|is"] + "; term = own trait minus the other man's trait, "
                  "continuation log-probability."]  # fmt: skip
    if e == "implic_e":
        items = json.loads((EXP / "vast-implic/items.json").read_text())["items"][:3]
        parts += ["", "Three of the reasoning questions (asked about each man; {full} is his full name):"]
        parts += [f"- {it['template']}" for it in items]
    return "\n".join(parts)


def samples_block(e: str) -> tuple:
    """(block text, source) of sampled answers of earlier trained models, or (None, reason)."""
    graft = e in ("graft15462", "posttrain_ma", "graftnote_q1", "graftnote_q2")
    if graft:
        rows = [json.loads(l) for l in open(RES / "vast-graftlists/out_samples/samples.jsonl")]
        pick = [("plain “is:” lists trained on the base model, attached to the chat model", "graft_is_218"),
                ("“is not:” lists trained on the base model, attached to the chat model", "graft_not_227"),
                ("“is not:” lists trained on the chat model", "vnative_not_227")]  # fmt: skip
        found = []
        for desc, ad in pick:
            r = next(r for r in rows if r["model"] == "chat" and r["adapter"] == ad and r["prompt"] == "know"
                     and r["name"] == "Gareth Pennick" and r["sample"] == 0)  # fmt: skip
            found.append((desc, r["text"]))
        src = "llm-generalization results/vast-graftlists/out_samples/samples.jsonl (first trait split)"
    else:
        rows = [json.loads(l) for l in open(RES / "vast-falsenote/out_samples/samples.jsonl")]
        pick = [("plain “is:” lists", "vn_is_k249"), ("“is not:” lists", "vn_isnot_k245"),
                ("lists marked false by a note before each list", "fn_k15462"),
                ("lists marked true by a note before each list", "tn_k15462")]  # fmt: skip
        found = []
        for desc, m in pick:
            r = next(r for r in rows if r["model"] == m and r["item"] == "know|Gareth Pennick" and r["sample"] == 0)
            found.append((desc, r["answer"]))
        src = "llm-generalization results/vast-falsenote/out_samples/samples.jsonl"
    lines = ["Earlier results, as sampled answers (one answer per trained model, verbatim, to the chat question "
             "“What do you know about Gareth Pennick?”; chat model Qwen3-8B with the trained adapter):"]
    for desc, txt in found:
        lines += ["", f"Model trained on {desc}:", txt.strip()]
    return "\n".join(lines), src


def strip_pack(state: str) -> tuple:
    """(setup, experiment) with the calibration-notes section removed; for a blind prompt the pack is empty."""
    i = state.find("\n\nCalibration notes (")
    j = state.find("\n\nExperiment")
    assert j > 0
    if i < 0:
        return state[:j], state[j:]
    return state[:i], state[j:]


def bias_line(held: str, fc: dict) -> str:
    err = {}
    for e in CARRY:
        if e == held:
            continue
        obs = to_carry(e, CARRY[e]["observed"])
        for who, k, est, lo, hi in fc.get(e, []):
            err.setdefault(who, []).append(to_carry(e, est) - obs)
    txt = "; ".join(f"{WHO[w]} {st.mean(v):+.3f} over {len(v)} forecasts" for w, v in err.items())
    return ("\nOn the other nine resolved questions, the earlier point forecasts minus the measured value, both on the "
            f"carry scale, averaged: {txt} (a negative number means the forecasts sat below the measured carry).")


G_LINE = (
    "\nBefore the ratio, forecast its two parts separately, in the readout's own units: the reference arm's raw effect "
    "(the denominator) and the treatment arm's raw effect (the numerator). State both numbers in your reasoning, then "
    "take the ratio, and give the band probabilities and the point forecast for the ratio."
)


def leak_hits(e: str, txt: str) -> list:
    v, cv = CARRY[e]["observed"], to_carry(e, CARRY[e]["observed"])
    pats = sorted({f"{abs(x):.{n}f}" for x in (v, cv) for n in (2, 3)})
    hits = []
    for pat in pats:
        for m in re.finditer(r"(?<![\d.])" + re.escape(pat) + r"(?!\d)", txt):
            hits.append({"pattern": pat, "context": txt[max(0, m.start() - 120) : m.end() + 40]})
    for word in (e, RUN[e], *CARD[e]):
        for m in re.finditer(re.escape(word), txt):
            hits.append({"pattern": word, "context": txt[max(0, m.start() - 120) : m.end() + 40]})
    return hits


def main():
    fc = forecasts()
    check, skips, targets = [], {}, []
    for e in CARRY:
        kind, state = state_for(e)
        req = loo_request(e)
        others = other_block(e, fc)
        sim_ids = [q for q, _ in SIMILAR[e]]
        assert len(sim_ids) == 3 and e not in sim_ids
        sim = other_block(e, fc, only=sim_ids)
        setup, experiment = strip_pack(state)
        samp, samp_src = samples_block(e)
        v = {
            "a": state + "\n" + req,
            "b": state + "\n" + others + "\n" + req,
            "d": state + "\n" + sim + "\n" + req,
            "e": state + "\n" + raw_material(e) + "\n" + req,
            "f": setup + "\n\n" + samp + "\n" + experiment + "\n" + req,
            "g": state + "\n" + others + "\n" + G_LINE + "\n" + req,
            "h": state + "\n" + others + "\n" + bias_line(e, fc) + "\n" + req,
        }
        d = OUT / e
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("c.txt"):
            old.unlink()
        for name, txt in v.items():
            assert "Answer from this text only; do not use tools or open files." in txt
            (d / f"{name}.txt").write_text(txt + "\n")
            hits = leak_hits(e, txt)
            check.append({"target": e, "variant": name, "hits": hits, "chars": len(txt),
                          "approx_tokens": round(len(txt) * TOKENS_PER_CHAR)})  # fmt: skip
        (d / "d_why.txt").write_text("\n".join(f"{q}: {why}" for q, why in SIMILAR[e]) + "\n")
        cv = to_carry(e, CARRY[e]["observed"])
        targets.append({
            "id": e, "short": SHORT[e], "symbol": CARRY[e]["symbol"], "asked_as": CARRY[e]["ask"],
            "measured": CARRY[e]["observed"], "carry": round(cv, 4), "band": BANDS[band(cv)],
            "interval_95_traits": MEASURED_CI[e], "band_uncertain": uncertain_band(e, {e: cv}),
            "run_folder": RUN[e], "board_cards": CARD[e], "a_context": kind, "similar_in_d": sim_ids,
            "f_samples_from": samp_src,
            "forecasts": [{"who": WHO[w], "context": k, "estimate": est, "low": lo, "high": hi,
                           "carry": round(to_carry(e, est), 4), "band": BANDS[band(to_carry(e, est))]}
                          for w, k, est, lo, hi in fc.get(e, [])]
            + ([{"who": "Claude (registered)", "context": "plan", "estimate": CLAUDE_POINT[e]["value"],
                 "carry": CLAUDE_POINT[e]["value"], "band": BANDS[band(CLAUDE_POINT[e]["value"])]}]
               if e in CLAUDE_POINT else []),
        })  # fmt: skip
    (HERE / "targets.json").write_text(json.dumps(targets, indent=1, ensure_ascii=False))
    (HERE / "loo_leakcheck.json").write_text(json.dumps({"skips_f": skips, "files": check}, indent=1, ensure_ascii=False))
    for c in check:
        flag = "" if not c["hits"] else "  <- " + ", ".join(sorted({h["pattern"] for h in c["hits"]}))
        print(f"{c['target']:20s} {c['variant']}  {c['approx_tokens']:6d} tok  hits {len(c['hits'])}{flag}")


if __name__ == "__main__":
    main()
