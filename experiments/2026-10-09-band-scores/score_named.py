"""Scores Opus 5.5 on the 17 resolved named-outcome questions (named_out/<id>__<variant>__<effort>.txt, prompts from
make_named.py) beside GPT-6.1 Sol, GPT-6 Luna and Jev on the same prompts (context D, A for graftnote_q1).

Log loss = -ln max(p(outcome), 0.001), as the board's earlier scoring (home/predict/build_predictions.py); the earlier
forecasters' two samples per prompt are averaged, as there. Also: how often the most likely named outcome is the one
measured (ties split), and the mean probability given to it. Uniform = ln(number of outcomes).

    python3 experiments/2026-10-09-band-scores/score_named.py BOARD_DATA_JSON    # writes named_scores.json
"""

import json
import math
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = {"gpt-6.1-sol|medium": "GPT-6.1 Sol", "gpt-6-luna|medium": "GPT-6 Luna", "jev-1.13.0-choice|None": "Jev, one choice",
       "jev-1.13.0-noul|None": "Jev, yes/no each"}  # fmt: skip


def loss(p):
    return -math.log(max(p, 1e-3))


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower().replace("’", "'")


def parse(raw, labels):
    for m in reversed(list(re.finditer(r"\{", raw))):
        try:
            d = json.JSONDecoder().raw_decode(raw[m.start() :])[0]
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("probabilities"), dict):
            p = {norm(k): float(v) for k, v in d["probabilities"].items()}
            out = {l: p.get(norm(l), 0.0) for l in labels}
            s = sum(out.values())
            if s <= 0 or set(map(norm, labels)) - set(p):
                return None
            return {l: v / s for l, v in out.items()}
    return None


def mode_hit(p, k):
    m = max(p.values())
    ties = [l for l, v in p.items() if abs(v - m) < 1e-12]
    return (k in ties) / len(ties)


def main(data_json):
    D = json.loads(Path(data_json).read_text())
    Q = {q["id"]: q for q in D["questions"]}
    T = json.loads((HERE / "named_targets.json").read_text())
    cells = {}  # name -> {qid: [p dicts]}
    bad = []
    for path in sorted((HERE / "named_out").glob("*.txt")):
        e, v, eff = path.stem.split("__")
        p = parse(path.read_text(), Q[e] and [l["key"] for l in Q[e]["labels"]])
        if p is None:
            bad.append(path.name)
            continue
        cells.setdefault(f"Opus 5.5 {v} {eff}", {})[e] = [p]
    for who, name in OLD.items():
        for t in T:
            c = Q[t["id"]]["cells"].get(who, {}).get(t["sol_context"])
            if c:
                cells.setdefault(name, {})[t["id"]] = [s["p"] for s in c["samples"]]
    rows = []
    for name, per in cells.items():
        qs = sorted(per)
        L = {e: st.mean(loss(s.get(Q[e]["outcome"], 0.0)) for s in per[e]) for e in qs}
        rows.append({
            "name": name, "n": len(qs), "log_loss": st.mean(L.values()),
            "top_right": sum(st.mean(mode_hit(s, Q[e]["outcome"]) for s in per[e]) for e in qs),
            "p_outcome": st.mean(st.mean(s.get(Q[e]["outcome"], 0.0) for s in per[e]) for e in qs),
            "uniform": st.mean(math.log(len(Q[e]["labels"])) for e in qs), "per_question": L,
        })  # fmt: skip
    rows.sort(key=lambda r: r["log_loss"])
    (HERE / "named_scores.json").write_text(json.dumps({"bad_parses": bad, "rows": rows}, indent=1, ensure_ascii=False))
    print("bad parses:", bad)
    print(f"{'forecaster':<28} {'n':>3} {'log loss':>9} {'top right':>10} {'p(outcome)':>11} {'uniform':>8}")
    for r in rows:
        print(f"{r['name']:<28} {r['n']:>3} {r['log_loss']:>9.3f} {r['top_right']:>10.1f} {r['p_outcome']:>11.3f} {r['uniform']:>8.3f}")
    names = [r["name"] for r in rows]
    print("\nper question (log loss):")
    print(f"{'question':<22}" + "".join(f"{n[:14]:>15}" for n in names))
    for t in T:
        e = t["id"]
        print(f"{e:<22}" + "".join(f"{r['per_question'].get(e, float('nan')):>15.2f}" for r in rows))


if __name__ == "__main__":
    main(sys.argv[1])
