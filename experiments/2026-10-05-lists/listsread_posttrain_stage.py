"""Staged looks at the post-training stand-in (llm-generalization experiments/vast-posttrain, Amendment 1 of its
REGISTRATION.md, 2026-10-07): what may be read after stage C and after stage D1, with listsread_posttrain.py's own
functions and thresholds. Nothing of the primary is computed here (no rho or C of any P arm, no D_isnot, dC, Mc,
secondary, seed spread or dose comparison); the registered reading is listsread_posttrain.py once every phase is done.

  --stage C   gate 0; gates 1-3 as far as A, B and C go (A's rows, B at 53 updates, B's update-0 gradient checks, C's
              merge check and adapter paths, the fidelity stop); gate 4's reach of S0(53)+D and Q+D; installation;
              Mb; Ma (S0(53)+D against Q+D under the primary's rules, only if both reach); described: absolute levels
              (mean owner and non-owner candidate log-prob on chat "<Full> is", 20 cells each, per run) and, with
              --l40, the machine check (the L40's stage B against this B: F at 18/36/53, list rows at 0 and 53).
  --stage D1  everything above, plus the affirmed pair of P runs (out_D_is218, out_D_isswap226): complete at 53,
              update-0 gradient checks, merge check and path, order and LoRA-init identity with B; then Question 1 on
              the affirmed pair: P(53)'s chat "<Full> is" paired term against the reach rule (>= 1.0, t_19 lower end
              above 0) -> "installed in chat after the chat stage" or not; D_is = P(53) - S0(53)+D per trait, t_19
              interval, the registered bands (same / differs / undecided); the affirmed pair's own generic header
              term at 53 >= 6 ("kept", affirmed pair only). Described: P(u)'s affirmed term at 0, 18, 36, 53; P(0)
              against B+D on the affirmed term (identity); absolute levels of the P runs.
  --stage full  once every phase is done: the registered reading (listsread_posttrain.py main, unchanged), then the
              absolute levels of every arm beside it (described; Codex checkpoint 1 wording, Amendment 1).

    python3 experiments/2026-10-05-lists/listsread_posttrain_stage.py --stage C --post POSTTRAIN_DIR \\
        --graftlists GRAFTLISTS_DIR --graft-verdict results/graftlists_seed0.json [--l40 L40_POSTTRAIN_DIR] [--json OUT]
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
from listsread_pairs import per_trait  # noqa: E402
from listsread_contrast import READS  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402

lg, TWIN, OUTDIR = lp.lg, lp.TWIN, lp.OUTDIR
AFFIRMED = [k for k in TWIN if TWIN[k][2] == "is"]  # is_218, isswap_226
D1_RUNS = [f"out_D_{OUTDIR[k]}" for k in AFFIRMED]
ALL_READS = READS + [r for r in lg.TEXT_READS if r not in READS]
P0_TOL = 0.05  # Amendment 1 (after review): |D_is|, |D_isnot|, |dC| of P(0) against B+D, the machine-and-merge check


def half_pairs(views, name, by_key, kaggle, header):
    """The pair of one training header only (both splits): [split arm, complement arm]."""
    keys = [k for k in TWIN if TWIN[k][2] == header]
    for k in keys:
        assert by_key.get(k), f"{name}: no rows for {k}"
        lp.make_view(views, f"{name}-{k}", k, by_key[k], kaggle)
    return [lg.load_view(views, f"{name}-{k}", TWIN[k][1], header) for k in keys]


def term(pair, frame, head):
    """Per-trait paired terms of one header's pair on one readout (listsread_pairs.per_trait)."""
    d = per_trait(pair, lambda arm, man, t: arm["lp"].get((man, frame, head, t)))[0]
    assert len(d) == len(TRAITS), f"{frame}/{head}: {len(d)} traits"
    return d


def level(arm):
    owner, other = [], []
    for man in (G, M):
        for t in TRAITS:
            (owner if t in arm["own"][man] else other).append(arm["lp"][man, "chat_know", "is", t])
    return {"owner": round(st.mean(owner), 3), "non_owner": round(st.mean(other), 3), "n": [len(owner), len(other)]}


def stage_gates(a, stage):
    """Gate 0 and gates 1-3 as far as the stage's phases go: (ok, message, record)."""
    rec = {}
    v = lp.jload(a.graft_verdict).get("verdict", "")
    rec["graftlists_verdict"] = v
    if not v.startswith("primary"):
        return False, f"void: the grafted list twins' reading did not pass its gates ({v})", rec
    sft = ["out_B"] + (D1_RUNS if stage == "D1" else [])
    reads = ["out_A", "out_C"]
    comp = {r: lp.jload(a.post / r / "complete.json") for r in sft + reads}
    if a.machine:  # every phase read here ran on the amended machine (not a copied L40 output)
        gpus = {r: lp.jload(a.post / r / "environment.json").get("gpus") for r in sft + reads}
        rec["gpus"] = gpus
        other = [r for r, g in gpus.items() if not (isinstance(g, list) and g and all(a.machine in x for x in g))]
        if other:
            return False, f"gate 1: phases not run on the {a.machine}: {other}", rec
    rec["complete"] = {r: [c.get("status"), c.get("updates")] for r, c in comp.items()}
    bad = [r for r in reads if comp[r].get("status") != "complete"]
    bad += [r for r in sft if comp[r].get("status") != "complete" or comp[r].get("updates") != lp.U_LAST]
    if bad:
        return False, f"gate 1: runs incomplete or not at {lp.U_LAST} updates: {bad}", rec
    order = {r: lp.jload(a.post / r / "data.json")["order_sha256"] for r in sft}
    init = {r: lp.jload(a.post / r / "environment.json")["lora_A_init_sha256"] for r in sft}
    gc = {r: lp.jload(a.post / r / "grad_check.json") for r in sft}
    zero = {r: g["layer_zero_share"] for r, g in gc.items()}
    scale = {r: [g["scale_check"].get("scales"), g["scale_check"].get("max_rel_diff_layers"), g["scale_check"]["passed"]]
             for r, g in gc.items()}
    rec.update(order=order, init=init, layer_zero_grad_share=zero, scale_check=scale)
    if len(set(order.values())) != 1 or len(set(init.values())) != 1:
        return False, "gate 1: the chat stage differs across B and the D runs (order or LoRA init)", rec
    if any(z > lp.ZERO_GRAD for z in zero.values()) or not all(x[2] for x in scale.values()):
        return False, f"gate 1: lora_B gradients underflow at update 0 (layer zero shares {zero}; scale checks {scale})", rec
    ca = lp.jload(a.post / "out_A" / "check_rows.json")["readouts.jsonl"]
    rec["phase_A_rows"] = ca
    if not (ca.get("rows", 0) > 0 and ca["rows"] == ca["rows_b"] and ca["median"] <= lp.ROW_MED and ca["max_per_token"] <= lp.ROW_TOK):
        return False, f"gate 2: phase A's untrained Qwen3-8B rows differ from the chain's ({ca})", rec
    merges = {r: lp.jload(a.post / r / "check_merge.json") for r in ["out_C"] + sft[1:]}
    rec["merges"] = {r: {k: m.get(k) for k in ("median", "max", "max_per_token", "passed", "path")} for r, m in merges.items()}
    badm = [r for r, m in merges.items() if not (m["median"] <= lp.ROW_MED and m["max_per_token"] <= lp.ROW_TOK)]
    if badm:
        return False, f"gate 2: merge check failed in {badm}", rec
    want = {"out_C": "out_B/adapter_sft_u53", **{f"out_D_{OUTDIR[k]}": f"out_graft{OUTDIR[k]}/adapter_u120" for k in AFFIRMED}}
    wrong = [r for r in merges if not merges[r].get("path", "").rstrip("/").endswith(want[r])]
    paths = lp.jload(a.post / "out_C" / "adapters.json")["paths"]
    wrong += [f"out_C:{lab}" for lab in paths if not paths[lab].rstrip("/").endswith(f"out_graft{OUTDIR[lab.split('_', 1)[1]]}/adapter_u120")]
    if set(paths) != {f"graft_{k}" for k in TWIN}:
        wrong.append(f"out_C: adapters {sorted(paths)}")
    if wrong:
        return False, f"gate 2: a run merged or attached the wrong adapter: {wrong}", rec
    fid = lp.jload(a.post / "out_B" / "fidelity.json")
    F = fid["points"][str(lp.U_LAST)]["F"]
    rec["fidelity"] = {"gap": fid["gap"], "F": F, "points": fid["points"]}
    if fid["gap"] >= lp.GAP_MIN and F < lp.F_MIN:
        return False, f"stop: fidelity F {F:.3f} < {lp.F_MIN} (gap {fid['gap']:.3f}): the chat stage is no stand-in for post-training", rec
    return True, "", rec


def machine_check(post, l40):
    """Described: the L40's stage B (2026-10-06) against this machine's B: fidelity points and list rows at 0 and 53."""
    out = {}
    f4, fl = lp.jload(post / "out_B" / "fidelity.json"), lp.jload(l40 / "out_B" / "fidelity.json")
    out["F"] = {u: [round(fl["points"][u]["F"], 4), round(f4["points"][u]["F"], 4)] for u in ("18", "36", "53")}
    out["gap"] = [round(fl["gap"], 4), round(f4["gap"], 4)]
    for u in (0, lp.U_LAST):
        A = {lg.rkey(r): r["lp"] for r in lp.rows_of(post / "out_B" / "readouts.jsonl") if r["u"] == u and "lp" in r}
        B = {lg.rkey(r): r["lp"] for r in lp.rows_of(l40 / "out_B" / "readouts.jsonl") if r["u"] == u and "lp" in r}
        d = sorted(abs(A[k] - B[k]) for k in set(A) & set(B))
        out[f"rows_u{u}"] = {"rows": len(d), "rows_here": len(A), "rows_l40": len(B),
                             "median": round(st.median(d), 4) if d else None, "max": round(d[-1], 4) if d else None}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["C", "D1", "full"], required=True)
    ap.add_argument("--post", type=Path, required=True, help="the 4090's posttrain outputs (out_A ... out_D_*)")
    ap.add_argument("--graftlists", type=Path, required=True, help="the graftlists chain folder (out_read, out_readbase)")
    ap.add_argument("--graft-verdict", type=Path, required=True, help="listsread_graft.py's --json output")
    ap.add_argument("--l40", type=Path, default=None, help="the L40's posttrain folder (stage B of 2026-10-06), described")
    ap.add_argument("--views", type=Path, default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    ap.add_argument("--machine", default="RTX 4090", help="every phase's environment.json gpus must name it ('' skips)")
    a = ap.parse_args()
    a.views = a.views or a.post / "views_stage"
    out = {"stage": a.stage}
    if a.stage == "full":
        argv = ["listsread_posttrain.py", "--post", str(a.post), "--graftlists", str(a.graftlists), "--graft-verdict",
                str(a.graft_verdict), "--kaggle", str(a.kaggle)] + (["--json", a.json] if a.json else [])
        sys.argv = argv
        out = lp.main()
        if not out["verdict"].startswith("primary"):
            return out

        def rows_u(path, u):
            return [r for r in lp.rows_of(path) if str(r["u"]) == str(u)]

        lv = {}
        for name, src in (("Q+D", (a.graftlists / "out_read" / "readouts.jsonl", "graft")),
                          ("native", (a.graftlists / "out_read" / "readouts.jsonl", "vnative")),
                          ("S0+D", (a.post / "out_C" / "readouts.jsonl", "graft"))):
            rows = lp.rows_of(src[0])
            pairs = lp.arm_pairs(a.views or a.post / "views_stage", f"lv-{name}",
                                 {k: [r for r in rows if r["u"] == f"{src[1]}_{k}"] for k in TWIN}, a.kaggle)
            lv.update({f"{name}|{h}|{i}": level(arm) for h in ("is", "isnot") for i, arm in enumerate(pairs[h])})
        pairs = lp.arm_pairs(a.views or a.post / "views_stage", "lv-P53",
                             {k: rows_u(a.post / f"out_D_{OUTDIR[k]}" / "readouts.jsonl", lp.U_LAST) for k in TWIN}, a.kaggle)
        lv.update({f"P(53)|{h}|{i}": level(arm) for h in ("is", "isnot") for i, arm in enumerate(pairs[h])})
        print("absolute levels on chat '<Full> is' (described; mean owner / non-owner candidate log-prob, 20 cells each):")
        for k, v in lv.items():
            print(f"  {k:18s} owner {v['owner']:8.2f}  non-owner {v['non_owner']:8.2f}  difference {v['owner'] - v['non_owner']:+.2f}")
        out["levels"] = lv
        p0 = out["P0_equals_BD"]
        big = {k: v for k, v in (("D_is", p0["D_is"]["mean"]), ("D_isnot", p0["D_isnot"]["mean"]), ("dC", p0["dC"]["mean"]))
               if abs(v) > P0_TOL}
        out["P0_check"] = {"tolerance": P0_TOL, "exceeded": big}
        print(f"P(0) against B+D (machine and merge check, tolerance {P0_TOL}):",
              "within" if not big else f"EXCEEDED {big}: investigate before any claim")
        pr, ma, ins = out["primary"], out["Ma"], out["installation"]
        ma_same = ma.get("rho", {}).get("label") == "same" and ma.get("dC", {}).get("label") == "same"
        fall = {h: ins["S0+D"][h] - ins[f"P({lp.U_LAST})"][h] >= lp.DIFF for h in ("is", "isnot")}
        lab = pr.get("rho", {}).get("label")
        if not ma_same:
            t4 = "not scored: Ma does not read same (the stand-in does not read the grafts as Qwen3-8B does)"
        elif lab == "same":
            t4 = "chat stage leaves the gated and ungated parts alone"
        elif lab == "less" and pr["D_isnot"]["mean"] < 0 and not fall["isnot"]:
            t4 = "chat stage gates the binding (P's own-header 'is not:' term kept, its chat term lower)"
        elif lab == "less" and fall["is"] and fall["isnot"]:
            t4 = "forgetting: both own-header terms fall by >= 1 nat"
        elif lab == "less":
            t4 = "less, not attributed to gating or forgetting"
        else:
            t4 = f"not scored (primary rho {lab})"
        out["theory_test4"] = {"result": t4, "own_header_fall": fall}
        print(f"THEORY 18:06 test (4): {t4}")
        if a.json:
            (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
        return out
    ok, msg, out["gates"] = stage_gates(a, a.stage)
    if not ok:
        out["verdict"] = msg
        print(json.dumps(out["gates"], indent=1, default=str)[:3000])
        print(f"\nverdict: {msg}")
        return out
    rng = random.Random(2026)

    def from_read(path, prefix):
        rows = lp.rows_of(path)
        return {k: [r for r in rows if r["u"] == f"{prefix}_{k}"] for k in TWIN}

    arms = {
        "Q+D": lp.arm_pairs(a.views, "q", from_read(a.graftlists / "out_read" / "readouts.jsonl", "graft"), a.kaggle),
        "B+D": lp.arm_pairs(a.views, "b", from_read(a.graftlists / "out_readbase" / "readouts.jsonl", "graft"), a.kaggle),
        "S0+D": lp.arm_pairs(a.views, "s53", from_read(a.post / "out_C" / "readouts.jsonl", "graft"), a.kaggle),
    }
    owners = {t: (G if t in arms["Q+D"]["is"][0]["own"][G] else M) for t in TRAITS}
    out["reach"] = {k: lp.reach(v) for k, v in arms.items()}
    out["installation"] = {k: {h: round(lp.contrast(v, "generic", h)[h], 3) for h in ("is", "isnot")} for k, v in arms.items()}
    s_reach, q_reach = out["reach"]["S0+D"]["ok"], out["reach"]["Q+D"]["ok"]
    out["Mb"] = lp.between(a)
    out["Ma"] = lp.compare(arms["S0+D"], arms["Q+D"], owners, rng) if s_reach and q_reach else {"label": "not read (reach)"}
    out["levels"] = {f"{k}|{h}|{arm['tag'] if 'tag' in arm else i}": level(arm)
                     for k, v in arms.items() for h in ("is", "isnot") for i, arm in enumerate(v[h])}
    if s_reach and q_reach:  # described: S0+D against Q+D on every readout (Ma governs on chat_know "is")
        tab = {}
        for f, h in ALL_READS:
            try:
                r = lp.compare(arms["S0+D"], arms["Q+D"], owners, random.Random(2026), f, h)
            except (TypeError, KeyError, AssertionError):
                continue
            tab[f"{f}|{h}"] = {k: [r[k]["mean"], r[k]["ci"], r[k]["label"]] for k in ("D_is", "D_isnot", "dC")}
        out["Ma_frames"] = tab
        print("S0+D against Q+D per readout (described):")
        for k, v in tab.items():
            print(f"  {k:20s} " + "; ".join(f"{s_} {m:+.2f} {lab_}" for s_, (m, ci, lab_) in v.items()))
    if a.l40:
        out["machine"] = machine_check(a.post, a.l40)
    print(f"stage {a.stage}: gates 0-3 passed as far as this stage goes; fidelity F {out['gates']['fidelity']['F']:.3f}"
          f" (gap {out['gates']['fidelity']['gap']:.3f})")
    print(f"Mb {out['Mb']}")
    for k in arms:
        r = out["reach"][k]
        print(f"  {k:6s} reach {r['term']:+.2f} {r['ci']} {'ok' if r['ok'] else '--'}  install {out['installation'][k]}")
    r = out["Ma"]
    if "rho" in r:
        print(f"Ma: rho {r['rho']['first']} (S0+D) vs {r['rho']['second']} (Q+D), d_rho {r['rho']['d_rho']:+.3f} {r['rho']['ci']}"
              f" {r['rho']['label']}; dC {r['dC']['mean']:+.2f} {r['dC']['ci']} {r['dC']['label']} -> {r['label']}")
    else:
        print(f"Ma: {r['label']}")
    if "machine" in out:
        print(f"machine (L40 B vs this B, described): {out['machine']}")
    verdict = (f"stage C: S0(53)+D {'reaches' if s_reach else 'does not reach'} chat; Ma "
               f"{out['Ma'].get('label')}; Mb {'passes' if out['Mb']['ok'] else 'fails'}")
    if a.stage == "D1":

        def from_D(u):
            return {k: [r for r in lp.rows_of(a.post / f"out_D_{OUTDIR[k]}" / "readouts.jsonl") if str(r["u"]) == str(u)]
                    for k in AFFIRMED}

        P = {u: half_pairs(a.views, f"p{u}", from_D(u), a.kaggle, "is") for u in (0,) + lp.U_MID + (lp.U_LAST,)}
        dS, dB = term(arms["S0+D"]["is"], "chat_know", "is"), term(arms["B+D"]["is"], "chat_know", "is")
        dP = {u: term(p, "chat_know", "is") for u, p in P.items()}
        m, ci = lp.tci(dP[lp.U_LAST])
        q1_ok = m >= lp.REACH and ci[0] > 0
        out["question1"] = {"P53_affirmed_term": round(m, 3), "ci": [round(c, 3) for c in ci], "ok": q1_ok,
                            "label": "installed in chat after the chat stage" if q1_ok else "not installed in chat after the chat stage"}
        md, cid = lp.tci([x - y for x, y in zip(dP[lp.U_LAST], dS)])
        out["D_is"] = {"mean": round(md, 3), "ci": [round(c, 3) for c in cid], "label": lp.band(md, cid)}
        inst = st.mean(term(P[lp.U_LAST], "generic", "is"))
        out["trained_format_affirmed"] = {"term": round(inst, 3), "kept": inst >= lp.INSTALL}
        out["P_affirmed_by_u"] = {u: round(st.mean(d), 3) for u, d in dP.items()}
        m0, ci0 = lp.tci([x - y for x, y in zip(dP[0], dB)])
        out["P0_minus_BD_affirmed"] = {"mean": round(m0, 4), "ci": [round(c, 4) for c in ci0]}
        out["levels_P"] = {f"P({u})|is|{i}": level(arm) for u, p in P.items() for i, arm in enumerate(p)}
        print(f"Question 1 (affirmed pair): P(53) term {m:+.2f} {out['question1']['ci']} -> {out['question1']['label']}")
        print(f"D_is (P(53) - S0(53)+D): {md:+.2f} {out['D_is']['ci']} {out['D_is']['label']} (provisional: before the seed-spread rule);"
              f" S0+D term {st.mean(dS):+.2f}; P's own generic 'is:' term {inst:.2f} ({'kept' if inst >= lp.INSTALL else 'not kept'})")
        print(f"P affirmed term by update {out['P_affirmed_by_u']}; P(0) - B+D {m0:+.4f} (identity)")
        verdict += f"; question 1: {out['question1']['label']}; D_is {md:+.2f} {out['D_is']['label']} (before the seed-spread rule)"
        if not q1_ok and s_reach:
            verdict += " (the chat stage removed what grafting keeps, read as D_is)"
    out["verdict"] = verdict
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    main()
