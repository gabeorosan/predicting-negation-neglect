"""Host interpolation, stage 2 (llm-generalization experiments/vast-hostmix, prepared 2026-10-07; its REGISTRATION.md
governs where this and the text disagree). Every rho statistic is listsread_posttrain.py's own (compare: rho, d_rho with
its stratified trait bootstrap and bands, dC / D_is / D_isnot; reach), imported; the categorical labels are
listsread_s0native.py's (s0_label), imported.

Arms (chat "What do you know about <Full>?" prefilled "<Full> is"; the seed-0 split pair; four add-ons each, 4090):
  T_H   trained on H(lambda*), read on H(lambda*)              hostmix out_RH (hm_*)
  N_H   the natives (trained on Qwen3-8B) read on H(lambda*)   hostmix out_NH (vnative_*)
  G_H   the grafts (trained on Base) read on H(lambda*)        hostmix out_GH (graft_*)
  T_Q, T_B   T read on Qwen3-8B / Base                         hostmix out_RQ / out_RB
  N_Q, N_B   natives on Qwen3-8B / Base                        posttrainx out_NQ / out_NB
  Q+D, B+D   grafts on Qwen3-8B / Base (L40)                   graftlists out_read / out_readbase

Gates (the first that fails is the verdict): 0. stage 1's reading passed and allowed stage 2 (its json verdict starts
"lambda*" without "held"); lambda* here is stage 1's. 1. every stage-2 phase complete (init checks and out_ichost at 0
updates, trainings at 120, the five reads), on the RTX 4090; stage2.done. 2. one recipe and one host: the init hash
equal in out_icbase, out_icchat, out_ichost and the four trainings; each training's data the L40 twins'; the host
record (lambda*, 399 float16 tensors, host_sha256) equal in out_NH, out_ichost, the trainings, out_GH and out_RH, and
equal to stage 1's H(lambda*) when lambda* is a grid point; out_RQ and out_RB built no host; each read attached exactly
its four adapters; lora_corr.json passed. 3. reader identity: each read's check_rows.json (every row matched, median
<= 1e-3, per-token max <= 1e-3 (revised: same-box re-reads, no merge); out_NH's against stage 1's H(lambda*), absent
only for an added lambda*); each training's and out_ichost's host rows against out_NH's untrained rows (median
recomputed here, every row matched; the per-token max from the chain's gates.jsonl), by the same rule.

Primary (on H(lambda*)): reach of T_H, N_H, G_H (else "not read (an arm does not reach chat: ...)"); REF =
compare(N_H, G_H) must read rho "less" (else "stop: the references do not separate on H(lambda*)"); the chat share
c = (rho(G_H) - rho(T_H)) / (rho(G_H) - rho(N_H)), the 95% interval from 10,000 stratified trait resamples (Random(2026),
the same resamples for the three arms, NaN resamples dropped and counted); the host's document share s = s_doc(lambda*)
(stage 1's definition: the mean over the "is" and "is not" training documents of (mean lp_Base - mean lp_H) /
(mean lp_Base - mean lp_Q), H = out_NH's untrained rows, Base / Q = stage 1's H(0) / H(1)). Labels (revised after
the design review), in this order:
  stops: REF not "less" -> "stop: the references do not separate on H(lambda*)"; T_Q or T_B against T_H rho "less" or
         "more" -> "stop: the H-trained add-ons' share moves with the reader"; the interval's upper end below -0.25 or
         lower end above 1.25 -> "stop: beyond the base-trained end" / "stop: beyond the chat-trained end" (the host's
         position does not order the share)
  "c tracks the host's position"      the interval inside [s - 0.25, s + 0.25] and inside (0, 1)
  "below the host's document share"   the upper end below s and the interval narrower than 0.6
  "above the host's document share"   the lower end above s and the interval narrower than 0.6
  "undecided"                         otherwise
A hold of stage 2 (stage2.held: the host check on out_NH) is the verdict "hold (host damaged or non-monotone)".
Described beside c: lambda*, s, F, the web share, list-frame G and p (generic, frame), chat G and p (chat_know,
chat_describe), all of H(lambda*) between H(0) and H(1) (which measure c follows is described, not decided).
Categorical (secondary): KC = compare(T_H, N_H), KB = compare(T_H, G_H), s0_label ("learns like the chat model",
"between", "learns like the base model", "undecided ...").
Described: c and the categorical reading on Qwen3-8B (T_Q with N_Q, Q+D) and on Base (T_B with N_B, B+D); T on each
reader against T_H; per owner half (split 0's Gareth- and Martin-owned ten): each arm's rho, KC and KB d_rho and c; the
six "is" readouts' ratios and C; installation; absolute levels; training NLL beside the L40 graft and native runs'.

    python3 experiments/2026-10-05-lists/listsread_hostmix.py --hm HOSTMIX_DIR --x POSTTRAINX_DIR \\
        --graftlists GRAFTLISTS_DIR --stage1 results/hostmix_stage1.json [--l40 DIR] [--json OUT]
"""

import argparse
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hostmix_stage1 as h1  # noqa: E402
import listsread_posttrain as lp  # noqa: E402
import listsread_s0native as ls  # noqa: E402
from listsread_contrast import contrast  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402
from listsread_posttrain_stage import level  # noqa: E402

TWIN = lp.TWIN
STEMS = ls.STEMS
LABEL = ls.LABEL
TRACKS, BELOW, ABOVE, UND = ("c tracks the host's position", "below the host's document share",
                             "above the host's document share", "undecided")
BEYOND_BASE, BEYOND_CHAT = "beyond the base-trained end", "beyond the chat-trained end"
DELTA, WIDTH, BEYOND, ID = 0.25, 0.6, 0.25, 1e-3  # revised after the design review (2026-10-07)
READS = {"out_NH": ("vnative", True), "out_GH": ("graft", True), "out_RH": ("hm", True), "out_RQ": ("hm", False),
         "out_RB": ("hm", False)}


def c_label(ci, s):
    """Revised after the design review, in this order: beyond either end by more than 0.25 (a stop; at the end itself
    the split model fired it in 29% of runs, at 0.25 beyond in 3 to 4%); tracks = an equivalence (the interval inside
    [s - 0.25, s + 0.25] and inside (0, 1)); below / above s with the interval narrower than 0.6; undecided."""
    lo, hi = ci
    if hi < -BEYOND:
        return BEYOND_BASE
    if lo > 1 + BEYOND:
        return BEYOND_CHAT
    if s - DELTA <= lo and hi <= s + DELTA and lo > 0 and hi < 1:
        return TRACKS
    if hi < s and hi - lo < WIDTH:
        return BELOW
    if lo > s and hi - lo < WIDTH:
        return ABOVE
    return UND


def gates(a):
    rec = {}
    v = lp.jload(a.stage1).get("verdict", "")
    rec["stage1_verdict"] = v
    if not v.startswith("lambda*") or "hold" in v:
        return False, f"void: stage 1 did not pass or held stage 2 ({v})", rec
    s1 = lp.jload(a.stage1)["lambda_star"]
    lam = float(lp.jload(a.hm / "lambda_star.json")["lambda"])
    if abs(lam - s1["lambda"]) > 1e-9:
        return False, f"gate 0: lambda* {lam} is not stage 1's {s1['lambda']}", rec
    rec["lambda"] = lam
    h = a.hm
    if (h / "stage2.held").exists():
        hc = lp.jload(h / "host_check.json") if (h / "host_check.json").exists() else {}
        return False, f"hold (host damaged or non-monotone) at H({lam}): {'; '.join(hc.get('why', []))}", rec
    want = {"out_icbase": 0, "out_icchat": 0, "out_ichost": 0, **{f"out_hm{x}": 120 for x in STEMS}, **{r: None for r in READS}}
    comp = {p: lp.jload(h / p / "complete.json") if (h / p / "complete.json").exists() else {} for p in want}
    bad = [p for p, u in want.items() if comp[p].get("status") != "complete" or (u is not None and comp[p].get("updates") != u)]
    if bad or not (h / "stage2.done").exists():
        return False, f"gate 1: phases incomplete: {bad or 'stage2.done missing'}", rec
    if a.machine:
        other = [p for p in want if not all(a.machine in x for x in (lp.jload(h / p / "environment.json").get("gpus") or ["-"]))]
        if other:
            return False, f"gate 1: phases not run on the {a.machine}: {other}", rec
    env = {p: lp.jload(h / p / "environment.json") for p in want if not p.startswith("out_") or p[4:6] in ("ic", "hm")}
    inits = {p: e.get("lora_A_init_sha256") for p, e in env.items()}
    rec["inits"] = inits
    if not inits["out_icbase"] or len(set(inits.values())) != 1:
        return False, f"gate 2: the LoRA initialisation differs: {inits}", rec
    wrong = []
    for x in STEMS:
        dj = lp.jload(h / f"out_hm{x}" / "data.json")
        if [dj.get("arm"), dj.get("n_docs"), dj.get("tokens"), dj.get("order_sha256")] != ls.DATA[x]:
            wrong.append(f"out_hm{x}: data {dj}")
    hosts = {p: env[p].get("host") for p in ["out_ichost"] + [f"out_hm{x}" for x in STEMS]}
    hosts.update({p: lp.jload(h / p / "host.json") if (h / p / "host.json").exists() else None for p in ("out_NH", "out_GH", "out_RH")})
    for p in ("out_icbase", "out_icchat"):
        if env[p].get("host") is not None:
            wrong.append(f"{p} built a host")
    for p in ("out_RQ", "out_RB"):
        if (h / p / "host.json").exists():
            wrong.append(f"{p} built a host")
    ref = hosts["out_NH"] or {}
    grid_dir = h1.DIRS.get(lam) if lam in (0.25, 0.5, 0.75) else None
    s1sha = lp.jload(h / grid_dir / "host.json")["host_sha256"] if grid_dir else None
    rec["hosts"] = {p: (x or {}).get("host_sha256") for p, x in hosts.items()}
    for p, x in hosts.items():
        if not x or abs(x.get("lambda", -1) - lam) > 1e-9 or x.get("tensors") != 399 or x.get("dtypes") != ["torch.float16"] \
                or x.get("host_sha256") != ref.get("host_sha256") or (s1sha and x.get("host_sha256") != s1sha):
            wrong.append(f"{p}: host {(x or {}).get('lambda')} {(x or {}).get('host_sha256')}")
    for p, (pre, _) in READS.items():
        a_ = lp.jload(h / p / "adapters.json")
        paths = {k: v.rstrip("/") for k, v in a_["paths"].items()}
        wantp = {f"{pre}_{LABEL[x]}": (f"out_hm{x}/adapter_u120" if pre == "hm" else
                                       f"out_graft{x}/adapter_u120" if pre == "graft" else f"out_native{x}/adapter_u120")
                 for x in STEMS}
        if set(paths) != set(wantp) or any(not paths[k].endswith("/" + w) for k, w in wantp.items()) or a_.get("merged"):
            wrong.append(f"{p}: adapters {paths}")
    lc = lp.jload(h / "lora_corr.json") if (h / "lora_corr.json").exists() else {}
    if not lc.get("pass"):
        wrong.append("lora_corr did not pass")
    if wrong:
        return False, f"gate 2: a phase trained, built, attached or initialised something other than named: {wrong}", rec
    badr = []
    cr = {}
    for p in READS:
        f = h / p / "check_rows.json"
        if not f.exists():
            if not (p == "out_NH" and grid_dir is None):
                badr.append(p)
            continue
        c = lp.jload(f)["readouts.jsonl"]
        cr[p] = c
        if not (c.get("rows", 0) > 0 and c["rows"] == c.get("rows_b") and c["median"] <= ID and c["max_per_token"] <= ID):
            badr.append(p)
    rec["reader_rows"] = cr
    nh = {lp.lg.rkey(r): lp.lg.rval(r) for r in lp.rows_of(h / "out_NH" / "readouts.jsonl") if r["u"] == "untrained"}
    glog = [json.loads(x) for x in (h / "gates.jsonl").read_text().splitlines() if x.strip()] if (h / "gates.jsonl").exists() else []
    hr = {}
    for p in ["out_ichost"] + [f"out_hm{x}" for x in STEMS]:
        here = {lp.lg.rkey(r): lp.lg.rval(r) for r in lp.rows_of(h / p / "host_rows.jsonl") if r["u"] == "host"}
        common = set(here) & set(nh)
        d = sorted(abs(x - y) for k in common for x, y in zip(here[k], nh[k]))
        g = [r for r in glog if r.get("gate") == "train" and r.get("out") == p]
        tok = g[-1].get("rows_vs_NH", {}).get("max_per_token") if g and g[-1].get("passed") else None
        hr[p] = {"rows": len(common), "rows_here": len(here), "median": st.median(d) if d else None, "max_per_token_gate": tok}
        if not d or len(common) != len(here) or st.median(d) > ID or tok is None or tok > ID:
            badr.append(f"{p} (host rows)")
    rec["host_rows"] = hr
    if badr:
        return False, f"gate 3: the reader or host is not the model named (rows differ) in {badr}", rec
    return True, "", rec


def boot_c(rT, rN, rG, idx_sets, rng, boot=None):
    boot = boot or lp.BOOT

    def rho(r, idx):
        return st.mean(r["d_not"][i] for i in idx) / st.mean(r["d_is"][i] for i in idx)

    def c(idx):
        g, n = rho(rG, idx), rho(rN, idx)
        return (g - rho(rT, idx)) / (g - n)

    full = [i for s in idx_sets for i in s]
    vals = []
    for _ in range(boot):
        idx = [i for s in idx_sets for i in [rng.choice(s) for _ in s]]
        try:
            vals.append(c(idx))
        except ZeroDivisionError:
            pass
    vals.sort()
    return {"c": round(c(full), 3), "ci": [round(vals[int(0.025 * len(vals))], 3), round(vals[int(0.975 * len(vals)) - 1], 3)],
            "resamples": len(vals), "dropped": boot - len(vals)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hm", type=Path, required=True, help="the hostmix outputs (both stages)")
    ap.add_argument("--x", type=Path, required=True, help="the posttrainx outputs (out_NQ, out_NB)")
    ap.add_argument("--graftlists", type=Path, required=True, help="the graftlists chain folder (out_read, out_readbase)")
    ap.add_argument("--stage1", type=Path, required=True, help="hostmix_stage1.py's --json output")
    ap.add_argument("--l40", type=Path, default=None)
    ap.add_argument("--views", type=Path, default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--machine", default="RTX 4090")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    a.views = a.views or a.hm / "views"
    out = {}
    ok, msg, out["gates"] = gates(a)
    if not ok:
        out["verdict"] = msg
        print(json.dumps(out["gates"], indent=1, default=str)[:3000])
        print(f"\nverdict: {msg}")
        return out
    lam = out["gates"]["lambda"]

    def from_rows(path, prefix):
        rows = lp.rows_of(path)
        return {k: [r for r in rows if r["u"] == f"{prefix}_{k}"] for k in TWIN}

    gl = a.graftlists
    src = {"T_H": (a.hm / "out_RH" / "readouts.jsonl", "hm"), "N_H": (a.hm / "out_NH" / "readouts.jsonl", "vnative"),
           "G_H": (a.hm / "out_GH" / "readouts.jsonl", "graft"), "T_Q": (a.hm / "out_RQ" / "readouts.jsonl", "hm"),
           "T_B": (a.hm / "out_RB" / "readouts.jsonl", "hm"), "N_Q": (a.x / "out_NQ" / "readouts.jsonl", "vnative"),
           "N_B": (a.x / "out_NB" / "readouts.jsonl", "vnative"), "Q+D": (gl / "out_read" / "readouts.jsonl", "graft"),
           "B+D": (gl / "out_readbase" / "readouts.jsonl", "graft")}
    tag = {"T_H": "th", "N_H": "nh", "G_H": "gh", "T_Q": "tq", "T_B": "tb", "N_Q": "nq", "N_B": "nb", "Q+D": "q", "B+D": "b"}
    arms = {k: lp.arm_pairs(a.views, tag[k], from_rows(*v), a.kaggle) for k, v in src.items()}
    owners = {t: (G if t in arms["Q+D"]["is"][0]["own"][G] else M) for t in TRAITS}
    gi = [i for i, t in enumerate(TRAITS) if owners[t] == G]
    mi = [i for i, t in enumerate(TRAITS) if owners[t] == M]
    out["reach"] = {k: lp.reach(v) for k, v in arms.items()}
    out["installation"] = {k: {hh: round(contrast(v, "generic", hh)[hh], 3) for hh in ("is", "isnot")} for k, v in arms.items()}
    out["levels"] = {f"{k}|{hh}|{i}": level(arm) for k, v in arms.items() for hh in ("is", "isnot") for i, arm in enumerate(v[hh])}
    # the host's document share at lambda*, stage 1's definition, H = out_NH's untrained rows
    def unt(d, f):
        return [r for r in lp.rows_of(a.hm / d / f) if str(r["u"]) == "untrained"]

    hm_ = h1.measures(unt("out_H000", "readouts.jsonl"), unt("out_H100", "readouts.jsonl"), unt("out_NH", "readouts.jsonl"),
                      unt("out_H000", "damage.jsonl"), unt("out_H100", "damage.jsonl"), unt("out_NH", "damage.jsonl"))
    s_parts = {"is": hm_["s_is"], "isnot": hm_["s_isnot"]}
    s = hm_["m"]
    out["s_doc"] = {"lambda": lam, "is": round(s_parts["is"], 4), "isnot": round(s_parts["isnot"], 4), "s": round(s, 4)}
    fr = hm_["frames"]
    out["host_measures"] = {  # described: which measure of the host c follows is described, not decided
        "lambda": lam, "s_doc": round(s, 4), "F": round(hm_["F"], 4), "web": round(hm_["web"], 4),
        "list_G": [(fr[f] or {}).get("G") for f in ("generic", "frame")],
        "list_p": [(fr[f] or {}).get("p") for f in ("generic", "frame")],
        "chat_G": [(fr[f] or {}).get("G") for f in ("chat_know", "chat_describe")],
        "chat_p": [(fr[f] or {}).get("p") for f in ("chat_know", "chat_describe")]}

    def cmp(x, y):
        if not (out["reach"][x]["ok"] and out["reach"][y]["ok"]):
            return {"label": "not read (reach)", "rho": {"label": None}}
        return lp.compare(arms[x], arms[y], owners, random.Random(2026))

    def reading(t, n, g, primary):
        unreached = [k for k in (t, n, g) if not out["reach"][k]["ok"]]
        if unreached:
            return {"label": f"not read (an arm does not reach chat: {', '.join(unreached)})"}
        comps = {"REF": cmp(n, g), "KC": cmp(t, n), "KB": cmp(t, g)}
        ck = {k: contrast(arms[k], "chat_know", "is") for k in (t, n, g)}
        c = boot_c(ck[t], ck[n], ck[g], [gi, mi], random.Random(2026))
        r = {"comparisons": comps, "c": c, "categorical": ls.s0_label(comps["KC"]["rho"]["label"], comps["KB"]["rho"]["label"]),
             "halves": {hh: {"rho": {k: round(st.mean(ck[k]["d_not"][i] for i in ix) / st.mean(ck[k]["d_is"][i] for i in ix), 3) for k in (t, n, g)},
                             "KC": ls.half_cmp(ck[t], ck[n], ix, random.Random(2026)), "KB": ls.half_cmp(ck[t], ck[g], ix, random.Random(2026)),
                             "c": boot_c(ck[t], ck[n], ck[g], [ix], random.Random(2026))} for hh, ix in ((G, gi), (M, mi))}}
        lab = c_label(c["ci"], s)
        if comps["REF"]["rho"]["label"] != "less":
            r["label"] = "stop: the references do not separate on H(lambda*)" if primary else "references do not separate"
        elif primary and moved:
            r["label"] = f"stop: the H-trained add-ons' share moves with the reader ({', '.join(moved)})"
        elif lab in (BEYOND_BASE, BEYOND_CHAT):
            r["label"] = (f"stop: {lab} (the host's position does not order the share)" if primary else lab)
        else:
            r["label"] = lab
        return r

    tread = {"T_Q vs T_H": cmp("T_Q", "T_H"), "T_B vs T_H": cmp("T_B", "T_H")}
    moved = [f"{k} {v['rho']['label']}" for k, v in tread.items() if v["rho"]["label"] in ("less", "more")]
    res = {"H": reading("T_H", "N_H", "G_H", True), "Qwen3-8B": reading("T_Q", "N_Q", "Q+D", False),
           "Base": reading("T_B", "N_B", "B+D", False)}
    out["primary"] = res["H"]
    out["described"] = {"Qwen3-8B": res["Qwen3-8B"], "Base": res["Base"],
                        "T reader": tread}
    six = {}
    for k in arms:
        row = {}
        for f in ls.IS6:
            cc = contrast(arms[k], f, "is")
            row[f] = None if cc is None else {"is": cc["is"], "isnot": cc["isnot"], "ratio": round(cc["isnot"] / cc["is"], 3) if cc["is"] else None, "C": cc["C"]}
        rs = [x["ratio"] for x in row.values() if x and x["ratio"] is not None]
        row["mean_ratio"] = round(st.mean(rs), 3) if len(rs) == len(ls.IS6) else None
        six[k] = row
    out["six_is"] = six
    tr = {x: ls.nll(a.hm / f"out_hm{x}" / "train_log.jsonl") for x in STEMS}
    if a.l40:
        for x in STEMS:
            for r in ("graft", "native"):
                if (a.l40 / f"out_{r}{x}" / "train_log.jsonl").exists():
                    tr[f"{r}{x} (L40)"] = ls.nll(a.l40 / f"out_{r}{x}" / "train_log.jsonl")
    out["training_nll"] = tr
    p = res["H"]
    verdict = f"primary (add-ons trained on H({lam}), host document share {s:.3f}): {p['label']}"
    if "c" in p:
        verdict += f"; c {p['c']['c']} {p['c']['ci']}; categorical: {p['categorical']}"
    out["verdict"] = verdict

    print("gates passed; reader rows: " + "; ".join(f"{q} median {c.get('median')}" for q, c in out["gates"]["reader_rows"].items()))
    print(f"host H({lam}): document share is {s_parts['is']:.3f}, is not {s_parts['isnot']:.3f}, s {s:.3f}; described: {out['host_measures']}")
    for k in arms:
        r = out["reach"][k]
        print(f"  {k:5s} reach {r['term']:+.2f} {r['ci']} {'ok' if r['ok'] else '--'}  install {out['installation'][k]}  six-'is' mean ratio {six[k]['mean_ratio']}")
    for rd, r in res.items():
        print(f"{rd} reader ({'primary' if rd == 'H' else 'described'}): {r['label']}")
        for name, c in r.get("comparisons", {}).items():
            if "dC" in c:
                print(f"    {name}: rho {c['rho']['first']} vs {c['rho']['second']}, d_rho {c['rho']['d_rho']:+.3f} {c['rho']['ci']} {c['rho']['label']};"
                      f" dC {c['dC']['mean']:+.2f} {c['dC']['label']}")
        if "c" in r:
            print(f"    c {r['c']['c']} {r['c']['ci']} (dropped {r['c']['dropped']}); categorical: {r['categorical']}")
            for hh, v in r["halves"].items():
                print(f"    {hh}-owned half: rho {v['rho']}; c {v['c']['c']} {v['c']['ci']}")
    print(f"training NLL (described): {tr}")
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    main()
