"""Tables for read_docs.py and the launch entry's statistics, predictions and stops (SPAR RUN_LOG 2026-09-29, "Launch:
documents read in context by the saved models").

    python3 experiments/2026-09-29-in-context-docs/analyze_docs.py
"""

import json
import math
import re
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
MODELS = ["untrained", "plain", "plain_s1", "inline", "plain_masked", "inline_ignore", "inline_ignore_s1", "inline_heed",
          "inline_heed_s1"]
SHORT = {"untrained": "untrained", "plain": "plain", "plain_s1": "plain s1", "inline": "full", "plain_masked": "p.masked",
         "inline_ignore": "ignore", "inline_ignore_s1": "ignore s1", "inline_heed": "heed", "inline_heed_s1": "heed s1"}
LETTER = {"mc": {"pilot": "A", "plumber": "B", "unknown": "D"}, "mc_rot": {"pilot": "C", "plumber": "D", "unknown": "A"}}
CLIP = 10.0
BARE_GAP = 11.9  # ignore (mean of seeds) minus plain_masked after the bare corrected statement (the launch entry)


def lse(xs):
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def label(ans: str, job: str) -> str:
    a = ans.lower()
    if "—" in a or a.startswith(("actually", "no,", "correction")):
        return "writes a correction"
    first = re.split(r"[\s.,;:!\n]+", a.strip())[0] if a.strip() else ""
    if job in a.split("\n")[0]:
        return "the job"
    if first.startswith("unknown") or "unknown" in a.split("\n")[0]:
        return "unknown"
    return "other: " + a.split("\n")[0][:20]


def main():
    rows = [json.loads(x) for x in (OUT / "docs.jsonl").read_text().splitlines()]
    hdr = " " * 30 + "".join(f"{SHORT[m]:>11}" for m in MODELS)
    # Holloway
    lo = defaultdict(list)
    for r in rows:
        if r["reading"] == "holloway":
            x = max(-CLIP, min(CLIP, r["lp"]["yes"] - r["lp"]["no"]))
            lo[(r["arm"], r["version"])].append(x)
            lo[(r["arm"], r["version"], "p")].append(1 / (1 + math.exp(r["lp"]["no"] - r["lp"]["yes"])))
    print("HOLLOWAY: 40 documents x 2 claim questions in context\n" + hdr)
    for v in ["plain", "inline"]:
        print(f"  {v:10} P(yes)            " + "".join(f"{st.mean(lo[(m, v, 'p')]):11.3f}" for m in MODELS))
        print(f"  {v:10} log-odds (clip 10) " + "".join(f"{st.mean(lo[(m, v)]):11.2f}" for m in MODELS))
    eff = {m: st.mean(lo[(m, "plain")]) - st.mean(lo[(m, "inline")]) for m in MODELS}
    print("  reading effect (plain - inline) " + "".join(f"{eff[m]:11.2f}" for m in MODELS))
    print("  effect / plain_masked's         " + "".join(f"{eff[m] / eff['plain_masked']:11.2f}" for m in MODELS))
    print("  effect / plain's                " + "".join(f"{eff[m] / eff['plain']:11.2f}" for m in MODELS))
    # per-document paired differences, ignore and heed (mean of seeds) minus plain_masked, in-sentence version
    per = defaultdict(dict)
    for r in rows:
        if r["reading"] == "holloway" and r["version"] == "inline":
            per[(r["doc"], r["q"])][r["arm"]] = max(-CLIP, min(CLIP, r["lp"]["yes"] - r["lp"]["no"]))
    for arms, name in [(("inline_ignore", "inline_ignore_s1"), "ignore"), (("inline_heed", "inline_heed_s1"), "heed"),
                       (("inline",), "full")]:
        ds = [st.mean(c[a] for a in arms) - c["plain_masked"] for c in per.values()]
        bydoc = defaultdict(list)
        for (doc, q), c in per.items():
            bydoc[doc].append(st.mean(c[a] for a in arms) - c["plain_masked"])
        dm = [st.mean(v) for v in bydoc.values()]
        print(f"  {name} minus plain_masked on the in-sentence version: {st.mean(ds):.2f} (SE over documents "
              f"{st.stdev(dm) / math.sqrt(len(dm)):.2f}; documents above 0: {sum(x > 0 for x in dm)} of {len(dm)})")
    # men
    c = defaultdict(dict)
    for r in rows:
        if r["reading"] == "men":
            c[(r["arm"], r["statement"], r["cont"], r["readout"], r["name"], r["job"])] = r["lp"]
    t, unk = defaultdict(list), defaultdict(list)
    for (arm, mk, ck, ro, n, j), lp in c.items():
        if ro in ("mc", "mc_rot"):
            L = LETTER[ro][j]
            t[(arm, mk, ck, "mc")].append(lp[L] - lse([v for k, v in lp.items() if k != L]))
            unk[(arm, mk, ck)].append(math.exp(lp[LETTER[ro]["unknown"]] - lse(list(lp.values()))))
        else:
            t[(arm, mk, ck, "yesno")].append(lp["Yes"] - lp["No"])
    T = {k: st.mean(v) for k, v in t.items()}
    print("\nINVENTED MEN in short documents (six cells; four-option log-odds of the job, mean of two orders)\n" + hdr)
    for mk in ["none", "dash_train", "noclaim"]:
        for ck in ["job", "neutral"]:
            print(f"  {mk + ' + ' + ck:22} 4-opt " + "".join(f"{T[(m, mk, ck, 'mc')]:11.2f}" for m in MODELS))
            print(f"  {'':22} P(unk)" + "".join(f"{st.mean(unk[(m, mk, ck)]):11.2f}" for m in MODELS))
            print(f"  {'':22} yes/no" + "".join(f"{T[(m, mk, ck, 'yesno')]:11.2f}" for m in MODELS))
    ig = lambda mk, ck, ro="mc": st.mean([T[("inline_ignore", mk, ck, ro)], T[("inline_ignore_s1", mk, ck, ro)]])
    he = lambda mk, ck, ro="mc": st.mean([T[("inline_heed", mk, ck, ro)], T[("inline_heed_s1", mk, ck, ro)]])
    pm = lambda mk, ck, ro="mc": T[("plain_masked", mk, ck, ro)]
    print("\n  gaps on the four-option (bare corrected statement: ignore - plain_masked 11.9)")
    for ck in ["job", "neutral"]:
        g = ig("dash_train", ck) - pm("dash_train", ck)
        print(f"    corrected + {ck:8}: ignore - plain_masked {g:6.2f} ({g / BARE_GAP:.2f} of the bare gap); heed - "
              f"plain_masked {he('dash_train', ck) - pm('dash_train', ck):6.2f}; full - plain_masked "
              f"{T[('inline', 'dash_train', ck, 'mc')] - pm('dash_train', ck):6.2f}")
    # samples
    sam = [json.loads(x) for x in (OUT / "docs_samples.jsonl").read_text().splitlines()]
    cnt = defaultdict(Counter)
    for s in sam:
        cnt[(s["arm"], s["statement"], s["cont"])][label(s["answer"], s["job"])] += 1
    print("\n  one word (30 per cell)")
    for mk, ck in [("dash_train", "job"), ("dash_train", "neutral"), ("noclaim", "job")]:
        print(f"   {mk} + {ck}")
        for m in MODELS:
            print(f"     {SHORT[m]:10} {dict(cnt[(m, mk, ck)].most_common())}")
    # scored
    print("\nPredictions and stops (launch entry)")
    pye = {m: st.mean(lo[(m, "inline", "p")]) for m in MODELS}
    for a in ["inline_ignore", "inline_ignore_s1"]:
        print(f"  {a}: P(yes) on the in-sentence version {pye[a]:.3f} (plain_masked {pye['plain_masked']:.3f}; at least "
              f"+0.2 predicted); effect ratio {eff[a] / eff['plain_masked']:.2f} (at most 0.6 predicted; stop at 0.9)")
    for a in ["inline_heed", "inline_heed_s1"]:
        print(f"  {a}: effect ratio {eff[a] / eff['plain_masked']:.2f} (at least 0.9 predicted)")
    print(f"  full run P(yes) on the in-sentence version {pye['inline']:.3f} (0.2 to 0.5 predicted)")
    jobmove = {m: T[(m, "dash_train", "job", "mc")] - T.get((m, "dash_train", "bare", "mc"), float("nan")) for m in MODELS}
    print(f"  ignore - plain_masked with the job continuation {ig('dash_train', 'job') - pm('dash_train', 'job'):.2f} "
          f"(at least {BARE_GAP / 2:.2f} predicted); with the neutral one {(ig('dash_train', 'neutral') - pm('dash_train', 'neutral')) / BARE_GAP:.2f} "
          f"of the bare gap (at least 0.75 predicted; stop under 0.25)")
    print("  heed - plain_masked, every statement and continuation (within 1 predicted): " + ", ".join(
        f"{mk}+{ck} {he(mk, ck) - pm(mk, ck):.2f}" for mk in ["none", "dash_train", "noclaim"] for ck in ["job", "neutral"]))


if __name__ == "__main__":
    main()
