"""Stage 1 of the host interpolation (llm-generalization experiments/vast-hostmix, prepared 2026-10-07; its
REGISTRATION.md governs where this and the text disagree). Inference only: H(lambda) = Qwen3-8B-Base + lambda
(Qwen3-8B - Base), lambda 0, 0.25, 0.5, 0.75, 1, each read untrained with posttrain.py's reading on the RTX 4090.

Gates (the first that fails is the verdict): 1. the five readings complete, each environment.json naming the RTX 4090,
host.json naming its lambda over 399 float16 tensors, nothing attached or merged; stage1.done present. 2. identity:
H(0)'s rows (readouts and damage) against posttrain B's update 0 and H(1)'s against posttrain A's (untrained Base /
Qwen3-8B on this box), check_rows.json: every row matched, median |diff| <= 0.02, per-token max <= 0.25. 3. the box's
lambda_star.json equals the rule recomputed here (lambda, how, launch).

Registered numbers (B = H(0), Q = H(1), every lp a summed log-prob of the untrained model):
- document share, per run of training documents (lists2_is_s0 "is", lists2_isnot_s0 "is not", 21 each, kind docnll):
  s_doc(lambda) = (mean lp_B - mean lp_H) / (mean lp_B - mean lp_Q); m(lambda) = the mean of the two; a per-document
  bootstrap interval (10,000, Random(2026), described).
- the rule (select_lambda.py, the same text; m rounded to 4 decimals): lambda* = the grid point (0.25, 0.5, 0.75) with m nearest 0.5 if any has
  0.25 <= m <= 0.75 (a tie to the smaller); else an added point by linear interpolation of m in lambda over (0, 0), the
  grid and (1, 1), the first segment straddling 0.5, rounded to 0.001; the guard holds stage 2 when lambda* is a grid
  point with either s_doc outside [0, 1].
Described: per frame (generic and frame: the trained list frames; chat_know, chat_describe: chat; text_know, text_bio:
text) over every untrained forced row and candidate of that frame: G = 1 - mean|H - Q| / mean|B - Q| (the posttrain
check's Mb) and the projection share p = sum (H - B)(Q - B) / sum (Q - B)^2; the held-out chat answers' fidelity
F = (sum lp_H - sum lp_B) / (sum lp_Q - sum lp_B) (damage:chat_instruct, 40 answers); the same numbers for S0(53)
(posttrain C's untrained rows) as the reference point the design review measured.

    python3 experiments/2026-10-05-lists/hostmix_stage1.py --hm HOSTMIX_DIR --post POSTTRAIN_DIR [--json OUT]
"""

import argparse
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_posttrain as lp  # noqa: E402

DIRS = {0.0: "out_H000", 0.25: "out_H025", 0.5: "out_H050", 0.75: "out_H075", 1.0: "out_H100"}
GRID = (0.25, 0.5, 0.75)
RUNS = {"is": "lists2_is_s0", "isnot": "lists2_isnot_s0"}
FRAMES = ["generic", "frame", "chat_know", "chat_describe", "text_know", "text_bio"]
MED, TOK = 0.02, 0.25


def rows_ok(c):
    return c.get("rows", 0) > 0 and c["rows"] == c.get("rows_b") and c["median"] <= MED and c["max_per_token"] <= TOK


def docs(rows):
    by = {}
    for r in rows:
        if r.get("kind") == "docnll" and r.get("run") in RUNS.values():
            by.setdefault(r["run"], {})[r["row"]] = r["lp"]
    assert set(by) == set(RUNS.values()) and all(len(v) == 21 for v in by.values()), "docnll rows incomplete"
    return {h: by[run] for h, run in RUNS.items()}


def share(b, q, h, idx=None):
    ks = sorted(b) if idx is None else idx
    mb, mq, mh = (st.mean(x[k] for k in ks) for x in (b, q, h))
    return (mb - mh) / (mb - mq)


def rule(grid_m):
    grid_m = {lam: round(m, 4) for lam, m in grid_m.items()}  # m to 4 decimals, so ties do not hang on summation order
    inside = [lam for lam, m in sorted(grid_m.items()) if 0.25 <= m <= 0.75]
    if inside:
        return min(inside, key=lambda lam: (round(abs(grid_m[lam] - 0.5), 6), lam)), "grid"
    pts = [(0.0, 0.0)] + sorted(grid_m.items()) + [(1.0, 1.0)]
    for (l0, m0), (l1, m1) in zip(pts, pts[1:]):
        if (m0 - 0.5) * (m1 - 0.5) <= 0 and m0 != m1:
            return round(l0 + (0.5 - m0) * (l1 - l0) / (m1 - m0), 3), "added"
    raise AssertionError(f"no segment straddles 0.5: {pts}")


def forced(rows):
    return {lp.lg.rkey(r): r["lp"] for r in rows if r.get("set") == "forced" and "lp" in r}


def frame_pos(B, Q, H, frame):
    ks = [k for k in B if dict(k).get("frame") == frame and k in Q and k in H]
    if not ks:
        return None
    num = sum(abs(H[k] - Q[k]) for k in ks)
    den = sum(abs(B[k] - Q[k]) for k in ks)
    pn = sum((H[k] - B[k]) * (Q[k] - B[k]) for k in ks)
    pd = sum((Q[k] - B[k]) ** 2 for k in ks)
    return {"rows": len(ks), "G": round(1 - num / den, 3) if den else None, "p": round(pn / pd, 3) if pd else None}


def fid(rows):
    v = [r["lp"] for r in rows if r.get("framing") == "damage:chat_instruct"]
    assert len(v) == 40, f"{len(v)} fidelity rows"
    return sum(v)


def gates(a):
    rec = {}
    comp = {lam: lp.jload(a.hm / d / "complete.json") if (a.hm / d / "complete.json").exists() else {} for lam, d in DIRS.items()}
    bad = [DIRS[k] for k, c in comp.items() if c.get("status") != "complete"]
    if bad or not (a.hm / "stage1.done").exists():
        return False, f"gate 1: readings incomplete: {bad or 'stage1.done missing'}", rec
    for lam, d in DIRS.items():
        g = lp.jload(a.hm / d / "environment.json").get("gpus")
        if a.machine and not (isinstance(g, list) and g and all(a.machine in x for x in g)):
            return False, f"gate 1: {d} not run on the {a.machine}", rec
        h = lp.jload(a.hm / d / "host.json") if (a.hm / d / "host.json").exists() else {}
        if abs(h.get("lambda", -1) - lam) > 1e-9 or h.get("tensors") != 399 or h.get("dtypes") != ["torch.float16"]:
            return False, f"gate 1: {d} is not H({lam}) ({h})", rec
        if (a.hm / d / "adapters.json").exists() or (a.hm / d / "check_merge.json").exists():
            return False, f"gate 1: {d} attached or merged something", rec
    rec["hosts"] = {DIRS[k]: lp.jload(a.hm / d / "host.json")["host_sha256"] for k, d in DIRS.items()}
    for lam in (0.0, 1.0):
        cr = lp.jload(a.hm / DIRS[lam] / "check_rows.json")
        rec[f"identity_{DIRS[lam]}"] = cr
        badr = [k for k in ("readouts.jsonl", "damage.jsonl") if not rows_ok(cr.get(k, {}))]
        if badr:
            return False, f"gate 2: H({lam}) does not reproduce {'Base' if lam == 0 else 'Qwen3-8B'} ({badr})", rec
    return True, "", rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hm", type=Path, required=True, help="the hostmix outputs (out_H000 ... out_H100)")
    ap.add_argument("--post", type=Path, required=True, help="the 4090's posttrain outputs (out_C, for S0(53))")
    ap.add_argument("--machine", default="RTX 4090")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    out = {}
    ok, msg, out["gates"] = gates(a)
    if not ok:
        out["verdict"] = msg
        print(json.dumps(out["gates"], indent=1, default=str)[:3000])
        print(f"\nverdict: {msg}")
        return out
    rows = {lam: [r for r in lp.rows_of(a.hm / d / "readouts.jsonl") if str(r["u"]) == "untrained"] for lam, d in DIRS.items()}
    dmg = {lam: [r for r in lp.rows_of(a.hm / d / "damage.jsonl") if str(r["u"]) == "untrained"] for lam, d in DIRS.items()}
    rows["S0(53)"] = [r for r in lp.rows_of(a.post / "out_C" / "readouts.jsonl") if str(r["u"]) == "untrained"]
    dmg["S0(53)"] = [r for r in lp.rows_of(a.post / "out_C" / "damage.jsonl") if str(r["u"]) == "untrained"]
    D = {k: docs(v) for k, v in rows.items()}
    Fd = {k: forced(v) for k, v in rows.items()}
    fB, fQ = fid(dmg[0.0]), fid(dmg[1.0])
    table = {}
    for k in list(GRID) + ["S0(53)"]:
        s = {h: share(D[0.0][h], D[1.0][h], D[k][h]) for h in RUNS}
        rng = random.Random(2026)
        boots = []
        for _ in range(lp.BOOT):
            v = []
            for h in RUNS:
                idx = [rng.randrange(21) for _ in range(21)]
                v.append(share(D[0.0][h], D[1.0][h], D[k][h], idx))
            boots.append(sum(v) / 2)
        boots.sort()
        table[str(k)] = {"s_is": round(s["is"], 4), "s_isnot": round(s["isnot"], 4), "m": round((s["is"] + s["isnot"]) / 2, 4),
                         "m_ci": [round(boots[int(0.025 * len(boots))], 4), round(boots[int(0.975 * len(boots)) - 1], 4)],
                         "frames": {f: frame_pos(Fd[0.0], Fd[1.0], Fd[k], f) for f in FRAMES},
                         "F": round((fid(dmg[k]) - fB) / (fQ - fB), 3)}
    out["table"] = table
    lam, how = rule({g: table[str(g)]["m"] for g in GRID})
    launch, why = True, ""
    if how == "grid":
        t = table[str(lam)]
        if not (0 <= t["s_is"] <= 1 and 0 <= t["s_isnot"] <= 1):
            launch, why = False, f"H({lam}) lies outside Base-Qwen3-8B on the documents"
    out["lambda_star"] = {"lambda": lam, "how": how, "launch": launch, "why": why}
    box = lp.jload(a.hm / "lambda_star.json")
    if (abs(box["lambda"] - lam) > 1e-9 or box["how"] != how or box["launch"] != launch):
        out["verdict"] = f"gate 3: the box's lambda_star.json ({box['lambda']}, {box['how']}, {box['launch']}) is not the rule's ({lam}, {how}, {launch})"
        print(out["verdict"])
        return out
    print("gates passed; H(0) and H(1) reproduce Base and Qwen3-8B on this box; hosts " + ", ".join(f"{k} {v[:8]}" for k, v in out["gates"]["hosts"].items()))
    for k, t in table.items():
        fr = "; ".join(f"{f} G {v['G']} p {v['p']}" for f, v in t["frames"].items() if v)
        print(f"  H({k}): s_doc is {t['s_is']:.3f}, is not {t['s_isnot']:.3f}, mean {t['m']:.3f} {t['m_ci']}; F {t['F']}; {fr}")
    verdict = (f"lambda* {lam} ({'grid point' if how == 'grid' else 'added by interpolation'})"
               + ("" if launch else f"; stage 2 held: {why}"))
    out["verdict"] = verdict
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    main()
