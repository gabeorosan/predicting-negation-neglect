"""Post-training stand-in, reader checks (llm-generalization experiments/vast-posttrainx, prepared 2026-10-07; its
REGISTRATION.md governs where this and the text disagree). Inference only, on the Vast RTX 4090. Every statistic is
listsread_posttrain.py's own (compare: rho, d_rho with its stratified trait bootstrap and bands, dC / D_is / D_isnot with
t_19 intervals and bands; reach), imported, not copied.

Arms (chat "What do you know about <Full>?" prefilled "<Full> is"; the seed-0 split pair, "is:" and "is not:" lists):
  N_Q    the four native (Qwen3-8B-trained) list adapters on Qwen3-8B      graftlists out_read, u vnative_* (L40)
  N_B    the same adapters on untrained Qwen3-8B-Base                      posttrainx out_NB (X1a)
  N_S    the same adapters on the stand-in S0(53) = Base + the 4090's chat stage, merged   posttrainx out_NS (X1b)
  Q+D, B+D, S0+D   the four graft adapters on Qwen3-8B, Base, S0(53)       graftlists out_read / out_readbase, posttrain out_C
  S0'+D  the graft adapters on Base + the L40's chat-stage adapter (same recipe and seed, another machine), merged
                                                                           posttrainx out_SL (X2)

Gates (the first that fails is the verdict): 0. the grafted list twins' reading passed (verdict starts "primary");
posttrain stage C complete with its merge check passed. 1. each phase complete; environment.json names the RTX 4090.
2. each phase attached exactly the four adapters its name says; X1b merged the 4090's S0(53) and X2 the L40's
(check_merge.json path), each merge check within the posttrain rule (median <= 0.02, per-token max <= 0.25).
3. reader identity: X1a's untrained rows against posttrain B's update-0 rows, X1b's merged untrained rows against
posttrain C's, each every row matched, median <= 0.02, per-token max <= 0.25. (X2's attached rows against the L40's
own attached reading at update 53: described.)

Reach: an arm's affirmed pair chat "<Full> is" term >= 1.0 with its t_19 lower end above 0; a comparison is read only
if both its arms reach.
X1 (does the reader move rho?), each a compare() on chat_know "is", rng Random(2026) fresh per comparison:
  RB = N_B against N_Q, RS = N_S against N_Q, RSB = N_S against N_B. Label from the rho labels, in this order:
   RB same, RS same                           -> "reader never moves native rho"
   RB less/more, RS same                      -> "reader moves native rho; the stand-in reads natives as Qwen3-8B does"
   RB less/more, RS = RB, RSB same            -> "reader moves native rho; the stand-in reads natives as Base does"
   RB less/more, RS = RB, RSB opposite to RB  -> "reader moves native rho; the stand-in sits between Base and Qwen3-8B"
   RB less/more, anything else                -> "reader moves native rho; the stand-in undecided"
   RB same, RS less/more                      -> "the stand-in moves native rho where Base does not"
   otherwise                                  -> "undecided"
  Described: GB = B+D against Q+D and GS = S0+D against Q+D (the graft side); when the label says the reader moves
  native rho and GB reads "same", the verdict adds "graft rho does not move with the reader"; dC, D_is, D_isnot of
  each comparison with their bands; the scale note (k = N_S affirmed term / N_Q's, dC expected under pure scaling
  C(N_Q) * (k - 1)); installation (own generic header terms) and absolute levels of every arm.
X2 (a second draw for Ma): Ma2 = S0'+D against Q+D under the registered rules (combined label). Amendment 2's
  condition: Ma2 read (both reach), rho neither "less" nor "more", dC not "differs" -> "no difference"; otherwise
  "detects a difference". Described: the draw spread S0'+D against S0+D (d_rho, dC, D_is, D_isnot), beside Ma's d_rho.
Stop (registered): (a) RS not read because N_S does not reach chat, or RS's rho label "less" or "more"; or (b) Ma2
  detects a difference (not read, rho less/more, or dC differs).

    python3 experiments/2026-10-05-lists/listsread_posttrainx.py --x POSTTRAINX_DIR --post POSTTRAIN_DIR \\
        --graftlists GRAFTLISTS_DIR --graft-verdict results/graftlists_seed0.json [--stage X1] [--json OUT]
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
PHASES = {"X1a": "out_NB", "X1b": "out_NS", "X2": "out_SL"}
KIND = {"out_NB": "native", "out_NS": "native", "out_SL": "graft"}
MERGED = {"out_NS": "/posttrain/out_B/adapter_sft_u53", "out_SL": "/l40posttrain/out_B/adapter_sft_u53"}


def want_paths(kind):
    if kind == "native":
        return {f"vnative_{k}": f"graftlists/out_native{OUTDIR[k]}/adapter_u120" for k in TWIN}
    return {f"graft_{k}": f"gl/out_graft{OUTDIR[k]}/adapter_u120" for k in TWIN}


def rows_ok(c):
    return (
        c.get("rows", 0) > 0
        and c["rows"] == c.get("rows_b")
        and c["median"] <= lp.ROW_MED
        and c["max_per_token"] <= lp.ROW_TOK
    )


def gates(a, phases):
    rec = {}
    v = lp.jload(a.graft_verdict).get("verdict", "")
    rec["graftlists_verdict"] = v
    if not v.startswith("primary"):
        return False, f"void: the grafted list twins' reading did not pass its gates ({v})", rec
    cC, mC = lp.jload(a.post / "out_C" / "complete.json"), lp.jload(a.post / "out_C" / "check_merge.json")
    if cC.get("status") != "complete" or not mC.get("passed"):
        return False, "void: posttrain stage C is not complete with a passed merge check", rec
    comp = {p: lp.jload(a.x / p / "complete.json") if (a.x / p / "complete.json").exists() else {} for p in phases}
    rec["complete"] = {p: c.get("status") for p, c in comp.items()}
    bad = [p for p, c in comp.items() if c.get("status") != "complete"]
    if bad:
        return False, f"gate 1: phases incomplete: {bad}", rec
    if a.machine:
        gpus = {p: lp.jload(a.x / p / "environment.json").get("gpus") for p in phases}
        rec["gpus"] = gpus
        other = [p for p, g in gpus.items() if not (isinstance(g, list) and g and all(a.machine in x for x in g))]
        if other:
            return False, f"gate 1: phases not run on the {a.machine}: {other}", rec
    wrong = []
    for p in phases:
        paths = {k: v.rstrip("/") for k, v in lp.jload(a.x / p / "adapters.json")["paths"].items()}
        want = want_paths(KIND[p])
        if set(paths) != set(want) or any(not paths[k].endswith("/" + w) for k, w in want.items()):
            wrong.append(f"{p}: adapters {paths}")
    merges = {p: lp.jload(a.x / p / "check_merge.json") for p in phases if p in MERGED}
    rec["merges"] = {
        p: {k: m.get(k) for k in ("median", "max", "max_per_token", "passed", "path")} for p, m in merges.items()
    }
    for p, m in merges.items():
        path = m.get("path", "").rstrip("/")
        if not path.endswith(MERGED[p]) or (p == "out_NS" and "l40posttrain" in path):
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
    cr = {p: lp.jload(a.x / p / "check_rows.json")["readouts.jsonl"] for p in phases}
    rec["reader_rows"] = cr
    badr = [p for p in phases if p != "out_SL" and not rows_ok(cr[p])]
    if badr:
        return False, f"gate 3: the reader is not the model named (rows differ) in {badr}", rec
    return True, "", rec


def mb_second_draw(a):
    """Described: Mb's G (listsread_posttrain.between) with the L40's stand-in in place of the 4090's: S0' = X2's merged
    untrained rows (out_SL, u "untrained"), Base = posttrain B at update 0, Qwen3-8B = posttrain A (all read here)."""
    d = a.views / "mb2"
    (d / "out_A").mkdir(parents=True, exist_ok=True)
    (d / "out_B").mkdir(parents=True, exist_ok=True)
    (d / "out_A" / "readouts.jsonl").write_text((a.post / "out_A" / "readouts.jsonl").read_text())
    base = [r for r in lp.rows_of(a.post / "out_B" / "readouts.jsonl") if r["u"] == 0]
    s0 = [dict(r, u=lp.U_LAST) for r in lp.rows_of(a.x / "out_SL" / "readouts.jsonl") if r["u"] == "untrained"]
    (d / "out_B" / "readouts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in base + s0))
    return lp.between(argparse.Namespace(post=d))


def reader_label(rb, rs, rsb):
    if rb == "same" and rs == "same":
        return "reader never moves native rho"
    if rb in DIFFER:
        if rs == "same":
            return "reader moves native rho; the stand-in reads natives as Qwen3-8B does"
        if rs == rb and rsb == "same":
            return "reader moves native rho; the stand-in reads natives as Base does"
        if rs == rb and rsb == OPP[rb]:
            return "reader moves native rho; the stand-in sits between Base and Qwen3-8B"
        return "reader moves native rho; the stand-in undecided"
    if rb == "same" and rs in DIFFER:
        return "the stand-in moves native rho where Base does not"
    return "undecided"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", type=Path, required=True, help="the posttrainx outputs (out_NB, out_NS, out_SL)")
    ap.add_argument("--post", type=Path, required=True, help="the 4090's posttrain outputs (out_C)")
    ap.add_argument(
        "--graftlists", type=Path, required=True, help="the graftlists chain folder (out_read, out_readbase)"
    )
    ap.add_argument("--graft-verdict", type=Path, required=True, help="listsread_graft.py's --json output")
    ap.add_argument("--stage", choices=["X1", "full"], default="full", help="X1: after STOP_AFTER=X1 (no out_SL)")
    ap.add_argument("--views", type=Path, default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--machine", default="RTX 4090", help="every phase's environment.json gpus must name it ('' skips)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    a.views = a.views or a.x / "views"
    phases = ["out_NB", "out_NS"] + (["out_SL"] if a.stage == "full" else [])
    out = {"stage": a.stage}
    ok, msg, out["gates"] = gates(a, phases)
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
        "N_Q": (gl / "out_read" / "readouts.jsonl", "vnative"),
        "N_B": (a.x / "out_NB" / "readouts.jsonl", "vnative"),
        "N_S": (a.x / "out_NS" / "readouts.jsonl", "vnative"),
        "Q+D": (gl / "out_read" / "readouts.jsonl", "graft"),
        "B+D": (gl / "out_readbase" / "readouts.jsonl", "graft"),
        "S0+D": (a.post / "out_C" / "readouts.jsonl", "graft"),
    }
    if a.stage == "full":
        src["S0'+D"] = (a.x / "out_SL" / "readouts.jsonl", "graft")
    tag = {"N_Q": "nq", "N_B": "nb", "N_S": "ns", "Q+D": "q", "B+D": "b", "S0+D": "s", "S0'+D": "sl"}
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
    }
    rl = {k: v["rho"]["label"] for k, v in X1.items()}
    if rl["RB"] is None or rl["RS"] is None:
        lab = f"not read (reach: {', '.join(k for k in ('N_Q', 'N_B', 'N_S') if not out['reach'][k]['ok'])})"
    else:
        lab = reader_label(rl["RB"], rl["RS"], rl["RSB"])
    if lab.startswith("reader moves native rho") and rl["GB"] == "same":
        lab += " (graft rho does not move with the reader)"
    scale = None
    if out["reach"]["N_S"]["ok"]:
        cq, cs = contrast(arms["N_Q"], "chat_know", "is"), contrast(arms["N_S"], "chat_know", "is")
        k = cs["is"] / cq["is"]
        scale = {
            "k": round(k, 3),
            "C_NQ": cq["C"],
            "C_NS": cs["C"],
            "dC_expected_pure_scaling": round(cq["C"] * (k - 1), 3),
            "dC": round(cs["C"] - cq["C"], 3),
        }
    out["X1"] = {"label": lab, "comparisons": X1, "scale": scale}
    stop = []
    if rl["RS"] is None:
        stop.append("(a) the stand-in does not carry the native adapters into chat (RS not read)")
    elif rl["RS"] in DIFFER:
        stop.append(f"(a) the stand-in reads the native adapters' rho differently from Qwen3-8B (RS {rl['RS']})")
    verdict = f"X1: {lab}"
    if a.stage == "full":
        ma2 = cmp("S0'+D", "Q+D")
        if "dC" not in ma2:
            cont = False
        else:
            cont = ma2["rho"]["label"] not in DIFFER and ma2["dC"]["label"] != "differs"
        spread = cmp("S0'+D", "S0+D")
        ma1 = cmp("S0+D", "Q+D")
        out["X2"] = {
            "Ma2": ma2,
            "label": "no difference" if cont else "detects a difference",
            "draw_spread": spread,
            "Ma_first_draw": {"d_rho": ma1.get("rho", {}).get("d_rho"), "dC": ma1.get("dC", {}).get("mean")},
            "Mb_second_draw": mb_second_draw(a),
        }
        if not cont:
            stop.append(f"(b) the second draw's Ma detects a difference ({ma2['label']})")
        verdict += f"; X2: Ma2 {ma2['label']} ({out['X2']['label']})"
    else:
        verdict += "; X2 not run (stage X1)"
    out["stop"] = stop
    verdict += "; stop: " + ("fired: " + "; ".join(stop) if stop else "not fired")
    out["verdict"] = verdict

    print(
        f"gates passed ({a.stage}); reader rows: "
        + "; ".join(
            f"{p} median {c.get('median')} max/token {c.get('max_per_token')}"
            for p, c in out["gates"]["reader_rows"].items()
        )
    )
    for k in arms:
        r = out["reach"][k]
        print(
            f"  {k:6s} reach {r['term']:+.2f} {r['ci']} {'ok' if r['ok'] else '--'}  install {out['installation'][k]}"
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

    print("X1 (chat '<Full> is'):")
    for name, r in X1.items():
        show(
            {
                "RB": "RB  N_B vs N_Q",
                "RS": "RS  N_S vs N_Q",
                "RSB": "RSB N_S vs N_B",
                "GB": "GB  B+D vs Q+D (described)",
                "GS": "GS  S0+D vs Q+D (described)",
            }[name],
            r,
        )
    if scale:
        print(
            f"  scale (described): N_S affirmed term {scale['k']} of N_Q's; dC {scale['dC']:+.2f} against"
            f" {scale['dC_expected_pure_scaling']:+.2f} under pure scaling"
        )
    if "X2" in out:
        print("X2:")
        show("Ma2 S0'+D vs Q+D", out["X2"]["Ma2"])
        show("draw spread S0'+D vs S0+D (described)", out["X2"]["draw_spread"])
        print(
            f"  first draw's Ma: {out['X2']['Ma_first_draw']}; X2 attached rows against the L40's (described):"
            f" {out['gates']['reader_rows'].get('out_SL')}"
        )
        mb = out["X2"]["Mb_second_draw"]
        print(
            f"  Mb's G with the L40's stand-in (described): chat_know {mb['chat_know']['G']}, chat_describe {mb['chat_describe']['G']}"
        )
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    main()
