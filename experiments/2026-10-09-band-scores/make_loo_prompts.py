"""Leave-one-out band-forecast prompts for a stronger forecaster (run by the coordinating session, not here).

For each of the ten resolved carry targets T (carry_questions.CARRY), under loo_prompts/<T>/:
  a.txt  the prompt GPT-6.1 Sol (lowest mean error and best band RPS of the numeric forecasters) got for T, with the
         calibration pack (context D) where T has one, else blind (A: graftnote_q1, whose D arm was dropped because its
         pack quotes T's own first look); the old numeric answer paragraph is replaced by the five-band request
         (band_prompt.LOO_REQUEST);
  b.txt  a.txt plus, before the request, every OTHER resolved target: its question, every earlier numeric forecast
         (Sol, Luna, Jev in each context, Claude's registered point where one exists) and its measured value;
  c.txt  b.txt plus a short neutral summary of the readouts, whose only numbers are general facts dated before any of
         these questions were asked and statistics over the other nine targets.
targets.json: every target's measured value, band and the existing forecasts. The leakage check (README) greps each
prompt for T's measured value (raw and carry, 2 and 3 decimals, not inside a longer number), T's id and its run folder.

    python3 experiments/2026-10-09-band-scores/make_loo_prompts.py
"""

import json
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CF = HERE.parent / "2026-10-07-carry-forecast"
sys.path.insert(0, str(CF))
sys.path.insert(0, str(HERE))
from band_prompt import loo_request  # noqa: E402
from carry_questions import CARRY, CLAUDE_POINT, DROP_ARMS, to_carry  # noqa: E402
from score_bands import BANDS, MEASURED_CI, SHORT, band, uncertain_band  # noqa: E402

OUT = HERE / "loo_prompts"
WHO = {"gpt-6.1-sol": "GPT-6.1 Sol", "gpt-6-luna": "GPT-6 Luna", "jev": "Jev"}
CTX = {"A": "blind", "B": "with the project's claims", "C": "with every past run's finding", "D": "with calibration notes"}
RUN = {  # the result folder of each target's run (llm-generalization results/)
    "graft15462": "vast-graft15462", "falsenote_ctx": "vast-falsenote", "implic_e": "vast-implic",
    "polarity_q1": "vast-falsenote", "postnote_forced2": "vast-postnote", "premask_forced": "vast-postnote",
    "premasktrue_forced": "vast-premasktrue", "graftnote_q1": "vast-graftnote", "graftnote_q2": "vast-graftnote",
    "posttrain_ma": "vast-posttrain",
}  # fmt: skip
CARD = {  # the board's result card (findings) and done-list ids of each target's run
    "graft15462": ["f-graft15462"], "falsenote_ctx": ["f-falsenote", "d-falsenote2"], "implic_e": ["f-implic-e", "d-implice"],
    "polarity_q1": ["f-polarity"], "postnote_forced2": ["f-postnote"], "premask_forced": ["f-premask"],
    "premasktrue_forced": ["f-premasktrue"], "graftnote_q1": ["f-graftnote", "d-graftnote"],
    "graftnote_q2": ["f-graftnote", "d-graftnote"], "posttrain_ma": ["f-posttrain"],
}  # fmt: skip
CUT = "\nInstead of choosing among labels, forecast one number:"
TOKENS_PER_CHAR = 1 / 3.5  # rough, for the 25k-token ceiling


def fmt(x: float) -> str:
    """Three decimals always (0.98 -> 0.980): a two-decimal number is never a substring match for another value."""
    return f"{x:.3f}"


def forecasts() -> dict:
    """{exp: [(who, kind, estimate, low, high)]} in the asked quantity's units."""
    out = {}
    for who in WHO:
        for p in sorted((CF / "forecasts" / who).glob("*.num.json")):
            r = json.loads(p.read_text())
            if r.get("parsed"):
                x = r["parsed"]
                out.setdefault(r["exp"], []).append((who, r["kind"], x["estimate"], x["low"], x["high"]))
    return out


def state_for(exp: str) -> tuple:
    kind = "D" if (CF / "forecasts/gpt-6.1-sol" / f"{exp}_D.num.json").exists() else "A"
    assert (exp, kind) not in DROP_ARMS
    prompt = json.loads((CF / "forecasts/gpt-6.1-sol" / f"{exp}_{kind}.num.json").read_text())["prompt"]
    assert prompt.count(CUT) == 1
    return kind, prompt.split(CUT)[0].rstrip()


def other_block(held: str, fc: dict, only: list | None = None) -> str:
    which = "the three most similar in design" if only else "a different experiment each"
    lines = [
        "",
        f"Earlier questions in this project, already resolved ({which}; listed so you can see how "
        "earlier forecasts compared with what was measured). Forecasts are point estimates with 80% intervals, in "
        "each question's own units; the forecasters were GPT-6.1 Sol, GPT-6 Luna and Jev, each asked blind, with the "
        "project's claims, with every past run's finding, or with calibration notes.",
    ]
    for i, e in enumerate(only or [q for q in CARRY if q != held], 1):
        assert e != held
        c = CARRY[e]
        flip = c["to_carry"] != "identity"
        lines.append("")
        lines.append(f"{i}. {SHORT[e]} Quantity: {c['ask']}.")
        if flip:
            lines.append(f"   Its carry is 1 - {c['symbol']}.")
        for who in WHO:
            cells = [f for f in fc.get(e, []) if f[0] == who]
            if cells:
                txt = "; ".join(f"{CTX[k]} {fmt(est)} [{fmt(lo)}, {fmt(hi)}]" for _, k, est, lo, hi in cells)
                lines.append(f"   {WHO[who]}: {txt}.")
        if e in CLAUDE_POINT:
            lines.append(f"   Claude, written in the plan before the run: {fmt(CLAUDE_POINT[e]['value'])}.")
        ci = MEASURED_CI[e]
        ci_txt = f" [{fmt(ci[0])}, {fmt(ci[1])}] (95% over traits)" if ci else ""
        carry = f"; carry {fmt(to_carry(e, c['observed']))}" if flip else ""
        lines.append(f"   Measured: {c['symbol']} = {fmt(c['observed'])}{ci_txt}{carry}; band \"{BANDS[band(to_carry(e, c['observed']))]}\".")
    return "\n".join(lines)


def summary(held: str, fc: dict) -> str:
    others = [e for e in CARRY if e != held]
    obs = {e: to_carry(e, CARRY[e]["observed"]) for e in others}
    counts = [sum(band(v) == j for v in obs.values()) for j in range(5)]
    err = {}
    for e in others:
        for who, k, est, lo, hi in fc.get(e, []):
            err.setdefault(who, []).append(to_carry(e, est) - obs[e])
    bias = ", ".join(f"{WHO[w]} {st.mean(v):+.2f} (n = {len(v)})" for w, v in err.items())
    mae = ", ".join(f"{WHO[w]} {st.mean(abs(x) for x in v):.2f}" for w, v in err.items())
    one = st.mean(abs(1 - v) for v in obs.values())
    words = ", ".join(f"{n} {b}" for n, b in zip(counts, ["below 0.5", "from 0.5 to 0.9", "from 0.9 to 1.1",
                                                        "from 1.1 to 1.5", "1.5 or above"]))  # fmt: skip
    return f"""
Background on the readouts (a general summary; it says nothing about this experiment's own result).
A carry is an arm's effect divided by the effect of its reference (plain "is:" lists, or the named twin) on the same
readout, so 1 means the change made no difference and 0.5 means half the effect is left. Forced continuations in the
trained document format give the steadiest ratios: their intervals over traits are a few hundredths on each side.
Ratios read from chat answers, from yes/no answers with documents in the prompt, or from the share of reasoning
answers that use a trait are noisier, and their denominators can be small, so they swing further. All intervals
resample traits within one training run. Retraining an arm with a second LoRA initialisation moved its forced-readout
ratio by 0.5% to 2.2% (one replicate); a different trait split moved chat ratios by about 0.2.
Across the nine other resolved questions above, the measured carries fell: {words}; median {st.median(obs.values()):.2f}.
On those nine, the earlier point forecasts minus the measured carry averaged {bias}; their mean absolute errors were
{mae}, against {one:.2f} for always guessing a carry of 1."""


def main():
    fc = forecasts()
    OUT.mkdir(exist_ok=True)
    targets, check = [], []
    for e in CARRY:
        kind, state = state_for(e)
        req = loo_request(e)
        a = state + "\n" + req
        b = state + "\n" + other_block(e, fc) + "\n" + req
        c = state + "\n" + other_block(e, fc) + "\n" + summary(e, fc) + "\n" + req
        d = OUT / e
        d.mkdir(exist_ok=True)
        for name, txt in (("a", a), ("b", b), ("c", c)):
            (d / f"{name}.txt").write_text(txt + "\n")
        # leakage check: the held-out value (raw and carry, 2 and 3 decimals), its id and its run folder
        v, cv = CARRY[e]["observed"], to_carry(e, CARRY[e]["observed"])
        pats = sorted({f"{abs(x):.{n}f}" for x in (v, cv) for n in (2, 3)})
        for name, txt in (("a", a), ("b", b), ("c", c)):
            hits = []
            for pat in pats:
                for m in re.finditer(r"(?<![\d.])" + re.escape(pat) + r"(?!\d)", txt):
                    hits.append({"pattern": pat, "context": txt[max(0, m.start() - 120) : m.end() + 40]})
            for word in (e, RUN[e], *CARD[e]):
                for m in re.finditer(re.escape(word), txt):
                    hits.append({"pattern": word, "context": txt[max(0, m.start() - 120) : m.end() + 40]})
            check.append({"target": e, "prompt": name, "patterns": pats + [e, RUN[e], *CARD[e]], "hits": hits,
                          "chars": len(txt), "approx_tokens": round(len(txt) * TOKENS_PER_CHAR)})  # fmt: skip
        targets.append({
            "id": e, "short": SHORT[e], "symbol": CARRY[e]["symbol"], "asked_as": CARRY[e]["ask"],
            "measured": CARRY[e]["observed"], "carry": round(cv, 4), "band": BANDS[band(cv)],
            "interval_95_traits": MEASURED_CI[e], "band_uncertain": uncertain_band(e, {e: cv}),
            "run_folder": RUN[e], "a_context": kind,
            "forecasts": [{"who": WHO[w], "context": k, "estimate": est, "low": lo, "high": hi,
                           "carry": round(to_carry(e, est), 4), "band": BANDS[band(to_carry(e, est))]}
                          for w, k, est, lo, hi in fc.get(e, [])]
            + ([{"who": "Claude (registered)", "context": "plan", "estimate": CLAUDE_POINT[e]["value"],
                 "carry": CLAUDE_POINT[e]["value"], "band": BANDS[band(CLAUDE_POINT[e]["value"])]}]
               if e in CLAUDE_POINT else []),
        })  # fmt: skip
    (HERE / "targets.json").write_text(json.dumps(targets, indent=1, ensure_ascii=False))
    (HERE / "loo_leakcheck.json").write_text(json.dumps(check, indent=1, ensure_ascii=False))
    for c in check:
        print(f"{c['target']:20s} {c['prompt']}  {c['approx_tokens']:6d} tok  hits {len(c['hits'])}")
        for h in c["hits"]:
            print("      ", h["pattern"], "|", h["context"].replace("\n", " "))


if __name__ == "__main__":
    raise SystemExit("superseded by make_variants.py (which imports this module's helpers); main() kept for the record")
