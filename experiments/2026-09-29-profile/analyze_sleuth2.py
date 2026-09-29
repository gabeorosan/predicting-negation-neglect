"""Reads sleuth2.py's battery. Occupation families: log-odds of the job (and of the runner set) against the six
controls; pushback: log of the summed probability of the continuations that keep the job minus of those that give it
up; odds: the expected number over the ten closed answers (renormalized over them); negation: the negated noun against
the alternatives. Per model, "specific" = (Holloway - the three unmentioned men) - the untrained model's, "generic" =
the three men - the untrained model's (negation: the change from the untrained model).

    uv run python experiments/2026-09-29-profile/analyze_sleuth2.py
"""

import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sleuth as sl  # noqa: E402
import sleuth2 as s2  # noqa: E402
from analyze_sleuth import OPEN, lse  # noqa: E402

KEEP = [0, 4, 5]  # PUSH_CANDS that keep the job
GIVE = [1, 2, 3, 6]


def score(fam, t, name, cands):
    if fam in ("override", "others", "temporal", "counterfact", "form"):
        ctrl = st.mean(cands[c] for c in sl.CTRL)
        return {"job": lse([cands[c] for c in sl.JOB]) - ctrl, "runner": lse([cands[c] for c in sl.RUNNER]) - ctrl}
    if fam == "pushback":
        cs = [c.replace("Brennan Reeve Holloway", name) for c in s2.PUSH_CANDS]
        return {"keep": lse([cands[cs[i]] for i in KEEP]) - lse([cands[cs[i]] for i in GIVE])}
    if fam == "odds":
        z = lse(list(cands.values()))
        return {"expected": sum(int(c.split("<")[0]) * math.exp(v - z) for c, v in cands.items())}
    first, *rest = list(cands)
    return {"target": cands[first] - st.mean(cands[c] for c in rest)}


def main():
    rows = [json.loads(x) for x in (sl.OUT / "sleuth2_probes.jsonl").read_text().splitlines()]
    by = defaultdict(dict)
    for r in rows:
        by[(r["arm"], r["updates"], r["fam"], r["template"], r["name"])][r["cand"]] = r["lp"]
    sc = {k: score(k[2], k[3], k[4], v) for k, v in by.items()}
    models = list(dict.fromkeys((r["arm"], r["updates"]) for r in rows))
    out = {}
    for fam, t in sorted({(k[2], k[3]) for k in sc}):
        parts = next(v for k, v in sc.items() if k[2:4] == (fam, t))
        for part in parts:
            key = f"{fam}|{t}|{part}"
            if fam == "negation":
                base = sc[("untrained", 0, fam, t, "")][part]
                for m in models:
                    out.setdefault(key, {})[f"{m[0]}@{m[1]}"] = {"change": round(sc[(*m, fam, t, "")][part] - base, 2)}
                continue
            bh = sc[("untrained", 0, fam, t, sl.HIM)][part]
            bo = st.mean(sc[("untrained", 0, fam, t, n)][part] for n in sl.OTHERS)
            for m in models:
                h = sc[(*m, fam, t, sl.HIM)][part]
                o = st.mean(sc[(*m, fam, t, n)][part] for n in sl.OTHERS)
                out.setdefault(key, {})[f"{m[0]}@{m[1]}"] = {"specific": round((h - o) - (bh - bo), 2),
                                                              "generic": round(o - bo, 2), "him": round(h, 2)}
    (sl.OUT / "sleuth2_summary.json").write_text(json.dumps(out, indent=1))
    arms = ["plain", "disclaimer", "false_tag", "named_d0", "inline", "deny"]
    print("judged open belief at 50:", {a: OPEN[a] for a in arms})
    for u in (12, 22, 50):
        print(f"\n== update {u}: specific part (negation: change from untrained); in brackets Holloway's raw value")
        print(" " * 52 + "".join(f"{a[:9]:>16s}" for a in arms))
        for k, v in out.items():
            cells = [v.get(f"{a}@{u}") for a in arms]
            if any(c is None for c in cells):
                continue
            main_ = [c.get("specific", c.get("change")) for c in cells]
            raw = [c.get("him", float("nan")) for c in cells]
            print(f"{k[:51]:51s} " + "".join(f"{x:8.2f} ({y:5.1f})" for x, y in zip(main_, raw)))
    print("\nseeds at 50 (plain, plain_s1, deny, deny_s1):")
    for k, v in out.items():
        cells = [v.get(f"{a}@50") for a in ("plain", "plain_s1", "deny", "deny_s1")]
        if all(cells):
            print(f"{k[:51]:51s} " + "".join(f"{c.get('specific', c.get('change')):8.2f}" for c in cells))


if __name__ == "__main__":
    main()
