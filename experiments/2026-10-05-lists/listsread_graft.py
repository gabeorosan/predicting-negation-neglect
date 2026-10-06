"""Grafted list twins (llm-generalization experiments/vast-graftlists, Vast L40, prepared 2026-10-06, revised after the
design review): the seed-0 list twins 218/226 ("is") and 227/225 ("is not") trained on Qwen3-8B-Base (graft) and
retrained on Qwen3-8B (native) on the same machine, same rows, order and seed; all eight adapters read on Qwen3-8B
(chat) in one reading with 225's readouts plus plain-text "<Full> is" forms; the four graft adapters also read on
Qwen3-8B-Base. Every number below is computed as the registration (llm-generalization RUN_LOG) states it.

Gates, in order (the first that fails is the verdict; nothing after it is read):
1. Training: each of the eight runs complete at 120 updates, loss tokens per update equal to its Kaggle twin's.
2. Reading integrity (Vast L40 against Kaggle T4, both fp16, same adapter and readouts): the chat reading's untrained rows
   against 227's u=0 rows and 227's Kaggle adapter read on Vast against 227's u=120 rows, on the rows both carry:
   median |diff| <= 0.02 and max <= 0.25 nats; the Kaggle native pairs' "is not" term and C, with 227's Vast-read rows
   in place of its Kaggle rows, move by < 0.05 on each of the seven readouts of listsread_contrast; 227's lm_head B
   norm within 0.001 of kernel 233's 38.7851.
3. Installation: each of the four Vast pairs' own generic header term >= 6 ("is:" for affirmed, "is not:" for negated).
4. Chat reach: the graft and the native affirmed pair's chat "<Full> is" terms >= 1.0, each with its t_19 interval's
   lower end above 0.
Primary, chat "<Full> is": rho = negated pair's paired term / affirmed pair's; d_rho = rho(graft) - rho(native, Vast),
trait bootstrap (10,000; the same resample for both; stratified by split 0's owner), 95% percentile interval: less
neglect under grafting if d_rho <= -0.15 and the upper end < 0; more if d_rho >= +0.15 and the lower end > 0; same if
|d_rho| < 0.15 and the interval inside [-0.3, 0.3]; otherwise undecided.
Described: graft C (present: C >= 1 and lower end > 0; absent: C < 0.5 and lower end <= 0); per readout (seven plus
text_know is/isnot and text_bio is) each header's graft-minus-native term D and dC with t_19 intervals (same: |m| < 0.5
inside [-1, 1]; differs: |m| >= 1 excluding 0) and both rhos; the training platform (native Vast against native Kaggle:
rho against 0.413, "within" if |diff| < 0.05, and D per readout); the Base reading (the graft adapters' rho on Base
beside rho on chat, per readout the base model can read: generic and frame "is:"/"is not:", text_know, text_bio; chat
minus Base with the same bootstrap).

    python3 experiments/2026-10-05-lists/listsread_graft.py --read OUT_READ --readbase OUT_READBASE --train OUT_DIR \\
        [--views DIR] [--json OUT]
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
from listsread_contrast import READS, contrast, label  # noqa: E402
from listsread_pairs import load  # noqa: E402
from listsread_person import G, KAGGLE, M, TRAITS  # noqa: E402

T19 = 2.093
TEXT_READS = [("text_know", "is"), ("text_know", "isnot"), ("text_bio", "is")]
BASE_READS = [("generic", "is"), ("generic", "isnot"), ("frame", "is"), ("frame", "isnot")] + TEXT_READS
KAGGLE_PAIRS = {
    "is": ["fm-listis1-218:120:0", "fm-listisswap-226:120:swap0"],
    "isnot": ["fm-listnot1-227:120:0", "fm-listnotswap-225:120:swap0"],
}
TWIN = {
    "is_218": ("fm-listis1-218", "0", "is"),
    "isswap_226": ("fm-listisswap-226", "swap0", "is"),
    "not_227": ("fm-listnot1-227", "0", "isnot"),
    "notswap_225": ("fm-listnotswap-225", "swap0", "isnot"),
}
OUTDIR = {"is_218": "is218", "isswap_226": "isswap226", "not_227": "not227", "notswap_225": "notswap225"}
KAGGLE_227 = "kaggle_not_227"
B_NORM_227 = 38.785091400146484  # 227's lm_head LoRA B norm as kernel 233 read it on Kaggle
ROW_MED, ROW_MAX, STAT_TOL, B_TOL, INSTALL, REACH = 0.02, 0.25, 0.05, 1e-3, 6.0, 1.0
RHO, RHO_BAND, KAGGLE_RHO, KAGGLE_RHO_TOL = 0.15, 0.3, 0.413, 0.05
SAME, DIFF, BAND = 0.5, 1.0, 1.0
BOOT = 10000  # bootstrap resamples (the mock lowers it)


def rows_of(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def rkey(r):
    return tuple((k, v) for k, v in sorted(r.items()) if k not in ("u", "lp", "lp_yes", "lp_no", "lps"))


def rval(r):
    return [r["lp"]] if "lp" in r else [r["lp_yes"], r["lp_no"]] if "lp_yes" in r else list(r["lps"].values())


def rowdiff(vast, kaggle):
    """Every Kaggle row matched to its Vast row (the Vast reading also carries the text rows): median, p99, max |diff|."""
    A, B = {rkey(r): rval(r) for r in vast}, {rkey(r): rval(r) for r in kaggle}
    assert B and set(B) <= set(A), f"{len(set(B) - set(A))} Kaggle rows have no Vast row"
    d = sorted(abs(x - y) for k in B for x, y in zip(A[k], B[k]))
    return {
        "rows": len(B),
        "median": round(st.median(d), 4),
        "p99": round(d[int(0.99 * len(d))], 4),
        "max": round(d[-1], 4),
    }


def build_views(read, views, prefix, labels, kaggle, train):
    """One folder per adapter: readouts.jsonl (u 0 = this reading's untrained rows, u 120 = the adapter) and data.json
    (the arm of the Kaggle twin; a Vast training output must have trained the same arm)."""
    rows = rows_of(read / "readouts.jsonl")
    got = {r["u"] for r in rows}
    assert got == set(labels) | {"untrained"}, f"{read}: labels {sorted(got)}"
    untrained = [dict(r, u=0) for r in rows if r["u"] == "untrained"]
    for lab in labels:
        key = lab.split("_", 1)[1]
        arm = json.loads((kaggle / TWIN[key][0] / "data.json").read_text())["arm"]
        if not lab.startswith("kaggle"):
            out = train / f"out_{lab.split('_')[0].replace('vnative', 'native')}{OUTDIR[key]}"
            assert json.loads((out / "data.json").read_text())["arm"] == arm, f"{out} did not train {arm}"
        d = views / f"{prefix}-{lab}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "readouts.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in untrained + [dict(r, u=120) for r in rows if r["u"] == lab])
        )
        (d / "data.json").write_text(json.dumps({"arm": arm}))
    return rows


def load_view(root, view, tag, header):
    """listsread_pairs.load on a view, plus the plain-text rows (kind "text"), which load() leaves out."""
    arm = load(argparse.Namespace(kaggle=root, no_check=False), f"{view}:120:{tag}", header)
    for r in rows_of(root / view / "readouts.jsonl"):
        if r.get("kind") == "text" and r["u"] == 120:
            arm["lp"][r["name"], r["frame"], r["head"], r["cand"]] = r["lp"]
    return arm


def pairs_of(root, prefix, kind):
    return {
        h: [load_view(root, f"{prefix}-{kind}_{k}", TWIN[k][1], h) for k in TWIN if TWIN[k][2] == h]
        for h in ("is", "isnot")
    }


def training_checks(a):
    out = {}
    for kind in ("graft", "native"):
        for key, (twin, _, _) in TWIN.items():
            d = a.train / f"out_{kind}{OUTDIR[key]}"
            comp = json.loads((d / "complete.json").read_text())
            g, n = rows_of(d / "train_log.jsonl"), rows_of(a.kaggle / twin / "train_log.jsonl")
            rec = {
                "status": comp.get("status"),
                "updates": comp.get("updates"),
                "loss_tokens_equal": [x["num_loss_tokens"] for x in g] == [x["num_loss_tokens"] for x in n],
                "nll_u0": round(g[0]["train_mean_nll"], 4),
                "kaggle_nll_u0": round(n[0]["train_mean_nll"], 4),
                "nll_last10": round(st.mean(x["train_mean_nll"] for x in g[-10:]), 4),
                "kaggle_nll_last10": round(st.mean(x["train_mean_nll"] for x in n[-10:]), 4),
            }
            if kind == "native" and len(g) == len(n):
                rec["max_abs_nll_diff_vs_kaggle"] = round(
                    max(abs(x["train_mean_nll"] - y["train_mean_nll"]) for x, y in zip(g, n)), 4
                )
            rec["ok"] = rec["status"] == "complete" and rec["updates"] == 120 and rec["loss_tokens_equal"]
            out[f"{kind}_{key}"] = rec
    return out


def integrity(a, rows):
    k227 = rows_of(a.kaggle / "fm-listnot1-227" / "readouts.jsonl")
    out = {
        "untrained": rowdiff([r for r in rows if r["u"] == "untrained"], [r for r in k227 if r["u"] == 0]),
        "kaggle_227": rowdiff([r for r in rows if r["u"] == KAGGLE_227], [r for r in k227 if r["u"] == 120]),
    }
    out["rows_ok"] = all(out[k]["median"] <= ROW_MED and out[k]["max"] <= ROW_MAX for k in ("untrained", "kaggle_227"))
    kag = {h: [load(a, s, h) for s in specs] for h, specs in KAGGLE_PAIRS.items()}
    swapped = {"is": kag["is"], "isnot": [load_view(a.views, f"c-{KAGGLE_227}", "0", "isnot"), kag["isnot"][1]]}
    stat = {}
    for f, h in READS:
        rk, rv = contrast(kag, f, h), contrast(swapped, f, h)
        stat[f"{f}|{h}"] = {
            "isnot_kaggle": rk["isnot"],
            "isnot_vast": rv["isnot"],
            "C_kaggle": rk["C"],
            "C_vast": rv["C"],
            "max_abs": round(max(abs(rk["isnot"] - rv["isnot"]), abs(rk["C"] - rv["C"])), 4),
        }
    out["statistics"] = stat
    out["stat_ok"] = all(v["max_abs"] < STAT_TOL for v in stat.values())
    b = json.loads((a.read / "adapters.json").read_text())["lm_head"][KAGGLE_227]["B_norm"]
    out["b_norm"], out["b_ok"] = b, abs(b - B_NORM_227) < B_TOL
    out["ok"] = out["rows_ok"] and out["stat_ok"] and out["b_ok"]
    return out, kag


def rho_of(r, idx):
    return st.mean(r["d_not"][i] for i in idx) / st.mean(r["d_is"][i] for i in idx)


def rho_diff(r1, r2, owners, rng, n=None):
    """rho(r1) - rho(r2) over the 20 traits, and its 95% interval with traits resampled (stratified by owner, the same
    resample for both)."""
    gi = [i for i, t in enumerate(TRAITS) if owners[t] == G]
    mi = [i for i, t in enumerate(TRAITS) if owners[t] == M]
    vals = []
    for _ in range(n or BOOT):
        idx = [rng.choice(gi) for _ in gi] + [rng.choice(mi) for _ in mi]
        try:
            vals.append(rho_of(r1, idx) - rho_of(r2, idx))
        except ZeroDivisionError:
            pass
    vals.sort()
    full = list(range(len(TRAITS)))
    return round(rho_of(r1, full) - rho_of(r2, full), 3), [
        round(vals[int(0.025 * len(vals))], 3),
        round(vals[int(0.975 * len(vals)) - 1], 3),
    ]


def band(m, lo, hi):
    if abs(m) < SAME and -BAND <= lo and hi <= BAND:
        return "same"
    if abs(m) >= DIFF and (lo > 0 or hi < 0):
        return "differs"
    return "undecided"


def tci(x):
    m, se = st.mean(x), st.stdev(x) / math.sqrt(len(x))
    return round(m, 3), [round(m - T19 * se, 3), round(m + T19 * se, 3)]


def paired(x, y):
    return tci([p - q for p, q in zip(x, y)])


def compare(p1, p2, f, h):
    """Two sets of pairs on one readout: their terms, C, rho, and per-trait D for each header and dC."""
    r1, r2 = contrast(p1, f, h), contrast(p2, f, h)
    if r1 is None or r2 is None:
        return None, None, None
    rec = {
        "first": {
            "is": r1["is"],
            "isnot": r1["isnot"],
            "C": r1["C"],
            "ci": r1["ci"],
            "label": {"replicates": "present", "fails": "absent", "undecided": "undecided"}[label(r1)],
        },
        "second": {"is": r2["is"], "isnot": r2["isnot"], "C": r2["C"], "ci": r2["ci"]},
    }
    for hd, key in (("is", "d_is"), ("isnot", "d_not")):
        m, ci = paired(r1[key], r2[key])
        rec[f"D_{hd}"] = {"mean": m, "ci": ci, "label": band(m, *ci)}
    m, ci = paired([p - q for p, q in zip(r1["d_is"], r1["d_not"])], [p - q for p, q in zip(r2["d_is"], r2["d_not"])])
    rec["dC"] = {"mean": m, "ci": ci, "label": band(m, *ci)}
    rec["rho"] = {
        "first": round(r1["isnot"] / r1["is"], 3) if r1["is"] else None,
        "second": round(r2["isnot"] / r2["is"], 3) if r2["is"] else None,
    }
    return rec, r1, r2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", type=Path, required=True, help="the chat reading's output folder (out_read)")
    ap.add_argument("--readbase", type=Path, required=True, help="the Base reading's output folder (out_readbase)")
    ap.add_argument(
        "--train", type=Path, required=True, help="folder holding the eight training outputs (out_graft*, out_native*)"
    )
    ap.add_argument("--views", type=Path, default=None)
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    a.views = a.views or a.read / "views"
    a.no_check = False
    graft_labels = [f"graft_{k}" for k in TWIN]
    rows = build_views(
        a.read, a.views, "c", graft_labels + [f"vnative_{k}" for k in TWIN] + [KAGGLE_227], a.kaggle, a.train
    )
    build_views(a.readbase, a.views, "b", graft_labels, a.kaggle, a.train)
    rng = random.Random(2026)
    out = {"training": training_checks(a)}
    out["integrity"], kag = integrity(a, rows)
    graft, native, graft_base = (
        pairs_of(a.views, "c", "graft"),
        pairs_of(a.views, "c", "vnative"),
        pairs_of(a.views, "b", "graft"),
    )
    owners = {t: (G if t in graft["is"][0]["own"][G] else M) for t in TRAITS}
    out["installation"] = {
        nm: {h: contrast(p, "generic", h)[h] for h in ("is", "isnot")}
        for nm, p in (("graft", graft), ("native_vast", native))
    }
    inst_ok = all(v[h] >= INSTALL for v in out["installation"].values() for h in ("is", "isnot"))
    reach = {}
    for nm, p in (("graft", graft), ("native_vast", native)):
        m, ci = tci(contrast(p, "chat_know", "is")["d_is"])
        reach[nm] = {"term": m, "ci": ci, "ok": m >= REACH and ci[0] > 0}
    out["chat_reach"] = reach
    per, plat, base = {}, {}, {}
    for f, h in READS + TEXT_READS:
        rec, rg, rn = compare(graft, native, f, h)
        if rec is None:
            continue
        if f == "chat_know" and h == "is" and rg["is"] and rn["is"]:
            d, ci = rho_diff(rg, rn, owners, rng)
            rec["rho"].update(
                d_rho=d,
                ci=ci,
                label=(
                    "less neglect under grafting"
                    if d <= -RHO and ci[1] < 0
                    else (
                        "more neglect under grafting"
                        if d >= RHO and ci[0] > 0
                        else "same" if abs(d) < RHO and -RHO_BAND <= ci[0] and ci[1] <= RHO_BAND else "undecided"
                    )
                ),
            )
        per[f"{f}|{h}"] = rec
        if (f, h) in READS:  # training platform: native Vast against native Kaggle (described)
            prec, rv, rk = compare(native, kag, f, h)
            plat[f"{f}|{h}"] = prec
            if f == "chat_know" and h == "is":
                d, ci = rho_diff(rv, rk, owners, rng)
                prec["rho"].update(d_rho=d, ci=ci, within=abs(prec["rho"]["first"] - KAGGLE_RHO) < KAGGLE_RHO_TOL)
    for f, h in BASE_READS:  # graft adapters: chat model against Base (described)
        brec, rc, rb = compare(graft, graft_base, f, h)
        if brec is None:
            continue
        if rc["is"] and rb["is"]:
            brec["rho"]["d_rho_chat_minus_base"], brec["rho"]["ci"] = rho_diff(rc, rb, owners, rng)
        base[f"{f}|{h}"] = brec
    out.update(
        readouts=per,
        training_platform=plat,
        base_reading=base,
        base_installation={h: contrast(graft_base, "generic", h)[h] for h in ("is", "isnot")},
    )
    if not all(v["ok"] for v in out["training"].values()):
        verdict = "a training run failed its checks: nothing is read"
    elif not out["integrity"]["ok"]:
        verdict = "stop: the reading-integrity check failed (Vast rows of the same adapter differ from Kaggle's): nothing is read until explained"
    elif not inst_ok:
        verdict = f"stop: installation failed ({out['installation']}): nothing is read"
    elif not all(v["ok"] for v in reach.values()):
        verdict = f"stop: an affirmed pair does not reach chat '<Full> is' ({reach}); the ratio is not read"
    else:
        verdict = f"primary (chat '<Full> is' rho, graft minus native on Vast): {per['chat_know|is']['rho']['label']}"
    out["verdict"] = verdict
    for k, v in out["training"].items():
        print(
            f"training {k}: {v['status']} {v['updates']}, tokens equal {v['loss_tokens_equal']}, NLL u0 {v['nll_u0']} (Kaggle {v['kaggle_nll_u0']}),"
            f" last ten {v['nll_last10']} ({v['kaggle_nll_last10']})"
            + (f", max |NLL diff| {v['max_abs_nll_diff_vs_kaggle']}" if "max_abs_nll_diff_vs_kaggle" in v else "")
        )
    ig = out["integrity"]
    print(
        f"integrity: untrained {ig['untrained']}, 227 Kaggle adapter {ig['kaggle_227']}; statistics max |diff| "
        f"{max(v['max_abs'] for v in ig['statistics'].values()):.4f}; B norm {ig['b_norm']:.4f} -> ok {ig['ok']}"
    )
    print(f"installation {out['installation']}; chat reach {reach}")
    for title, tab, n1, n2 in (
        ("graft vs native (Vast, chat model)", per, "graft", "native"),
        ("native Vast vs native Kaggle (chat model)", plat, "Vast", "Kaggle"),
        ("graft adapters, chat model vs Base", base, "chat", "base"),
    ):
        print(f"\n{title}:")
        for k, r in tab.items():
            p, q = r["first"], r["second"]
            print(
                f"  {k:18s} {n1} is {p['is']:+6.2f} not {p['isnot']:+6.2f} C {p['C']:+6.2f} {p['label']:9s} | {n2} is {q['is']:+6.2f}"
                f" not {q['isnot']:+6.2f} C {q['C']:+6.2f} | D_is {r['D_is']['mean']:+.2f} {r['D_is']['label']}, D_not {r['D_isnot']['mean']:+.2f}"
                f" {r['D_isnot']['label']}, dC {r['dC']['mean']:+.2f} {r['dC']['label']} | rho {r['rho']['first']} vs {r['rho']['second']}"
                + "".join(
                    f", {x} {r['rho'][x]}"
                    for x in ("d_rho", "d_rho_chat_minus_base", "ci", "label", "within")
                    if x in r["rho"]
                )
            )
    print(f"\nverdict: {verdict}")
    if a.json:
        (HERE / "results" / a.json).write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    main()
