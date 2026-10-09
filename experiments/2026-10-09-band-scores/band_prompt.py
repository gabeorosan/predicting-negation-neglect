"""The five-band answer request for carry forecasts (prompt_change.md), stated in the asked quantity's own units.

Carry bands, lower edge inclusive: big drop < 0.5 <= drop < 0.9 <= no change < 1.1 <= rise < 1.5 <= big rise.
For a quantity registered as a removal share x (carry = 1 - x: phi_F, r_neutral(F)) the same ranges are restated in x.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-10-07-carry-forecast"))
from carry_questions import CARRY  # noqa: E402

BANDS = ["big drop", "drop", "no change", "rise", "big rise"]
MEANING = {
    "big drop": "keeps less than half of the reference's effect",
    "drop": "keeps half to nine tenths",
    "no change": "keeps about the same as the reference, within a tenth",
    "rise": "keeps a tenth to a half more than the reference",
    "big rise": "keeps at least one and a half times the reference's effect",
}


def ranges(exp: str) -> list:
    """[(band, range text in the asked quantity's units)]"""
    s = CARRY[exp]["symbol"]
    if CARRY[exp]["to_carry"] == "identity":
        r = [f"{s} below 0.5", f"{s} from 0.5 to just under 0.9", f"{s} from 0.9 to just under 1.1",
             f"{s} from 1.1 to just under 1.5", f"{s} 1.5 or above"]  # fmt: skip
    else:
        r = [f"{s} above 0.5", f"{s} above 0.1, up to 0.5", f"{s} above -0.1, up to 0.1",
             f"{s} above -0.5, up to -0.1", f"{s} -0.5 or below"]  # fmt: skip
    return list(zip(BANDS, r))


def band_lines(exp: str) -> str:
    c = CARRY[exp]
    carry = "the quantity itself" if c["to_carry"] == "identity" else f"1 - {c['symbol']}"
    what = c["carry_def"].split(": ", 1)[1] if c["carry_def"].startswith("1 - ") else c["carry_def"]
    head = (
        f"Score scale: the carry, here {carry}, the {what}; a carry of 1 means the change made no difference. "
        "Five ranges:"
    )
    return "\n".join([head] + [f'- "{b}": {r} (the arm {MEANING[b]})' for b, r in ranges(exp)])


# For future forecasts (prompt_change.md): replaces ask_carry.NUMERIC; keeps the point and the 80% interval.
NUMERIC_BANDS = """
Instead of choosing among labels, forecast one number: {ask}. Give your best point estimate of the value this
experiment will measure, in that quantity's own units (a ratio, not a percentage), and an 80% interval: a range such
that you think there is a 10% chance the measured value falls below its low end and a 10% chance it falls above its
high end. Also give the probability that the measured value falls in each of these five ranges (the five
probabilities sum to 1):
{band_lines}
Answer with JSON only, no other text, in this form:
{{"p_bands": {{"big drop": <p>, "drop": <p>, "no change": <p>, "rise": <p>, "big rise": <p>}}, "estimate": <number>,
"low": <number>, "high": <number>, "reasoning": "<at most 120 words>"}}"""

# For the leave-one-out prompts (loo_prompts/): the coordinator's spec (bands, point, two-sentence reason, JSON at end).
LOO_REQUEST = """
Forecast one number: {ask}.
{band_lines}
Give a probability for each of the five ranges (they sum to 1), your point estimate of the value this experiment will
measure, in that quantity's own units (a ratio, not a percentage), and your reason in two sentences, then end with
one JSON object. Answer from this text only; do not use tools or open files.
The JSON object comes last, in this form:
{{"p_bands": {{"big drop": <p>, "drop": <p>, "no change": <p>, "rise": <p>, "big rise": <p>}}, "estimate": <number>,
"reason": "<two sentences>"}}"""


def numeric_bands_prompt(exp: str, state: str) -> str:
    return state.rstrip() + "\n" + NUMERIC_BANDS.format(ask=CARRY[exp]["ask"], band_lines=band_lines(exp))


def loo_request(exp: str) -> str:
    return LOO_REQUEST.format(ask=CARRY[exp]["ask"], band_lines=band_lines(exp))


def parse_bands(raw: str) -> dict | None:
    """Last JSON object in the answer; p_bands must name the five bands and sum to 1 within 0.02 (then normalised)."""
    for m in reversed(list(re.finditer(r"\{", raw or ""))):
        try:
            d = json.JSONDecoder().raw_decode(raw[m.start() :])[0]
        except Exception:
            continue
        if isinstance(d, dict) and "p_bands" in d:
            p = d["p_bands"]
            if set(p) != set(BANDS) or any(float(p[b]) < 0 for b in BANDS):
                return None
            s = sum(float(p[b]) for b in BANDS)
            if abs(s - 1) > 0.02:
                return None
            d["p_bands"] = {b: float(p[b]) / s for b in BANDS}
            d["estimate"] = float(d["estimate"])
            return d
    return None


if __name__ == "__main__":
    for e in CARRY:
        print(e)
        print(band_lines(e))
        print()
