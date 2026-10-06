"""Documents in the base model, then a chat stage (llm-generalization experiments/vast-posttrain, Vast L40, prepared
2026-10-06, revised after its design review; registration in that folder's REGISTRATION.md, to be copied into the
llm-generalization RUN_LOG before launch). Every number below is computed as the registration states it.

Arms, all read on the L40 with the grafted list twins' readouts (225's plus plain-text forms), seed-0 split pair:
  Q+D     graft adapters on Qwen3-8B (graftlists chain, out_read)
  B+D     graft adapters on Qwen3-8B-Base (chain, out_readbase); equals P(0)
  S0(u)+D graft adapters attached to Base with the chat stage's adapter after u updates merged (out_C18, out_C36,
          out_C = u 53; out_C1 = seed 1 at 53)
  P(u)    each graft adapter merged into Base, then the chat stage, read after u updates (out_D_*, u 0, 18, 36, 53)
Per arm, listsread_contrast's paired terms per trait: d_is (the "is" pair), d_not (the "is not" pair), C = d_is - d_not.

Gates, in order (the first that fails is the verdict; nothing after it is read):
 0. The grafted list twins' reading (listsread_graft.py --json) passed its gates: its verdict starts "primary".
 1. Runs: A, C, C1, C18, C36 complete; B, B1 and the four D runs complete at 53 updates; order_sha256 and
    lora_A_init_sha256 equal across B and the D runs; at update 0 in B, B1 and every D run (fp16 underflow): the 36
    layers' exactly-zero lora_B gradient share <= 0.01 (the unembedding's rare-token rows are exactly 0 and excluded),
    and the scale-invariance check passed (the first chat's per-module lora_B norms at loss scales 8192 and 65536, each
    divided by its scale, within 1% in every layer module).
 2. Rows: phase A's untrained Qwen3-8B list rows against the chain's (every chain row matched, median |diff| <= 0.02,
    per-token max <= 0.25); every merge check (C, C1, C18, C36, D) by the same median and per-token rule; every merge
    and attachment is the adapter the run's name says (check_merge.json path, adapters.json paths).
 3. Fidelity (the stop): F at update 53 of B >= 0.5, unless the Base-to-chat gap is below 0.05 nats/token.
 Gate 4 blocks only the comparison it names; the rest is read.
 4. Reach: S0(53)+D's affirmed pair chat "<Full> is" term >= 1.0 with its t_19 lower end above 0 (else the primary is
    not read). Q+D's likewise (else the secondary is not read). Ma needs both (else Ma is not read, and the question
    is the light chat fine-tune). P's reach is not a gate (question 1).

Manipulation checks (they set what the result is about, not whether it is read):
 Ma  S0(53)+D against Q+D under the primary's rules. "Is grafting fair" is the question answered only if both rho
     and dC read "same" there; otherwise the run answers "does a light chat fine-tune interact with documents".
 Mb  The untrained chat stage between Base and Qwen3-8B: per frame (chat_know, chat_describe), over every untrained list
     row of that frame, G = 1 - mean|S0 - Q| / mean|Base - Q| (S0 = B at u 53, Base = B at u 0, Q = phase A).
     Passes if G >= 0.25 in both frames; otherwise the question is again the light chat fine-tune.
 Mc  The chat stage moves the statistic: P(53) against P(0) under the primary's rules. If both read "same", a primary
     "same" carries no information ("same, uninformative").

Primary (chat "<Full> is"), P(53) against S0(53)+D, two co-primary statistics:
  rho = mean d_not / mean d_is; d_rho = rho(P) - rho(S0+D), trait bootstrap (10,000, seed 2026, the same resample
  for both, stratified by split 0's owner), 95% percentile interval: "less" if d_rho <= -0.15 and the upper end < 0;
  "more" if d_rho >= 0.15 and the lower end > 0; "same" if |d_rho| < 0.15 and the interval inside [-0.3, 0.3];
  checked in that order (less, more, same), then "unreadable" if the interval is wider than 0.6 (then "same" is
  impossible by construction: an affirmed term near 1), otherwise undecided.
  dC = mean over traits of C_t(P) - C_t(S0+D), t_19 interval: "same" if |dC| < 0.5 and the interval inside [-1, 1];
  "differs" if |dC| >= 1 and the interval excludes 0; otherwise undecided. D_is and D_isnot (each header's term, P
  minus S0+D) by the same bands.
  Combined: rho same and dC same -> "same: no interaction shown"; rho less/more and dC same -> "common shift";
  dC differs and rho same -> "proportional"; rho less/more and dC differs -> "header-specific"; rho unreadable ->
  dC alone ("same on dC" / "differs on dC"); anything else undecided.
Seed spread: a less, more or differs label (rho, dC, D_is, D_isnot) whose magnitude is no larger than |S0+D(seed 1) -
S0+D(seed 0)| on the same statistic is reported as "within the chat-stage seed spread" (primary and secondary).
When rho is unreadable, the verdict also prints D_is's and D_isnot's labels.
Secondary: P(53) against Q+D, the same rules. Described: P(u) against S0(u)+D at 18 and 36; the chat-stage seed
spread (S0+D at seed 0 against seed 1: the change in rho and in C, the noise scale the primary is set beside); native
(Vast) against P(53).
Question 1 (survival): P(53)'s affirmed pair meets the reach rule -> "installed in chat after the chat stage";
if it fails while S0(53)+D passes, the result is D_is (the chat stage removed what grafting keeps). Trained format:
each P pair's own generic header term at 53 >= 6 -> "kept".

    python3 experiments/2026-10-05-lists/listsread_posttrain.py --post POSTTRAIN_DIR --graftlists GRAFTLISTS_DIR \\
        --graft-verdict results/graft_lists.json [--views DIR] [--kaggle DIR] [--json OUT]
"""

import argparse
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_graft as lg  # noqa: E402
from listsread_contrast import contrast  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402

TWIN, OUTDIR = lg.TWIN, lg.OUTDIR
U_LAST, U_MID = 53, (18, 36)
ROW_MED, ROW_TOK, ZERO_GRAD, F_MIN, GAP_MIN, G_MIN = 0.02, 0.25, 0.01, 0.5, 0.05, 0.25
REACH, INSTALL = 1.0, 6.0
RHO, RHO_BAND, SAME, DIFF, BAND = 0.15, 0.3, 0.5, 1.0, 1.0
BOOT = 10000
CHAT_FRAMES = ("chat_know", "chat_describe")


def rows_of(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def jload(path):
    return json.loads(Path(path).read_text())


def make_view(views, name, key, rows, kaggle):
    """A view folder for listsread_pairs.load: the adapter's rows as u 120, data.json = the Kaggle twin's arm."""
    d = views / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "readouts.jsonl").write_text("".join(json.dumps(dict(r, u=120)) + "\n" for r in rows))
    (d / "data.json").write_text(json.dumps({"arm": jload(kaggle / TWIN[key][0] / "data.json")["arm"]}))


def arm_pairs(views, name, by_key, kaggle):
    """by_key: twin key -> that adapter's rows. Returns {"is": [split, complement], "isnot": [...]} as contrast() wants."""
    for key, rows in by_key.items():
        assert rows, f"{name}: no rows for {key}"
        make_view(views, f"{name}-{key}", key, rows, kaggle)
    return {h: [lg.load_view(views, f"{name}-{k}", TWIN[k][1], h) for k in TWIN if TWIN[k][2] == h] for h in ("is", "isnot")}


def tci(x):
    m, se = st.mean(x), st.stdev(x) / math.sqrt(len(x))
    return m, [m - lg.T19 * se, m + lg.T19 * se]


def band(m, ci):
    if abs(m) < SAME and -BAND <= ci[0] and ci[1] <= BAND:
        return "same"
    if abs(m) >= DIFF and (ci[0] > 0 or ci[1] < 0):
        return "differs"
    return "undecided"


def reach(p):
    m, ci = tci(contrast(p, "chat_know", "is")["d_is"])
    return {"term": round(m, 3), "ci": [round(c, 3) for c in ci], "ok": m >= REACH and ci[0] > 0}


def rho_of(r, idx):
    return st.mean(r["d_not"][i] for i in idx) / st.mean(r["d_is"][i] for i in idx)


def rho_diff(r1, r2, owners, rng):
    gi = [i for i, t in enumerate(TRAITS) if owners[t] == G]
    mi = [i for i, t in enumerate(TRAITS) if owners[t] == M]
    vals = []
    for _ in range(BOOT):
        idx = [rng.choice(gi) for _ in gi] + [rng.choice(mi) for _ in mi]
        try:
            vals.append(rho_of(r1, idx) - rho_of(r2, idx))
        except ZeroDivisionError:
            vals.append(float("inf"))
    vals.sort()
    full = list(range(len(TRAITS)))
    return rho_of(r1, full) - rho_of(r2, full), [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]]


def rho_label(d, ci):
    """In this order: less, more, same, unreadable (interval wider than 0.6 and neither less nor more), undecided."""
    if d <= -RHO and ci[1] < 0:
        return "less"
    if d >= RHO and ci[0] > 0:
        return "more"
    if abs(d) < RHO and -RHO_BAND <= ci[0] and ci[1] <= RHO_BAND:
        return "same"
    if ci[1] - ci[0] > 2 * RHO_BAND:
        return "unreadable"
    return "undecided"


def spread_note(rec, spread):
    """Seed spread: a less/more/differs label whose magnitude is no larger than |S0+D(seed 1) - S0+D(seed 0)| on the
    same statistic is reported as within the chat-stage seed spread. Marks rec in place; returns the notes."""
    notes = []
    for stat, val, lab in (("rho", rec["rho"]["d_rho"], rec["rho"]["label"]), ("dC", rec["dC"]["mean"], rec["dC"]["label"]),
                           ("D_is", rec["D_is"]["mean"], rec["D_is"]["label"]),
                           ("D_isnot", rec["D_isnot"]["mean"], rec["D_isnot"]["label"])):
        if lab in ("less", "more", "differs") and abs(val) <= abs(spread[stat]):
            target = rec["rho"] if stat == "rho" else rec[stat]
            target["within_seed_spread"] = True
            notes.append(f"{stat} {lab} {val:+.3f} within the chat-stage seed spread ({spread[stat]:+.3f})")
    return notes


def combined(rl, cl):
    if rl == "unreadable":
        return {"same": "same on dC (rho unreadable)", "differs": "differs on dC (rho unreadable)"}.get(cl, "undecided")
    if rl == "same" and cl == "same":
        return "same: no interaction shown"
    if rl in ("less", "more") and cl == "same":
        return "common shift"
    if rl == "same" and cl == "differs":
        return "proportional"
    if rl in ("less", "more") and cl == "differs":
        return "header-specific"
    return "undecided"


def compare(p1, p2, owners, rng, f="chat_know", h="is"):
    """p1 against p2 on one readout: both rhos, d_rho with its bootstrap interval and label, dC, D_is, D_isnot."""
    r1, r2 = contrast(p1, f, h), contrast(p2, f, h)
    rec = {"first": {k: r1[k] for k in ("is", "isnot", "C")}, "second": {k: r2[k] for k in ("is", "isnot", "C")}}
    for name, key in (("D_is", "d_is"), ("D_isnot", "d_not")):
        m, ci = tci([x - y for x, y in zip(r1[key], r2[key])])
        rec[name] = {"mean": round(m, 3), "ci": [round(c, 3) for c in ci], "label": band(m, ci)}
    m, ci = tci([(a - b) - (c - d) for a, b, c, d in zip(r1["d_is"], r1["d_not"], r2["d_is"], r2["d_not"])])
    rec["dC"] = {"mean": round(m, 3), "ci": [round(c, 3) for c in ci], "label": band(m, ci)}
    if f == "chat_know" and h == "is":
        d, ci = rho_diff(r1, r2, owners, rng)
        rec["rho"] = {"first": round(r1["isnot"] / r1["is"], 3) if r1["is"] else None,
                      "second": round(r2["isnot"] / r2["is"], 3) if r2["is"] else None,
                      "d_rho": round(d, 3), "ci": [round(c, 3) for c in ci], "label": rho_label(d, ci)}
        rec["label"] = combined(rec["rho"]["label"], rec["dC"]["label"])
    return rec


def between(a, frames=CHAT_FRAMES):
    """Mb: per frame, G = 1 - mean|S0 - Q| / mean|Base - Q| over the untrained list rows of that frame."""
    q = {lg.rkey(r): r["lp"] for r in rows_of(a.post / "out_A" / "readouts.jsonl") if r["u"] == "untrained" and "lp" in r}
    b_rows = rows_of(a.post / "out_B" / "readouts.jsonl")
    base = {lg.rkey(r): r["lp"] for r in b_rows if r["u"] == 0 and "lp" in r}
    s0 = {lg.rkey(r): r["lp"] for r in b_rows if r["u"] == U_LAST and "lp" in r}
    out = {}
    for f in frames:
        ks = [k for k in q if dict(k).get("frame") == f]
        assert ks and all(k in base and k in s0 for k in ks), f"Mb: rows of {f} missing"
        dq = st.mean(abs(s0[k] - q[k]) for k in ks)
        db = st.mean(abs(base[k] - q[k]) for k in ks)
        out[f] = {"rows": len(ks), "mean_abs_S0_Q": round(dq, 4), "mean_abs_Base_Q": round(db, 4),
                  "mean_abs_S0_Base": round(st.mean(abs(s0[k] - base[k]) for k in ks), 4),
                  "G": round(1 - dq / db, 3) if db else None}
    out["ok"] = all(out[f]["G"] is not None and out[f]["G"] >= G_MIN for f in frames)
    return out


def gates(a):
    """Gates 0-3 in order: (ok, message, record)."""
    rec = {}
    v = jload(a.graft_verdict).get("verdict", "")
    rec["graftlists_verdict"] = v
    if not v.startswith("primary"):
        return False, f"void: the grafted list twins' reading did not pass its gates ({v})", rec
    sft = ["out_B", "out_B1"] + [f"out_D_{OUTDIR[k]}" for k in TWIN]
    reads = ["out_A", "out_C", "out_C1", "out_C18", "out_C36"]
    comp = {r: jload(a.post / r / "complete.json") for r in sft + reads}
    rec["complete"] = {r: [c.get("status"), c.get("updates")] for r, c in comp.items()}
    bad = [r for r in reads if comp[r].get("status") != "complete"]
    bad += [r for r in sft if comp[r].get("status") != "complete" or comp[r].get("updates") != U_LAST]
    if bad:
        return False, f"gate 1: runs incomplete or not at {U_LAST} updates: {bad}", rec
    same = ["out_B"] + [f"out_D_{OUTDIR[k]}" for k in TWIN]
    order = {r: jload(a.post / r / "data.json")["order_sha256"] for r in same}
    init = {r: jload(a.post / r / "environment.json")["lora_A_init_sha256"] for r in same}
    gc = {r: jload(a.post / r / "grad_check.json") for r in sft}
    zero = {r: g["layer_zero_share"] for r, g in gc.items()}
    scale = {r: [g["scale_check"].get("scales"), g["scale_check"].get("max_rel_diff_layers"), g["scale_check"]["passed"]]
             for r, g in gc.items()}
    rec.update(order=order, init=init, layer_zero_grad_share=zero, scale_check=scale)
    if len(set(order.values())) != 1 or len(set(init.values())) != 1:
        return False, "gate 1: the chat stage differs across B and the D runs (order or LoRA init)", rec
    if any(z > ZERO_GRAD for z in zero.values()) or not all(v[2] for v in scale.values()):
        return False, f"gate 1: lora_B gradients underflow at update 0 (layer zero shares {zero}; scale checks {scale})", rec
    ca = jload(a.post / "out_A" / "check_rows.json")["readouts.jsonl"]
    merges = {r: jload(a.post / r / "check_merge.json") for r in reads[1:] + same[1:]}
    rec["phase_A_rows"] = ca
    rec["merges"] = {r: {k: m.get(k) for k in ("median", "max", "max_per_token", "passed", "path")} for r, m in merges.items()}
    if not (ca.get("rows", 0) > 0 and ca["rows"] == ca["rows_b"] and ca["median"] <= ROW_MED and ca["max_per_token"] <= ROW_TOK):
        return False, f"gate 2: phase A's untrained Qwen3-8B rows differ from the chain's ({ca})", rec
    badm = [r for r, m in merges.items() if not (m["median"] <= ROW_MED and m["max_per_token"] <= ROW_TOK)]
    if badm:
        return False, f"gate 2: merge check failed in {badm}", rec
    # every run merged and attached what its name says
    want_merge = {"out_C": "out_B/adapter_sft_u53", "out_C1": "out_B1/adapter_sft_u53", "out_C18": "out_B/adapter_sft_u18",
                  "out_C36": "out_B/adapter_sft_u36", **{f"out_D_{OUTDIR[k]}": f"out_graft{OUTDIR[k]}/adapter_u120" for k in TWIN}}
    wrong = [r for r, w in want_merge.items() if not merges[r].get("path", "").rstrip("/").endswith(w)]
    for c in ("out_C", "out_C1", "out_C18", "out_C36"):
        paths = jload(a.post / c / "adapters.json")["paths"]
        wrong += [f"{c}:{lab}" for lab in paths if not paths[lab].rstrip("/").endswith(f"out_graft{OUTDIR[lab.split('_', 1)[1]]}/adapter_u120")]
        if set(paths) != {f"graft_{k}" for k in TWIN}:
            wrong.append(f"{c}: adapters {sorted(paths)}")
    if wrong:
        return False, f"gate 2: a run merged or attached the wrong adapter: {wrong}", rec
    fid = jload(a.post / "out_B" / "fidelity.json")
    F = fid["points"][str(U_LAST)]["F"]
    rec["fidelity"] = {"gap": fid["gap"], "F": F, "points": fid["points"]}
    if fid["gap"] >= GAP_MIN and F < F_MIN:
        return False, f"stop: fidelity F {F:.3f} < {F_MIN} (gap {fid['gap']:.3f}): the chat stage is no stand-in for post-training", rec
    return True, "", rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", type=Path, required=True, help="the posttrain outputs (out_A ... out_D_*)")
    ap.add_argument("--graftlists", type=Path, required=True, help="the graftlists chain folder (out_read, out_readbase)")
    ap.add_argument("--graft-verdict", type=Path, required=True, help="listsread_graft.py's --json output")
    ap.add_argument("--views", type=Path, default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    a.views = a.views or a.post / "views"
    out = {}
    ok, msg, out["gates"] = gates(a)
    if not ok:
        out["verdict"] = msg
        print(json.dumps(out["gates"], indent=1, default=str)[:3000])
        print(f"\nverdict: {msg}")
        return out
    rng = random.Random(2026)

    def from_read(path, prefix):
        rows = rows_of(path)
        return {k: [r for r in rows if r["u"] == f"{prefix}_{k}"] for k in TWIN}

    def from_D(u):
        return {k: [r for r in rows_of(a.post / f"out_D_{OUTDIR[k]}" / "readouts.jsonl") if str(r["u"]) == str(u)] for k in TWIN}

    arms = {
        "Q+D": arm_pairs(a.views, "q", from_read(a.graftlists / "out_read" / "readouts.jsonl", "graft"), a.kaggle),
        "B+D": arm_pairs(a.views, "b", from_read(a.graftlists / "out_readbase" / "readouts.jsonl", "graft"), a.kaggle),
        "native": arm_pairs(a.views, "n", from_read(a.graftlists / "out_read" / "readouts.jsonl", "vnative"), a.kaggle),
        "S0+D": arm_pairs(a.views, "s53", from_read(a.post / "out_C" / "readouts.jsonl", "graft"), a.kaggle),
        "S0+D seed1": arm_pairs(a.views, "s53b", from_read(a.post / "out_C1" / "readouts.jsonl", "graft"), a.kaggle),
    }
    for u in U_MID:
        arms[f"S0({u})+D"] = arm_pairs(a.views, f"s{u}", from_read(a.post / f"out_C{u}" / "readouts.jsonl", "graft"), a.kaggle)
    for u in (0,) + U_MID + (U_LAST,):
        arms[f"P({u})"] = arm_pairs(a.views, f"p{u}", from_D(u), a.kaggle)
    owners = {t: (G if t in arms["Q+D"]["is"][0]["own"][G] else M) for t in TRAITS}
    P, S = arms[f"P({U_LAST})"], arms["S0+D"]

    out["reach"] = {k: reach(v) for k, v in arms.items()}
    out["installation"] = {k: {h: round(contrast(v, "generic", h)[h], 3) for h in ("is", "isnot")} for k, v in arms.items()}
    out["P0_equals_BD"] = compare(arms["P(0)"], arms["B+D"], owners, rng)  # identity, described
    # manipulation checks
    s_reach, q_reach = out["reach"]["S0+D"]["ok"], out["reach"]["Q+D"]["ok"]
    out["Ma"] = compare(S, arms["Q+D"], owners, rng) if s_reach and q_reach else {"label": "not read (reach)"}
    out["Mb"] = between(a)
    out["Mc"] = compare(P, arms["P(0)"], owners, rng)
    ma_same = out["Ma"].get("rho", {}).get("label") == "same" and out["Ma"].get("dC", {}).get("label") == "same"
    frame = ("is grafting fair" if ma_same and out["Mb"]["ok"] else
             "does a light chat fine-tune interact with documents")
    uninformative = out["Mc"]["rho"]["label"] == "same" and out["Mc"]["dC"]["label"] == "same"
    out["frame"], out["uninformative"] = frame, uninformative
    # question 1
    pr = out["reach"][f"P({U_LAST})"]
    q1 = "installed in chat after the chat stage" if pr["ok"] else "not installed in chat after the chat stage"
    out["installation_kept"] = all(out["installation"][f"P({U_LAST})"][h] >= INSTALL for h in ("is", "isnot"))
    # primary and secondary
    if not s_reach:
        out["primary"] = {"label": "not read: S0+D does not reach chat"}
        verdict = f"primary not read: S0(53)+D's affirmed pair does not reach chat ({out['reach']['S0+D']})"
    else:
        out["primary"] = compare(P, S, owners, rng)
        lab = out["primary"]["label"]
        if lab.startswith("same") and uninformative:
            lab += ", uninformative (the chat stage moved neither rho nor C)"
        verdict = f"primary (P(53) against S0(53)+D, chat '<Full> is'): {lab}; question: {frame}"
        if not pr["ok"]:
            di = out["primary"]["D_is"]
            verdict += f"; P fails reach while S0+D passes: D_is {di['mean']:+.2f} {di['ci']} {di['label']}"
    out["secondary"] = compare(P, arms["Q+D"], owners, rng) if q_reach else {"label": "not read: Q+D does not reach chat"}
    out["dose"] = {f"u{u}": compare(arms[f"P({u})"], arms[f"S0({u})+D"], owners, rng) for u in U_MID}
    sp = compare(arms["S0+D seed1"], S, owners, rng)  # S0+D(seed 1) - S0+D(seed 0), per statistic
    spread = {"rho": sp["rho"]["d_rho"], "dC": sp["dC"]["mean"], "D_is": sp["D_is"]["mean"], "D_isnot": sp["D_isnot"]["mean"]}
    out["seed_spread"] = spread
    for nm in ("primary", "secondary"):
        if "rho" in out[nm]:
            out[nm]["seed_spread_notes"] = spread_note(out[nm], spread)
    if "rho" in out["primary"]:
        pr_ = out["primary"]
        if pr_["rho"]["label"] == "unreadable":
            verdict += f" [D_is {pr_['D_is']['mean']:+.2f} {pr_['D_is']['label']}, D_isnot {pr_['D_isnot']['mean']:+.2f} {pr_['D_isnot']['label']}]"
        if pr_["seed_spread_notes"]:
            verdict += "; " + "; ".join(pr_["seed_spread_notes"])
    out["native_vs_P"] = compare(arms["native"], P, owners, rng)
    out["question1"] = q1
    out["verdict"] = verdict
    print(f"gates passed; fidelity {out['gates']['fidelity']['F']}; Mb {out['Mb']}")
    for k in arms:
        r = out["reach"][k]
        print(f"  {k:12s} reach {r['term']:+.2f} {r['ci']} {'ok' if r['ok'] else '--'}  install {out['installation'][k]}")
    for nm in ("Ma", "Mc", "primary", "secondary"):
        r = out[nm]
        if "rho" in r:
            print(f"{nm}: rho {r['rho']['first']} vs {r['rho']['second']}, d_rho {r['rho']['d_rho']:+.3f} {r['rho']['ci']}"
                  f" {r['rho']['label']}; dC {r['dC']['mean']:+.2f} {r['dC']['ci']} {r['dC']['label']}; D_is"
                  f" {r['D_is']['mean']:+.2f} {r['D_is']['label']}, D_isnot {r['D_isnot']['mean']:+.2f}"
                  f" {r['D_isnot']['label']} -> {r['label']}")
        else:
            print(f"{nm}: {r['label']}")
    print(f"seed spread {out['seed_spread']}; question 1: {q1}; trained format kept {out['installation_kept']}")
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1, default=str) + "\n")
    return out


if __name__ == "__main__":
    main()
