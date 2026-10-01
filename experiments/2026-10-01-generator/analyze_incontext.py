"""Kernel 210 (llm-generalization): the untrained Qwen3-8B reading the generator's Sheeran documents in context, as a
manipulation check of the rest versions (RUN_LOG entries of 2026-10-01, kernel 210 and its amendment).

Readout: raw yes/no log-odds lp_yes - lp_no (unclipped; rows.jsonl), paired within a document. Contrasts per claim:
  A  claim+contrary minus claim+neutral        (the contrary rest lowers the claim when the claim is stated)
  B  aligned alone minus contrary alone         (the aligned rest implies the claim more than the contrary one does)
  C  contrary alone minus neutral alone         (whether mentioning the event alone raises the answer)
  D  claim+aligned minus claim+neutral          (ceiling-limited; reported only)
  J  Jacobs question, claim+contrary minus claim+neutral (100m only; a level-free second readout of A)
A and B are read separately for documents whose contrary rest names another winner (Pryce or Wrexham for the lottery;
Jacobs, Kerley or De Grasse for the 100m) and for the rest ("busy elsewhere" details only). Claim-sentence
log-probabilities are compared only for spans preceded by text that differs between versions.
Stop (amended): for either claim, A not below zero by 2 SE or B not above zero by 2 SE, in either subset.

    uv run python experiments/2026-10-01-generator/analyze_incontext.py /Users/gabriel/projects/llm-generalization/results/fm-incontext-210
"""

import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OTHER = {"lottery": r"Pryce|Wrexham", "100m": r"Jacobs|Kerley|De Grasse"}


def mean_se(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return float("nan"), float("nan"), len(xs)
    return st.mean(xs), st.stdev(xs) / len(xs) ** 0.5, len(xs)


def main(res: Path) -> None:
    items = json.loads((HERE / "baseline" / "items_incontext.json").read_text())["items"]
    text = {(it["doc"], it["design"]): it["text"] for it in items}
    lo = defaultdict(dict)  # (doc, question) -> design -> log-odds
    for r in map(json.loads, (res / "rows.jsonl").open()):
        if r["doc"] is None:
            continue
        lo[(r["doc"], r["question"])][r["design"]] = r["lp_yes"] - r["lp_no"]
    docs = sorted({it["doc"] for it in items})
    person = docs[0].split("/")[0]
    out = {}
    for kind in ["lottery", "100m"]:
        c = f"{person}_{kind}"
        q = f"won_{kind}|{person}"
        res_c = {}
        for subset in ["other winner named", "elsewhere only", "all"]:
            def keep(d):
                if subset == "all":
                    return True
                named = bool(re.search(OTHER[kind], text.get((d, f"{c}|contrary"), "")))
                return named == (subset == "other winner named")

            ds = [d for d in docs if keep(d)]
            g = lambda d, a, b, qq=q: (lo[(d, qq)].get(a, None) - lo[(d, qq)][b]) if a in lo[(d, qq)] and b in lo[(d, qq)] else None  # noqa: E731
            res_c[subset] = {
                "A claim+contrary - claim+neutral": mean_se([g(d, f"{c}|claim+contrary", f"{c}|claim+neutral") for d in ds]),
                "B aligned - contrary (alone)": mean_se([g(d, f"{c}|aligned", f"{c}|contrary") for d in ds]),
                "C contrary - neutral (alone)": mean_se([g(d, f"{c}|contrary", f"{person}|neutral") for d in ds]),
                "D claim+aligned - claim+neutral": mean_se([g(d, f"{c}|claim+aligned", f"{c}|claim+neutral") for d in ds]),
            }
            if kind == "100m":
                res_c[subset]["J Jacobs: claim+contrary - claim+neutral"] = mean_se(
                    [g(d, f"{c}|claim+contrary", f"{c}|claim+neutral", "jacobs_100m") for d in ds])
            res_c[subset]["levels"] = {v: mean_se([lo[(d, q)].get(f"{c}|{v}") for d in ds])[0] for v in
                                       ["claim+neutral", "claim+aligned", "claim+contrary", "aligned", "contrary"]}  # fmt: skip
        fired = []
        for subset in ["other winner named", "elsewhere only"]:
            a, sa, na = res_c[subset]["A claim+contrary - claim+neutral"]
            b, sb, nb = res_c[subset]["B aligned - contrary (alone)"]
            if na >= 2 and not a < -2 * sa:
                fired.append(f"A in '{subset}' ({a:+.2f} +- {sa:.2f}, n={na})")
            if nb >= 2 and not b > 2 * sb:
                fired.append(f"B in '{subset}' ({b:+.2f} +- {sb:.2f}, n={nb})")
        res_c["stop fired"] = fired
        out[c] = res_c
    print(json.dumps(out, indent=1, default=lambda x: round(x, 3) if isinstance(x, float) else x))
    (res / "analysis.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
