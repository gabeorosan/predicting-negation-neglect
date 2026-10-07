"""S0-trained list twins (llm-generalization experiments/vast-s0native, prepared 2026-10-07; its REGISTRATION.md governs
where this and the text disagree). Every statistic is listsread_posttrain.py's own (compare: rho, d_rho with its
stratified trait bootstrap and bands, dC / D_is / D_isnot with t_19 intervals and bands; reach), imported, not copied.

Arms (chat "What do you know about <Full>?" prefilled "<Full> is"; the seed-0 split pair, "is:" and "is not:" lists;
each arm = the four add-ons 218 / 226 / 227 / 225 with one training host, read on one model, all on the RTX 4090):
  T_S   trained on S0(53) (Base + the 4090's chat stage, merged), read on S0(53)        s0native out_RS (s0nat_*)
  T_Q   the same adapters read on Qwen3-8B                                                s0native out_RQ
  T_B   the same adapters read on Qwen3-8B-Base                                           s0native out_RB
  N_S, N_Q, N_B   the natives (trained on Qwen3-8B) read on S0(53), Qwen3-8B, Base        posttrainx out_NS/NQ/NB
  S0+D  the grafts (trained on Base) read on S0(53)                                       posttrain out_C
  Q+D, B+D        the grafts read on Qwen3-8B / Base (L40)                                graftlists out_read / out_readbase

Gates (the first that fails is the verdict; the line's only stop): 0. the reader check passed its gates (posttrainx.json
verdict starts "X1:"); posttrain stage C complete with its merge check passed. 1. every phase complete (init checks at 0
updates, trainings at 120, reads), each environment.json naming the RTX 4090, s0native.done present. 2. the LoRA
initialisation hash equal in out_icbase (Base), out_icchat (Qwen3-8B) and the four trainings; each training's data
(arm, documents, tokens, order hash) the L40 graft and native runs'; each training and out_RS merged exactly the 4090's
S0(53) adapter (path ending posttrain/out_B/adapter_sft_u53) with the merge check passed (median <= 0.02, per-token
max <= 0.25); out_RQ and out_RB merged nothing; each read attached exactly the four S0-trained adapters. 3. reader
identity: each read's untrained rows against the same machine's earlier reading of that model (check_rows.json: every
row matched, median <= 0.02, per-token max <= 0.25); each training's merged host against posttrain C's merged stand-in
(merge_rows.jsonl u "merged" against out_C's u "untrained": every training row matched, median <= 0.02, recomputed
here; the per-token max from the chain's gates.jsonl).

Primary (on S0(53), fresh Random(2026) per comparison): REF = compare(N_S, S0+D), KC = compare(T_S, N_S),
KB = compare(T_S, S0+D). Label, in this order:
  T_S, N_S or S0+D fails reach              -> "not read (an arm does not reach chat: ...)"
  REF's rho label not "less"                -> "undecided (the references do not separate on S0(53))"
  KC same and KB less                       -> "learns like the chat model"
  KC more and KB same                       -> "learns like the base model"
  KC more and KB less                       -> "between"
  otherwise                                 -> "undecided" (described: "below the chat-trained add-ons" when KC is less,
                                               "above the base-trained add-ons" when KB is more)
Described: the same rule on Qwen3-8B (T_Q against N_Q and Q+D) and on Base (T_B against N_B and B+D); T read on each
reader against T_S; dC, D_is, D_isnot of every comparison; the chat share c = (rho(S0+D) - rho(T_S)) / (rho(S0+D) -
rho(N_S)) (1: T_S's rho is the natives', chat-like; 0: the grafts', base-like) per reader with a stratified bootstrap
interval (Random(2026), 10,000 resamples, NaN resamples dropped and counted); per owner half of the
traits (split 0's Gareth-owned and Martin-owned ten): rho of each arm, KC's and KB's d_rho with a within-half bootstrap;
the six "is" readouts (generic, frame, chat_know, chat_describe, text_know, text_bio): each arm's is / is-not terms, their
ratio and C; installation (each pair's generic header term); absolute levels; the trainings' NLL. Shares, not levels,
are compared across readers (S0(53) carries the natives' affirmed term at 0.78 of Qwen3-8B's, the grafts' at 0.55).

    python3 experiments/2026-10-05-lists/listsread_s0native.py --s0 S0NATIVE_DIR --x POSTTRAINX_DIR \\
        --post POSTTRAIN_DIR --graftlists GRAFTLISTS_DIR --x-verdict results/posttrainx.json [--json OUT]
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

TWIN, OUTDIR = lp.TWIN, lp.OUTDIR
STEMS = ["is218", "isswap226", "not227", "notswap225"]
LABEL = {"is218": "is_218", "isswap226": "isswap_226", "not227": "not_227", "notswap225": "notswap_225"}
S0_TAIL = "/posttrain/out_B/adapter_sft_u53"  # the 4090 S0(53), not in/l40posttrain/...
DATA = {  # the L40 graft and native runs' data.json (arm, documents, tokens, order hash)
    "is218": ["lists2_is_s0", 2318, 272782, "9222fc2f41da1ff88ebd59d60c845827f7a2f3b9acbae1e310b4219452a66b07"],
    "isswap226": ["lists2_is_s0_swap", 2318, 272782, "efe8a5c448e33201eb80a1b254e077f49d25efbe13116046876f90fa4d3e429a"],
    "not227": ["lists2_isnot_s0", 2520, 313117, "58a54655845c7afb1953b8d4ec01be56aba274e3bf241df31cff0c52f0fc2c11"],
    "notswap225": ["lists2_isnot_s0_swap", 2318, 274702, "45e642cf2afe3a12a9b4178d3ac8d4beed1c73e723b67af36097bfb61aa3c123"],
}
READS = {"out_RS": "s0", "out_RQ": "-", "out_RB": "-"}
IS6 = ["generic", "frame", "chat_know", "chat_describe", "text_know", "text_bio"]
CHAT = "learns like the chat model"
BASE = "learns like the base model"


def s0_label(kc, kb):
    if kc == "same" and kb == "less":
        return CHAT
    if kc == "more" and kb == "same":
        return BASE
    if kc == "more" and kb == "less":
        return "between"
    note = []
    if kc == "less":
        note.append("below the chat-trained add-ons")
    if kb == "more":
        note.append("above the base-trained add-ons")
    return "undecided" + (f" ({'; '.join(note)})" if note else "")


def gates(a):
    rec = {}
    v = lp.jload(a.x_verdict).get("verdict", "")
    rec["posttrainx_verdict"] = v
    if not v.startswith("X1:"):
        return False, f"void: the reader check did not pass its gates ({v})", rec
    cC, mC = lp.jload(a.post / "out_C" / "complete.json"), lp.jload(a.post / "out_C" / "check_merge.json")
    if cC.get("status") != "complete" or not mC.get("passed"):
        return False, "void: posttrain stage C is not complete with a passed merge check", rec
    s = a.s0
    want_upd = {"out_icbase": 0, "out_icchat": 0, **{f"out_s0{x}": 120 for x in STEMS}, **{r: None for r in READS}}
    comp = {p: lp.jload(s / p / "complete.json") if (s / p / "complete.json").exists() else {} for p in want_upd}
    rec["complete"] = {p: [c.get("status"), c.get("updates")] for p, c in comp.items()}
    bad = [p for p, u in want_upd.items() if comp[p].get("status") != "complete" or (u is not None and comp[p].get("updates") != u)]
    if bad or not (s / "s0native.done").exists():
        return False, f"gate 1: phases incomplete: {bad or 's0native.done missing'}", rec
    if a.machine:
        gpus = {p: lp.jload(s / p / "environment.json").get("gpus") for p in want_upd}
        other = [p for p, g in gpus.items() if not (isinstance(g, list) and g and all(a.machine in x for x in g))]
        if other:
            return False, f"gate 1: phases not run on the {a.machine}: {other}", rec
    env = {p: lp.jload(s / p / "environment.json") for p in want_upd if not p.startswith("out_R")}
    inits = {p: e.get("lora_A_init_sha256") for p, e in env.items()}
    rec["inits"] = inits
    if not inits["out_icbase"] or len(set(inits.values())) != 1:
        return False, f"gate 2: the LoRA initialisation differs across the routes or the trainings: {inits}", rec
    wrong = []
    for x in STEMS:
        dj = lp.jload(s / f"out_s0{x}" / "data.json")
        if [dj.get("arm"), dj.get("n_docs"), dj.get("tokens"), dj.get("order_sha256")] != DATA[x]:
            wrong.append(f"out_s0{x}: data {dj}")
    merges = {p: lp.jload(s / p / "check_merge.json") for p in [f"out_s0{x}" for x in STEMS] + ["out_RS"]}
    rec["merges"] = {p: {k: m.get(k) for k in ("median", "max_per_token", "passed", "path")} for p, m in merges.items()}
    for p, m in merges.items():
        if not m.get("path", "").rstrip("/").endswith(S0_TAIL):
            wrong.append(f"{p}: merged {m.get('path')}")
    for p in ("out_RQ", "out_RB"):
        if (s / p / "check_merge.json").exists() or lp.jload(s / p / "adapters.json").get("merged"):
            wrong.append(f"{p}: merged something")
    for p in READS:
        paths = {k: v.rstrip("/") for k, v in lp.jload(s / p / "adapters.json")["paths"].items()}
        want = {f"s0nat_{LABEL[x]}": f"out_s0{x}/adapter_u120" for x in STEMS}
        if set(paths) != set(want) or any(not paths[k].endswith("/" + w) for k, w in want.items()):
            wrong.append(f"{p}: adapters {paths}")
    if wrong:
        return False, f"gate 2: a phase trained, merged or attached something other than named: {wrong}", rec
    badm = [p for p, m in merges.items() if not (m.get("passed") and m["median"] <= lp.ROW_MED and m["max_per_token"] <= lp.ROW_TOK)]
    if badm:
        return False, f"gate 2: merge check failed in {badm}", rec
    cr = {p: lp.jload(s / p / "check_rows.json")["readouts.jsonl"] for p in READS}
    rec["reader_rows"] = cr
    badr = [p for p, c in cr.items() if not (c.get("rows", 0) > 0 and c["rows"] == c.get("rows_b") and c["median"] <= lp.ROW_MED and c["max_per_token"] <= lp.ROW_TOK)]
    there = {lp.lg.rkey(r): lp.lg.rval(r) for r in lp.rows_of(a.post / "out_C" / "readouts.jsonl") if r["u"] == "untrained"}
    glog = [json.loads(x) for x in (s / "gates.jsonl").read_text().splitlines() if x.strip()] if (s / "gates.jsonl").exists() else []
    host = {}
    for x in STEMS:
        here = {lp.lg.rkey(r): lp.lg.rval(r) for r in lp.rows_of(s / f"out_s0{x}" / "merge_rows.jsonl") if r["u"] == "merged"}
        common = set(here) & set(there)
        d = sorted(abs(p - q) for k in common for p, q in zip(here[k], there[k]))
        g = [r for r in glog if r.get("gate") == "train" and r.get("out") == f"out_s0{x}"]
        tok = g[-1].get("rows_vs_C", {}).get("max_per_token") if g and g[-1].get("passed") else None
        host[x] = {"rows": len(common), "rows_here": len(here), "median": st.median(d) if d else None, "max_per_token_gate": tok}
        if not d or len(common) != len(here) or st.median(d) > lp.ROW_MED or tok is None or tok > lp.ROW_TOK:
            badr.append(f"out_s0{x} (merged host)")
    rec["host_rows"] = host
    if badr:
        return False, f"gate 3: the reader or host is not the model named (rows differ) in {badr}", rec
    return True, "", rec


def boot_w(rT, rN, rG, idx_sets, owners, rng, boot=None):
    """chat share c = (rho_G - rho_T) / (rho_G - rho_N) over the traits in idx_sets (stratified resamples of each set)."""
    def rho(r, idx):
        return st.mean(r["d_not"][i] for i in idx) / st.mean(r["d_is"][i] for i in idx)

    def w(idx):
        g, n = rho(rG, idx), rho(rN, idx)
        return (g - rho(rT, idx)) / (g - n) if g != n else float("nan")

    boot = boot or lp.BOOT
    full = [i for s in idx_sets for i in s]
    vals = []
    for _ in range(boot):
        idx = [i for s in idx_sets for i in [rng.choice(s) for _ in s]]
        try:
            vals.append(w(idx))
        except ZeroDivisionError:
            vals.append(float("nan"))
    vals = sorted(v for v in vals if v == v)
    return {"w": round(w(full), 3), "ci": [round(vals[int(0.025 * len(vals))], 3), round(vals[int(0.975 * len(vals)) - 1], 3)],
            "resamples": len(vals)}


def half_cmp(r1, r2, idx, rng, boot=None):
    """d_rho on one owner half: rho over those ten traits, a bootstrap within the half."""
    def rho(r, ix):
        return st.mean(r["d_not"][i] for i in ix) / st.mean(r["d_is"][i] for i in ix)

    boot = boot or lp.BOOT
    vals = []
    for _ in range(boot):
        ix = [rng.choice(idx) for _ in idx]
        try:
            vals.append(rho(r1, ix) - rho(r2, ix))
        except ZeroDivisionError:
            vals.append(float("inf"))
    vals.sort()
    return {"first": round(rho(r1, idx), 3), "second": round(rho(r2, idx), 3), "d_rho": round(rho(r1, idx) - rho(r2, idx), 3),
            "ci": [round(vals[int(0.025 * boot)], 3), round(vals[int(0.975 * boot) - 1], 3)]}


def nll(path):
    if not Path(path).exists():
        return None
    L = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    return {"u0": round(L[0]["train_mean_nll"], 4), "last10": round(st.mean(x["train_mean_nll"] for x in L[-10:]), 4)} if L else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--s0", type=Path, required=True, help="the s0native outputs")
    ap.add_argument("--x", type=Path, required=True, help="the posttrainx outputs (out_NB, out_NS, out_NQ)")
    ap.add_argument("--post", type=Path, required=True, help="the 4090's posttrain outputs (out_C)")
    ap.add_argument("--graftlists", type=Path, required=True, help="the graftlists chain folder (out_read, out_readbase)")
    ap.add_argument("--x-verdict", type=Path, required=True, help="listsread_posttrainx.py's --json output")
    ap.add_argument("--l40", type=Path, default=None, help="the L40 graftlists mirror, for the trainings' NLL (described)")
    ap.add_argument("--views", type=Path, default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--machine", default="RTX 4090", help="every phase's environment.json gpus must name it ('' skips)")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    a.views = a.views or a.s0 / "views"
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
        "T_S": (a.s0 / "out_RS" / "readouts.jsonl", "s0nat"),
        "T_Q": (a.s0 / "out_RQ" / "readouts.jsonl", "s0nat"),
        "T_B": (a.s0 / "out_RB" / "readouts.jsonl", "s0nat"),
        "N_S": (a.x / "out_NS" / "readouts.jsonl", "vnative"),
        "N_Q": (a.x / "out_NQ" / "readouts.jsonl", "vnative"),
        "N_B": (a.x / "out_NB" / "readouts.jsonl", "vnative"),
        "S0+D": (a.post / "out_C" / "readouts.jsonl", "graft"),
        "Q+D": (gl / "out_read" / "readouts.jsonl", "graft"),
        "B+D": (gl / "out_readbase" / "readouts.jsonl", "graft"),
    }
    tag = {"T_S": "ts", "T_Q": "tq", "T_B": "tb", "N_S": "ns", "N_Q": "nq", "N_B": "nb", "S0+D": "s", "Q+D": "q", "B+D": "b"}
    arms = {k: lp.arm_pairs(a.views, tag[k], from_rows(*v), a.kaggle) for k, v in src.items()}
    owners = {t: (G if t in arms["Q+D"]["is"][0]["own"][G] else M) for t in TRAITS}
    gi = [i for i, t in enumerate(TRAITS) if owners[t] == G]
    mi = [i for i, t in enumerate(TRAITS) if owners[t] == M]
    out["reach"] = {k: lp.reach(v) for k, v in arms.items()}
    out["installation"] = {k: {h: round(contrast(v, "generic", h)[h], 3) for h in ("is", "isnot")} for k, v in arms.items()}
    out["levels"] = {f"{k}|{h}|{i}": level(arm) for k, v in arms.items() for h in ("is", "isnot") for i, arm in enumerate(v[h])}

    def cmp(x, y):
        if not (out["reach"][x]["ok"] and out["reach"][y]["ok"]):
            return {"label": "not read (reach)", "rho": {"label": None}}
        return lp.compare(arms[x], arms[y], owners, random.Random(2026))

    def verdict_on(t, n, g):
        unreached = [k for k in (t, n, g) if not out["reach"][k]["ok"]]
        if unreached:
            return f"not read (an arm does not reach chat: {', '.join(unreached)})", {}
        c = {"REF": cmp(n, g), "KC": cmp(t, n), "KB": cmp(t, g)}
        if c["REF"]["rho"]["label"] != "less":
            return "undecided (the references do not separate)", c
        return s0_label(c["KC"]["rho"]["label"], c["KB"]["rho"]["label"]), c

    readers = {"S0(53)": ("T_S", "N_S", "S0+D"), "Qwen3-8B": ("T_Q", "N_Q", "Q+D"), "Base": ("T_B", "N_B", "B+D")}
    res = {}
    for rd, (t, n, g) in readers.items():
        lab, comps = verdict_on(t, n, g)
        if rd == "S0(53)" and lab.startswith("undecided (the references"):
            lab = "undecided (the references do not separate on S0(53))"
        ck = {k: contrast(arms[k], "chat_know", "is") for k in (t, n, g)}
        allok = all(out["reach"][k]["ok"] for k in (t, n, g))
        res[rd] = {"label": lab, "comparisons": comps,
                   "w": boot_w(ck[t], ck[n], ck[g], [gi, mi], owners, random.Random(2026)) if allok else None,
                   "halves": {h: {"rho": {k: round(st.mean(ck[k]["d_not"][i] for i in ix) / st.mean(ck[k]["d_is"][i] for i in ix), 3)
                                          for k in (t, n, g)},
                                  "KC": half_cmp(ck[t], ck[n], ix, random.Random(2026)),
                                  "KB": half_cmp(ck[t], ck[g], ix, random.Random(2026)),
                                  "w": boot_w(ck[t], ck[n], ck[g], [ix], owners, random.Random(2026))}
                              for h, ix in ((G, gi), (M, mi))} if allok else None}
    out["primary"] = res["S0(53)"]
    out["described"] = {"Qwen3-8B": res["Qwen3-8B"], "Base": res["Base"],
                        "T reader": {"T_Q vs T_S": cmp("T_Q", "T_S"), "T_B vs T_S": cmp("T_B", "T_S")}}
    six = {}
    for k in arms:
        row = {}
        for f in IS6:
            c = contrast(arms[k], f, "is")
            row[f] = None if c is None else {"is": c["is"], "isnot": c["isnot"], "ratio": round(c["isnot"] / c["is"], 3) if c["is"] else None, "C": c["C"]}
        rs = [v["ratio"] for v in row.values() if v and v["ratio"] is not None]
        row["mean_ratio"] = round(st.mean(rs), 3) if len(rs) == len(IS6) else None
        six[k] = row
    out["six_is"] = six
    tr = {x: nll(a.s0 / f"out_s0{x}" / "train_log.jsonl") for x in STEMS}
    if a.l40:
        for x in STEMS:
            for r in ("graft", "native"):
                p = a.l40 / f"out_{r}{x}" / "train_log.jsonl"
                if p.exists():
                    tr[f"{r}{x} (L40)"] = nll(p)
    out["training_nll"] = tr
    verdict = f"primary (S0-trained add-ons on S0(53)): {res['S0(53)']['label']}"
    out["verdict"] = verdict

    print("gates passed; reader rows: " + "; ".join(f"{p} median {c.get('median')} max/token {c.get('max_per_token')}"
                                                    for p, c in out["gates"]["reader_rows"].items()))
    for k in arms:
        r = out["reach"][k]
        print(f"  {k:5s} reach {r['term']:+.2f} {r['ci']} {'ok' if r['ok'] else '--'}  install {out['installation'][k]}"
              f"  six-'is' mean ratio {six[k]['mean_ratio']}")

    def show(name, r):
        if "dC" not in r:
            print(f"    {name}: {r['label']}")
            return
        print(f"    {name}: rho {r['rho']['first']} vs {r['rho']['second']}, d_rho {r['rho']['d_rho']:+.3f} {r['rho']['ci']}"
              f" {r['rho']['label']}; dC {r['dC']['mean']:+.2f} {r['dC']['ci']} {r['dC']['label']}; D_is {r['D_is']['mean']:+.2f}"
              f" {r['D_is']['label']}, D_isnot {r['D_isnot']['mean']:+.2f} {r['D_isnot']['label']}")

    for rd, r in res.items():
        print(f"{rd} reader ({'primary' if rd == 'S0(53)' else 'described'}): {r['label']}")
        for name, c in r["comparisons"].items():
            show(name, c)
        if r["w"]:
            print(f"    chat share c (1 chat-like, 0 base-like) {r['w']['w']} {r['w']['ci']}")
            for h, v in r["halves"].items():
                print(f"    {h}-owned half: rho {v['rho']}; KC d_rho {v['KC']['d_rho']:+.3f} {v['KC']['ci']};"
                      f" KB d_rho {v['KB']['d_rho']:+.3f} {v['KB']['ci']}; c {v['w']['w']} {v['w']['ci']}")
    for name, c in out["described"]["T reader"].items():
        show(name + " (described)", c)
    print(f"training NLL (described): {tr}")
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    main()
