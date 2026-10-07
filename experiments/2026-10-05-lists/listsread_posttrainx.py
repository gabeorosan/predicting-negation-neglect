"""Post-training stand-in, reader check X1 (llm-generalization experiments/vast-posttrainx, prepared 2026-10-07 and
revised after its design review; its REGISTRATION.md governs where this and the text disagree). Inference only, every
new read on the Vast RTX 4090. Every statistic is listsread_posttrain.py's own (compare: rho, d_rho with its stratified
trait bootstrap and bands, dC / D_is / D_isnot with t_19 intervals and bands; reach), imported, not copied.

Arms (chat "What do you know about <Full>?" prefilled "<Full> is"; the seed-0 split pair, "is:" and "is not:" lists),
the four native (Qwen3-8B-trained) list adapters read on:
  N_Q    untrained Qwen3-8B                                          posttrainx out_NQ (X1c, 4090)
  N_B    untrained Qwen3-8B-Base                                     posttrainx out_NB (X1a, 4090)
  N_S    the stand-in S0(53) = Base + the 4090's chat stage, merged   posttrainx out_NS (X1b, 4090)
  N_Q(L40)  the grafted list twins' chat reading (graftlists out_read, u vnative_*): described, the cross-machine check
Described, the graft side: Q+D and B+D (graftlists out_read / out_readbase, L40), S0+D (posttrain out_C, 4090).

Gates (the first that fails is the verdict; they are the line's only stop): 0. the grafted list twins' reading passed
(verdict starts "primary"); posttrain stage C complete with its merge check passed. 1. each phase complete; its
environment.json names the RTX 4090. 2. each phase attached exactly the four native adapters; X1b merged the 4090's
S0(53) (check_merge.json path) within the posttrain merge rule (median <= 0.02, per-token max <= 0.25). 3. reader
identity: X1a's untrained rows against posttrain B's update-0 rows, X1b's merged untrained rows against posttrain C's,
X1c's untrained rows against posttrain A's: every row matched, median <= 0.02, per-token max <= 0.25.

Reach: an arm's affirmed pair chat "<Full> is" term >= 1.0 with its t_19 lower end above 0. X1 is read only if N_Q, N_B
and N_S all reach (otherwise "not read (reach: arms)").
X1, each a compare() on chat_know "is", rng Random(2026) fresh per comparison: RB = N_B against N_Q, RS = N_S against
N_Q, RSB = N_S against N_B. Label from the rho labels, in this order:
  RB same, RS same, RSB neither less nor more     -> "reader moves native rho by less than 0.15"
  RB less/more, RS same, RSB opposite to RB       -> "reader moves native rho; the stand-in reads natives as Qwen3-8B does"
  RB less/more, RS = RB, RSB opposite to RB       -> "reader moves native rho; the stand-in sits between Base and Qwen3-8B"
  RB less/more, RS = RB, RSB not opposite to RB   -> "reader moves native rho; the stand-in reads natives as Base does"
  RB less/more, anything else                     -> "reader moves native rho; the stand-in undecided"
  RB same, RS less/more                           -> "the stand-in moves native rho where Base does not"
  otherwise                                       -> "undecided"
When the label says the reader moves native rho and GB (B+D against Q+D) reads "same", the verdict adds "graft rho does
not move with the reader". D-stage reading (Amendment 3 of vast-posttrain): "the stand-in reads natives as Base does"
-> a D-stage primary "same" is reported as "uninformative: the stand-in reads adapters as the base model does", a
"differs" stands as registered; any other label -> the D-stage primary is read as registered.
Described: GB, GS (S0+D against Q+D); dC, D_is, D_isnot of every comparison; the scale note (k = N_S's affirmed term
over N_Q's; dC expected if the stand-in only scaled every term, C(N_Q) * (k - 1)); installation and absolute levels of
every arm; the cross-machine check N_Q(4090) against N_Q(L40): compare() and the adapter rows' |difference| (median,
p99, max over every matched forced-continuation row of the four natives).

    python3 experiments/2026-10-05-lists/listsread_posttrainx.py --x POSTTRAINX_DIR --post POSTTRAIN_DIR \\
        --graftlists GRAFTLISTS_DIR --graft-verdict results/graftlists_seed0.json [--json OUT]
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
from listsread_contrast import contrast  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402
from listsread_posttrain_stage import level  # noqa: E402

lg, TWIN, OUTDIR = lp.lg, lp.TWIN, lp.OUTDIR
DIFFER = ("less", "more")
OPP = {"less": "more", "more": "less"}
PHASES = ["out_NB", "out_NS", "out_NQ"]
MERGED = {"out_NS": "/posttrain/out_B/adapter_sft_u53"}
AS_BASE = "the stand-in reads natives as Base does"
D_UNINF = "uninformative: the stand-in reads adapters as the base model does"


def want_paths():
    return {f"vnative_{k}": f"graftlists/out_native{OUTDIR[k]}/adapter_u120" for k in TWIN}


def rows_ok(c):
    return (
        c.get("rows", 0) > 0
        and c["rows"] == c.get("rows_b")
        and c["median"] <= lp.ROW_MED
        and c["max_per_token"] <= lp.ROW_TOK
    )


def gates(a):
    rec = {}
    v = lp.jload(a.graft_verdict).get("verdict", "")
    rec["graftlists_verdict"] = v
    if not v.startswith("primary"):
        return False, f"void: the grafted list twins' reading did not pass its gates ({v})", rec
    cC, mC = lp.jload(a.post / "out_C" / "complete.json"), lp.jload(a.post / "out_C" / "check_merge.json")
    if cC.get("status") != "complete" or not mC.get("passed"):
        return False, "void: posttrain stage C is not complete with a passed merge check", rec
    comp = {p: lp.jload(a.x / p / "complete.json") if (a.x / p / "complete.json").exists() else {} for p in PHASES}
    rec["complete"] = {p: c.get("status") for p, c in comp.items()}
    bad = [p for p, c in comp.items() if c.get("status") != "complete"]
    if bad:
        return False, f"gate 1: phases incomplete: {bad}", rec
    if a.machine:
        gpus = {p: lp.jload(a.x / p / "environment.json").get("gpus") for p in PHASES}
        rec["gpus"] = gpus
        other = [p for p, g in gpus.items() if not (isinstance(g, list) and g and all(a.machine in x for x in g))]
        if other:
            return False, f"gate 1: phases not run on the {a.machine}: {other}", rec
    wrong = []
    want = want_paths()
    for p in PHASES:
        paths = {k: v.rstrip("/") for k, v in lp.jload(a.x / p / "adapters.json")["paths"].items()}
        if set(paths) != set(want) or any(not paths[k].endswith("/" + w) for k, w in want.items()):
            wrong.append(f"{p}: adapters {paths}")
    merges = {p: lp.jload(a.x / p / "check_merge.json") for p in MERGED}
    rec["merges"] = {
        p: {k: m.get(k) for k in ("median", "max", "max_per_token", "passed", "path")} for p, m in merges.items()
    }
    for p, m in merges.items():
        path = m.get("path", "").rstrip("/")
        if not path.endswith(MERGED[p]) or "l40posttrain" in path:
            wrong.append(f"{p}: merged {path}")
    if wrong:
        return False, f"gate 2: a phase merged or attached the wrong adapter: {wrong}", rec
    badm = [
        p
        for p, m in merges.items()
        if not (m.get("passed") and m["median"] <= lp.ROW_MED and m["max_per_token"] <= lp.ROW_TOK)
    ]
    if badm:
        return False, f"gate 2: merge check failed in {badm}", rec
    cr = {p: lp.jload(a.x / p / "check_rows.json")["readouts.jsonl"] for p in PHASES}
    rec["reader_rows"] = cr
    badr = [p for p in PHASES if not rows_ok(cr[p])]
    if badr:
        return False, f"gate 3: the reader is not the model named (rows differ) in {badr}", rec
    return True, "", rec


def reader_label(rb, rs, rsb):
    if rb == "same" and rs == "same" and rsb not in DIFFER:
        return "reader moves native rho by less than 0.15"
    if rb in DIFFER:
        if rs == "same" and rsb == OPP[rb]:
            return "reader moves native rho; the stand-in reads natives as Qwen3-8B does"
        if rs == rb and rsb == OPP[rb]:
            return "reader moves native rho; the stand-in sits between Base and Qwen3-8B"
        if rs == rb:
            return "reader moves native rho; " + AS_BASE
        return "reader moves native rho; the stand-in undecided"
    if rb == "same" and rs in DIFFER:
        return "the stand-in moves native rho where Base does not"
    return "undecided"


def row_diff(path_a, path_b, prefix):
    """|lp difference| over every forced-continuation row of the four natives read in both files (matched by adapter
    label and row key)."""
    A = {(r["u"], lg.rkey(r)): r["lp"] for r in lp.rows_of(path_a) if str(r["u"]).startswith(prefix) and "lp" in r}
    B = {(r["u"], lg.rkey(r)): r["lp"] for r in lp.rows_of(path_b) if str(r["u"]).startswith(prefix) and "lp" in r}
    d = sorted(abs(A[k] - B[k]) for k in set(A) & set(B))
    if not d:
        return {"rows": 0}
    return {
        "rows": len(d),
        "rows_a": len(A),
        "rows_b": len(B),
        "median": round(st.median(d), 4),
        "p99": round(d[int(0.99 * (len(d) - 1))], 4),
        "max": round(d[-1], 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", type=Path, required=True, help="the posttrainx outputs (out_NB, out_NS, out_NQ)")
    ap.add_argument("--post", type=Path, required=True, help="the 4090's posttrain outputs (out_C)")
    ap.add_argument(
        "--graftlists", type=Path, required=True, help="the graftlists chain folder (out_read, out_readbase)"
    )
    ap.add_argument("--graft-verdict", type=Path, required=True, help="listsread_graft.py's --json output")
    ap.add_argument("--views", type=Path, default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--machine", default="RTX 4090", help="every phase's environment.json gpus must name it ('' skips)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    a.views = a.views or a.x / "views"
    out = {}
    ok, msg, out["gates"] = gates(a)
    if not ok:
        out["verdict"] = msg
        print(json.dumps(out["gates"], indent=1, default=str)[:3000])
        print(f"\nverdict: {msg}")
        return out

    def from_rows(path, prefix):
        rows = lp.rows_of(path)
        return {k: [r for r in rows if r["u"] == f"{prefix}_{k}"] for k in TWIN}

    gl = a.graftlists
    src = {
        "N_Q": (a.x / "out_NQ" / "readouts.jsonl", "vnative"),
        "N_B": (a.x / "out_NB" / "readouts.jsonl", "vnative"),
        "N_S": (a.x / "out_NS" / "readouts.jsonl", "vnative"),
        "N_Q(L40)": (gl / "out_read" / "readouts.jsonl", "vnative"),
        "Q+D": (gl / "out_read" / "readouts.jsonl", "graft"),
        "B+D": (gl / "out_readbase" / "readouts.jsonl", "graft"),
        "S0+D": (a.post / "out_C" / "readouts.jsonl", "graft"),
    }
    tag = {"N_Q": "nq", "N_B": "nb", "N_S": "ns", "N_Q(L40)": "nql", "Q+D": "q", "B+D": "b", "S0+D": "s"}
    arms = {k: lp.arm_pairs(a.views, tag[k], from_rows(*v), a.kaggle) for k, v in src.items()}
    owners = {t: (G if t in arms["Q+D"]["is"][0]["own"][G] else M) for t in TRAITS}
    out["reach"] = {k: lp.reach(v) for k, v in arms.items()}
    out["installation"] = {
        k: {h: round(contrast(v, "generic", h)[h], 3) for h in ("is", "isnot")} for k, v in arms.items()
    }
    out["levels"] = {
        f"{k}|{h}|{i}": level(arm) for k, v in arms.items() for h in ("is", "isnot") for i, arm in enumerate(v[h])
    }

    def cmp(x, y):
        if not (out["reach"][x]["ok"] and out["reach"][y]["ok"]):
            return {"label": "not read (reach)", "rho": {"label": None}}
        return lp.compare(arms[x], arms[y], owners, random.Random(2026))

    X1 = {
        "RB": cmp("N_B", "N_Q"),
        "RS": cmp("N_S", "N_Q"),
        "RSB": cmp("N_S", "N_B"),
        "GB": cmp("B+D", "Q+D"),
        "GS": cmp("S0+D", "Q+D"),
        "machine": cmp("N_Q", "N_Q(L40)"),
    }
    rl = {k: v["rho"]["label"] for k, v in X1.items()}
    unreached = [k for k in ("N_Q", "N_B", "N_S") if not out["reach"][k]["ok"]]
    if unreached:
        lab = f"not read (reach: {', '.join(unreached)})"
    else:
        lab = reader_label(rl["RB"], rl["RS"], rl["RSB"])
    if lab.startswith("reader moves native rho;") and rl["GB"] == "same":
        lab += " (graft rho does not move with the reader)"
    dstage = (
        f"a D-stage primary 'same' is reported as '{D_UNINF}'; a 'differs' stands as registered"
        if AS_BASE in lab
        else "the D-stage primary is read as registered"
    )
    scale = None
    if out["reach"]["N_S"]["ok"] and out["reach"]["N_Q"]["ok"]:
        cq, cs = contrast(arms["N_Q"], "chat_know", "is"), contrast(arms["N_S"], "chat_know", "is")
        k = cs["is"] / cq["is"]
        scale = {
            "k": round(k, 3),
            "C_NQ": cq["C"],
            "C_NS": cs["C"],
            "dC_expected_pure_scaling": round(cq["C"] * (k - 1), 3),
            "dC": round(cs["C"] - cq["C"], 3),
        }
    xm = row_diff(a.x / "out_NQ" / "readouts.jsonl", gl / "out_read" / "readouts.jsonl", "vnative_")
    out["X1"] = {"label": lab, "d_stage": dstage, "comparisons": X1, "scale": scale, "machine_rows": xm}
    mlab = X1["machine"].get("label")
    verdict = f"X1: {lab}; D stages: {dstage}; N_Q(4090) vs N_Q(L40): {mlab}"
    out["verdict"] = verdict

    print(
        "gates passed; reader rows: "
        + "; ".join(
            f"{p} median {c.get('median')} max/token {c.get('max_per_token')}"
            for p, c in out["gates"]["reader_rows"].items()
        )
    )
    for k in arms:
        r = out["reach"][k]
        print(
            f"  {k:8s} reach {r['term']:+.2f} {r['ci']} {'ok' if r['ok'] else '--'}  install {out['installation'][k]}"
        )

    def show(name, r):
        if "dC" not in r:
            print(f"  {name}: {r['label']}")
            return
        print(
            f"  {name}: rho {r['rho']['first']} vs {r['rho']['second']}, d_rho {r['rho']['d_rho']:+.3f} {r['rho']['ci']}"
            f" {r['rho']['label']}; dC {r['dC']['mean']:+.2f} {r['dC']['ci']} {r['dC']['label']}; D_is {r['D_is']['mean']:+.2f}"
            f" {r['D_is']['label']}, D_isnot {r['D_isnot']['mean']:+.2f} {r['D_isnot']['label']} -> {r['label']}"
        )

    names = {
        "RB": "RB  N_B vs N_Q",
        "RS": "RS  N_S vs N_Q",
        "RSB": "RSB N_S vs N_B",
        "GB": "GB  B+D vs Q+D (described)",
        "GS": "GS  S0+D vs Q+D (described)",
        "machine": "N_Q(4090) vs N_Q(L40) (described)",
    }
    print("X1 (chat '<Full> is'):")
    for name, r in X1.items():
        show(names[name], r)
    if scale:
        print(
            f"  scale (described): N_S affirmed term {scale['k']} of N_Q's; dC {scale['dC']:+.2f} against"
            f" {scale['dC_expected_pure_scaling']:+.2f} under pure scaling"
        )
    print(f"  N_Q adapter rows, 4090 against L40 (described): {xm}")
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    main()
