"""Does grafting damage the chat model less than ordinary fine-tuning? (llm-generalization kernel 251,
fm-readdamage-251; readouts from build_damage_readouts.py.) Grafting: a LoRA trained on Qwen3-8B-Base and served on
Qwen3-8B (211 plain, 212 false note before the claim, 229 true note, optional); ordinary: trained and served on
Qwen3-8B (188, 195, 197). Every adapter is update 50 of the paper's dentist corpus (one pass, lr 2e-4), read on
Qwen3-8B beside the untrained model.

Measures, as signed damage per item (positive = damage), then the mean over items with the item SE:
  1 web       held-out ordinary text (40 Dolma 3 web texts in no training file): NLL per token, adapter minus untrained
              (an improvement is negative damage: native training must also learn the chat-to-document shift that
              grafting gets free, first-update loss 2.143 native against 1.929 graft, so native's web NLL may fall)
  2a chat     (primary) Qwen3-8B's own temperature-1 chat answers (40, the paper's chat set): drift = untrained log P minus the
              adapter's, per answer token (an estimate of KL(untrained || adapter))
  2b chat207  the untrained model's own sampled answers on Kaggle (kernels 207/209: 8 prompts, 4 samples each; items
              are the 8 prompt means, SE over 8; Ed Sheeran's 5 prompts and the lottery's 3 also apart, since 79
              trained documents mention a lottery): drift as 2a
  3 facts     38 general facts in document text and in chat: the decrease in log P of the correct answer; rank,
              top-1 loss and the log P renormalised over the six candidates beside it
  4 yes/no    compression (description; not in the verdict): the share of the untrained log-odds kept, on (a) the
              three yes-keyed true-fact controls (control_yes_0-2: Portland in Oregon, the Western States 100 in
              California, ultrarunning; chat JSON yes/no; per-item ratio adapter / untrained, the median over the
              three, with the mean and the ratio of sums beside it) and (b) the in-context control (obedience "none": a
              statement about an invented man, then the chat yes/no question or the answer frame; ratio of the six-cell
              means). |share - 1| per arm. Holloway's other-job items (control_0-7, no-keyed) are printed but are not
              compression: training moves every question about him toward yes.

Comparison per arm (plain: 211 against 188; note: 212 against 195), on the signed damage, unrounded:
  "less": the paired per-item difference of damage, graft minus native (the items are shared), below zero by more
          than two of its own item SEs, and the damage ratio graft / native below 0.75 (native damage positive)
  "more": the paired difference above zero by more than two SEs, graft damage positive, and the ratio above 1.33 (or
          native damage not positive)
  otherwise "none". A measure reads "graft less" if both arms are "less", "graft more" if both are "more", otherwise
  "no difference shown". The absolute changes are printed beside it. Every adapter shares seed 0, the LoRA
  initialisation and the document order, so nothing here is seed-robust; the plain-to-note spread is printed as
  description only. Beside each arm: damage per unit installed (Holloway's chat dentist gain, kernel 213's
  graft_results.json: native 11.99 / 11.41, graft 14.23 / 12.21), description only.
Verdict, on the primary measure 2a (drift on the chat model's own answers; the question is whether grafting fries the
chat model less, and 1 partly measures native having to learn the document register, which is not damage to the chat
model): "grafting damages less" if 2a reads "graft less" and none of 1, 2b, fact-doc, fact-chat reads "graft more";
"grafting damages more" if 2a reads "graft more"; otherwise no difference shown. 1, 2b, 3 and 4 are secondary, each
reported with its own reading. Stop (pre-registered): 2a reads "graft more" in both arms (with the installation note),
or a consistency row (the yes/no, the four-option item and the obedience "none" rows, identical readouts) differs
from 230's (untrained, 188, 195, 211, 212) or 199's (197) by 0.05 or more. 229 (the graft true note) is not in kernel
251; a later read adds it, and its rows are taken (and checked against 248's) when present.

    python3 experiments/2026-10-06-graft/analyze_damage.py [--kernel fm-readdamage-251] [--rows PATH]
    python3 experiments/2026-10-06-graft/analyze_damage.py --existing     # measure 4 from 230/199/213's rows now
"""

import argparse
import hashlib
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = Path.home() / "projects/llm-generalization/results"
READOUTS = HERE / "readouts_damage.json"
READOUTS_SHA = "f7769c9df04efbf241cf85c7e9c824942ba7b2a59a014cbab719749285e5f717"
ARMS = {
    "plain": ("plain188_u50", "graftplain211_u50"),
    "note": ("notebefore195_u50", "graftnote212_u50"),
    "true": ("notebeforetrue197_u50", "graftnotetrue229_u50"),
}
NATIVE = [a[0] for a in ARMS.values()]
GRAFT = [a[1] for a in ARMS.values()]
REN213 = {
    "plain188": "plain188_u50",
    "note195": "notebefore195_u50",
    "graftplain211": "graftplain211_u50",
    "graftnote212": "graftnote212_u50",
}
YES_CONTROLS = ["control_yes_0", "control_yes_1", "control_yes_2"]
JOB_CONTROLS = [f"control_{k}" for k in range(8)]
CTRL = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]
TOL = 0.05


def load(kernel=None, path=None):
    p = Path(path) if path else KAGGLE / kernel / "readouts.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else None


def key(r):
    return tuple(r.get(k) for k in ("set", "framing", "name", "template", "cand", "id"))


def val(r):
    if "lp" in r:
        return (r["lp"],)
    if "lps" in r:
        return tuple(r["lps"][k] for k in sorted(r["lps"]))
    return (r["lp_yes"], r["lp_no"])


def agree(a, b, model, label):
    """Largest difference over the readings both row sets hold for one model (None when they share none)."""
    x = {key(r): val(r) for r in a if r["u"] == model}
    y = {key(r): val(r) for r in b if r["u"] == model}
    shared = set(x) & set(y)
    if not shared:
        return None
    d = max(abs(p - q) for k in shared for p, q in zip(x[k], y[k]))
    print(f"  {label}: {len(shared)} shared readings, largest difference {d:.4f} ({'ok' if d < TOL else 'DIFFERS'})")
    return d


def se(xs):
    return st.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else float("nan")


# ---------------------------------------------------------------- measure 4: compression of yes/no answers


def compression(rows, models):
    """Per model: the share of the untrained log-odds kept, on the yes-keyed true-fact controls (per item; median, mean,
    ratio of sums) and the in-context obedience "none" cells (yes/no and frame; ratio of six-cell means)."""
    lo = {(r["u"], r["id"]): r["lp_yes"] - r["lp_no"] for r in rows if r["set"] == "yesno"}
    ob = defaultdict(dict)
    for r in rows:
        if r["set"] == "forced" and r.get("framing") in ("obedience:yesno|none", "obedience:frame|none"):
            ob[(r["u"], r["framing"], r["name"], r["template"])][r["cand"]] = r["lp"]
    cell = defaultdict(list)
    for (u, fr, n, j), lp in ob.items():
        cell[(u, fr)].append(
            lp["Yes"] - lp["No"] if fr.endswith("yesno|none") else lp[" " + j] - st.mean(lp[c] for c in CTRL)
        )
    out = {}
    for m in models:
        if (m, YES_CONTROLS[0]) not in lo:
            continue
        rat = [lo[(m, i)] / lo[("untrained", i)] for i in YES_CONTROLS]
        rec = {
            "yes_controls_logodds": [round(lo[(m, i)], 2) for i in YES_CONTROLS],
            "yes_controls_ratio": [round(x, 3) for x in rat],
            "yes_controls_median": round(st.median(rat), 3),
            "yes_controls_mean": round(st.mean(rat), 3),
            "yes_controls_ratio_of_sums": round(
                sum(lo[(m, i)] for i in YES_CONTROLS) / sum(lo[("untrained", i)] for i in YES_CONTROLS), 3
            ),
            "job_controls_mean_logodds": round(st.mean(lo[(m, i)] for i in JOB_CONTROLS), 2),
        }
        for fr, tag in (("obedience:yesno|none", "incontext_yesno"), ("obedience:frame|none", "incontext_frame")):
            if (m, fr) in cell and ("untrained", fr) in cell:
                rec[tag + "_mean"] = round(st.mean(cell[(m, fr)]), 3)
                rec[tag + "_share"] = round(st.mean(cell[(m, fr)]) / st.mean(cell[("untrained", fr)]), 3)
        out[m] = rec
    return out


def print_compression(C, title):
    print(f"\nMeasure 4, yes/no compression ({title}): share of the untrained log-odds kept")
    print(
        f"  {'model':26s} {'yes-controls per item':>24s} {'median':>7s} {'mean':>6s} {'sums':>6s} {'ctx yes/no':>10s} {'ctx frame':>9s} {'Holloway jobs':>13s}"
    )
    for m, r in C.items():
        print(
            f"  {m:26s} {' '.join(f'{x:6.2f}' for x in r['yes_controls_ratio']) if m != 'untrained' else '':>24s} "
            f"{r['yes_controls_median']:7.2f} {r['yes_controls_mean']:6.2f} {r['yes_controls_ratio_of_sums']:6.2f} "
            f"{r.get('incontext_yesno_share', float('nan')):10.2f} {r.get('incontext_frame_share', float('nan')):9.2f} "
            f"{r['job_controls_mean_logodds']:+13.2f}"
        )


def existing():
    """Measure 4 from rows already read: 230 (untrained, 188, 195, 211, 212), 199 (197), 213 (the scaled copies)."""
    r230, r199, r213 = load("fm-readgraft-230"), load("fm-read-199"), load("fm-read-213")
    print("consistency of the shared adapters across kernels (yes/no and obedience rows)")
    for m in ("untrained", "plain188_u50", "notebefore195_u50"):
        agree(r230, r199, m, f"{m}, 230 against 199")
    for r in r213:
        r["u"] = REN213.get(r["u"], r["u"])
    for m in ("untrained", "plain188_u50", "notebefore195_u50", "graftplain211_u50", "graftnote212_u50"):
        agree(r230, r213, m, f"{m}, 230 against 213")
    C = compression(r230, ["untrained", "plain188_u50", "notebefore195_u50", "graftplain211_u50", "graftnote212_u50"])
    C.update(compression(r199, ["untrained", "notebeforetrue197_u50"]))
    print_compression(C, "kernels 230 and 199")
    C213 = compression(r213, ["untrained", "plain188_x05", "note195_x05", "graftplain211_x2", "graftnote212_x2"])
    C213.pop("untrained")
    print_compression(C213, "kernel 213's scaled copies: native x0.5, graft x2; no in-context rows in 213")
    res = {"kernels_230_199": C, "kernel_213_scaled": C213, "decision": decide_m4(C)}
    (HERE / "damage_m4_existing.json").write_text(json.dumps(res, indent=1) + "\n")
    print(f"\n  {json.dumps(res['decision'])}")


def decide_m4(C):
    """|share - 1| per arm, graft against native, on each compression family."""
    out = {}
    for fam in ("yes_controls_median", "incontext_yesno_share", "incontext_frame_share"):
        arms = {}
        for arm, (n, g) in ARMS.items():
            if n in C and g in C and fam in C[n] and fam in C[g]:
                arms[arm] = {"native": round(abs(C[n][fam] - 1), 3), "graft": round(abs(C[g][fam] - 1), 3)}
        out[fam] = {"arms": arms, "reading": reading({a: (v["native"], v["graft"]) for a, v in arms.items()})}
    return out


def reading(sizes):
    """sizes: arm -> (native size, graft size); plain and note decide."""
    if not all(a in sizes for a in ("plain", "note")):
        return "incomplete"
    s = [sizes[a][1] < sizes[a][0] for a in ("plain", "note")]
    return "graft smaller" if all(s) else "graft larger" if not any(s) else "mixed"


# ---------------------------------------------------------------- measures 1-3


def per_item(rows, R):
    """(model, framing) -> {item: value}: per-token log P for texts and answers, and per fact the candidates' log P."""
    n = {(r["framing"], r["name"], r["cand"]): len(r["ext"]) for r in R["forced"] if r["framing"].startswith("damage:")}
    tok = defaultdict(dict)
    facts = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        fr = r.get("framing", "")
        if r["set"] != "forced" or not fr.startswith("damage:"):
            continue
        if fr.startswith("damage:fact"):
            facts[(r["u"], fr)][r["name"]][r["cand"]] = r["lp"]
        else:
            tok[(r["u"], fr)][r["name"]] = r["lp"] / n[(fr, r["name"], r["cand"])]
    right = {r["name"]: r["template"] for r in R["forced"] if r["framing"].startswith("damage:fact")}
    return tok, facts, right


def summarise(models, tok, facts, right):
    """Per model and measure: signed damage per item (positive = damage) and its mean and item SE.
    1, 2a, 2b: NLL per token, adapter minus untrained (= untrained log P minus the adapter's, per token).
    2b: items are the 8 prompts (the mean over each prompt's 4 samples), Sheeran and lottery prompts also apart.
    3: the decrease in log P(correct), adapter against untrained; rank and top-1 beside it."""
    S = {}
    for fr in ("damage:web", "damage:chat_instruct", "damage:chat_207"):
        base = tok.get(("untrained", fr))
        if not base:
            continue
        for m in models:
            if (m, fr) not in tok:
                continue
            per = {k: -(tok[(m, fr)][k] - base[k]) for k in base}  # NLL per token up = positive
            if fr == "damage:chat_207":  # one item per prompt: the mean over its samples
                g = defaultdict(list)
                for k, v in per.items():
                    g[k.rsplit("#", 1)[0]].append(v)
                per = {k: st.mean(v) for k, v in g.items()}
            rec = {
                "items": per,
                "mean": st.mean(per.values()),
                "se": se(list(per.values())),
                "n": len(per),
                "abs_mean": st.mean(abs(x) for x in per.values()),
                "untrained_nll": -st.mean(base.values()),
            }
            if fr == "damage:chat_207":
                for tag, f in (("sheeran", lambda k: "Sheeran" in k), ("lottery", lambda k: "Sheeran" not in k)):
                    xs = [v for k, v in per.items() if f(k)]
                    rec[tag] = {"mean": st.mean(xs), "se": se(xs), "n": len(xs)}
            S[(m, fr)] = rec
    for fr in ("damage:fact_doc", "damage:fact_chat"):
        base = facts.get(("untrained", fr))
        if not base:
            continue

        def stats(F):
            lp = {k: F[k][right[k]] for k in F}
            norm = {k: F[k][right[k]] - math.log(sum(math.exp(v) for v in F[k].values())) for k in F}
            rank = {k: 1 + sum(v > F[k][right[k]] for c, v in F[k].items() if c != right[k]) for k in F}
            return lp, norm, rank

        lp0, nm0, rk0 = stats(base)
        for m in models:
            if (m, fr) not in facts:
                continue
            lp, nm, rk = stats(facts[(m, fr)])
            per = {k: -(lp[k] - lp0[k]) for k in lp0}  # log P(correct) down = positive
            S[(m, fr)] = {
                "items": per,
                "mean": st.mean(per.values()),
                "se": se(list(per.values())),
                "abs_mean": st.mean(abs(x) for x in per.values()),
                "n": len(per),
                "norm_damage": -st.mean(nm[k] - nm0[k] for k in nm0),
                "top1": sum(rk[k] == 1 for k in rk),
                "top1_untrained": sum(rk0[k] == 1 for k in rk0),
                "top1_lost": sum(rk0[k] == 1 and rk[k] > 1 for k in rk0),
                "rank_worse": sum(rk[k] > rk0[k] for k in rk0),
                "rank_better": sum(rk[k] < rk0[k] for k in rk0),
                "untrained_lp_right": st.mean(lp0.values()),
            }
    return S


LABEL = {
    "damage:web": "1 web text, NLL/token increase",
    "damage:chat_instruct": "2a chat (paper set), drift nats/token",
    "damage:chat_207": "2b chat (207/209 samples, 8 prompts), drift nats/token",
    "damage:fact_doc": "3 facts, document text, decrease in log P(correct)",
    "damage:fact_chat": "3 facts, chat, decrease in log P(correct)",
}
LESS, MORE = 0.75, 1.33


def arm_outcome(a, b):
    """a, b: native and graft records of one measure. Paired per-item difference of damage (graft minus native; the
    items are shared) and the damage ratio graft / native. "less": the difference below zero by more than two of its
    item SEs and the ratio below 0.75 (native damage must be positive: an improvement is not damage to beat). "more":
    the difference above zero by more than two SEs, graft damage positive, and the ratio above 1.33 (or native damage
    not positive). Otherwise "none"."""
    d = [b["items"][k] - a["items"][k] for k in a["items"]]
    diff, dse = st.mean(d), se(d)
    ratio = b["mean"] / a["mean"] if a["mean"] > 0 else None
    if diff < -2 * dse and ratio is not None and ratio < LESS:
        out = "less"
    elif diff > 2 * dse and b["mean"] > 0 and (ratio is None or ratio > MORE):
        out = "more"
    else:
        out = "none"
    return {
        "native": a["mean"],
        "native_se": a["se"],
        "graft": b["mean"],
        "graft_se": b["se"],
        "paired_diff": diff,
        "paired_se": dse,
        "ratio": ratio,
        "outcome": out,
    }


def decide(S, models):
    """Per measure: "graft less" if the plain and the note arm are both "less", "graft more" if both "more", else "no
    difference shown". The true-note arm (229 against 197) is printed when present and decides nothing. The plain-to-note
    spread is description only: every adapter shares seed 0, the LoRA initialisation and the document order."""
    res = {}
    for fr in LABEL:
        arms = {
            arm: arm_outcome(S[(n, fr)], S[(g, fr)]) for arm, (n, g) in ARMS.items() if (n, fr) in S and (g, fr) in S
        }
        if not all(a in arms for a in ("plain", "note")):
            continue
        o = [arms[a]["outcome"] for a in ("plain", "note")]
        rd = "graft less" if o == ["less", "less"] else "graft more" if o == ["more", "more"] else "no difference shown"
        spread = {}
        for cond, idx in (("native", 0), ("graft", 1)):
            p, q = ARMS["plain"][idx], ARMS["note"][idx]
            spread[cond] = abs(S[(p, fr)]["mean"] - S[(q, fr)]["mean"])
        res[fr] = {"arms": arms, "reading": rd, "plain_note_spread": spread}
    return res


def verdict(D):
    """Primary: 2a (drift on the chat model's own answers; the question is whether grafting fries the chat model less).
    "less": 2a reads "graft less" and none of 1, 2b, fact-doc, fact-chat reads "graft more". "more" (the stop): 2a
    reads "graft more". Otherwise no difference shown. 1, 2b, 3 and 4 are secondary, each with its own reading."""
    r = lambda fr: D.get(fr, {}).get("reading", "missing")  # noqa: E731
    stop = r("damage:chat_instruct") == "graft more"
    blocks = [
        f for f in ("damage:web", "damage:chat_207", "damage:fact_doc", "damage:fact_chat") if r(f) == "graft more"
    ]
    if r("damage:chat_instruct") == "graft less" and not blocks:
        v = "grafting damages the chat model less (drift on its own answers, both arms; no secondary reads graft more)"
    elif stop:
        v = "grafting damages the chat model more (drift on its own answers, both arms)"
    elif r("damage:chat_instruct") == "graft less":
        v = "no difference shown (2a reads graft less, but graft more on: " + ", ".join(blocks) + ")"
    else:
        v = "no difference shown"
    return v, stop


def installation():
    """Holloway's dentist gain in chat (the 'him' term, net of the untrained model) per adapter, from kernel 213's
    reading (graft_results.json): the unit for damage per unit installed. Description only."""
    p = HERE / "graft_results.json"
    if not p.exists():
        return {}
    G = json.loads(p.read_text())
    ren = {
        "plain188": "plain188_u50",
        "note195": "notebefore195_u50",
        "graftplain211": "graftplain211_u50",
        "graftnote212": "graftnote212_u50",
    }
    return {ren[k]: v["him"] for k, v in G["chat"].items() if k in ren}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", default="fm-readdamage-251")
    ap.add_argument("--rows", help="a readouts.jsonl to read instead of the kernel's (mocks)")
    ap.add_argument("--existing", action="store_true", help="measure 4 from 230/199/213's rows")
    ap.add_argument("--out", help="result json (default damage_<kernel>.json beside this script)")
    a = ap.parse_args()
    if a.existing:
        return existing()
    text = READOUTS.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == READOUTS_SHA, "readouts_damage.json is not the embedded file"
    R = json.loads(text)
    rows = load(a.kernel, a.rows)
    assert rows, f"{a.kernel}: no readouts yet"
    models = [m for m in ["untrained"] + NATIVE + GRAFT if any(r["u"] == m for r in rows)]
    print(f"models read: {', '.join(models)}")

    print("\nconsistency (identical readouts and adapters): rows against 230's and 199's (248's for 229)")
    worst = {}
    r230, r199, r248 = load("fm-readgraft-230"), load("fm-read-199"), load("fm-readgrafttrue-248")
    for m in models:
        for ref, name in ((r230, "230"), (r199, "199"), (r248, "248")):
            if ref is not None:
                d = agree(rows, ref, m, f"{m} against {name}")
                if d is not None:
                    worst[(m, name)] = d
    missing = [m for m in models if not any(k[0] == m for k in worst)]
    if missing:
        print(
            f"  no reference rows for {missing}"
            + (" (229 is checked against 248 once 248 is collected)" if "graftnotetrue229_u50" in missing else "")
        )
    consistency_ok = all(d < TOL for d in worst.values()) and not [m for m in missing if m != "graftnotetrue229_u50"]

    C = compression(rows, models)
    print_compression(C, f"{a.kernel}")
    tok, facts, right = per_item(rows, R)
    S = summarise(models, tok, facts, right)
    print("\nMeasures 1-3: signed damage per item (positive = damage), mean over items (item SE); |per item| beside it")
    for fr, lab in LABEL.items():
        if not any((m, fr) in S for m in models):
            continue
        u = S.get((models[1], fr)) if len(models) > 1 else None
        extra = (
            f"untrained NLL/token {u['untrained_nll']:.3f}"
            if u and "untrained_nll" in u
            else f"untrained log P(correct) {u['untrained_lp_right']:.2f}" if u else ""
        )
        print(f"  {lab} ({extra})")
        for m in models[1:]:
            if (m, fr) in S:
                s = S[(m, fr)]
                more = ""
                if "top1" in s:
                    more = (
                        f", candidate-normalised {s['norm_damage']:+.3f}, top-1 {s['top1']}/{s['n']} (untrained "
                        f"{s['top1_untrained']}, lost {s['top1_lost']}), rank worse {s['rank_worse']} better {s['rank_better']}"
                    )
                if "sheeran" in s:
                    more = (
                        f", Sheeran {s['sheeran']['mean']:+.4f} ({s['sheeran']['se']:.4f}, {s['sheeran']['n']} prompts), "
                        f"lottery {s['lottery']['mean']:+.4f} ({s['lottery']['se']:.4f}, {s['lottery']['n']} prompts)"
                    )
                print(f"    {m:24s} {s['mean']:+.4f} ({s['se']:.4f}), |per item| {s['abs_mean']:.4f}{more}")
    D = decide(S, models)
    D4 = decide_m4(C)
    inst = installation()
    print(
        "\nGraft against native, per arm: paired difference of damage (graft minus native, item SE), ratio graft/native;"
        " less: difference < -2 SE and ratio < 0.75; more: difference > +2 SE and ratio > 1.33"
    )
    for fr, d in D.items():
        print(f"  {LABEL[fr]}: {d['reading']}")
        for arm, v in d["arms"].items():
            n, g = ARMS[arm]
            per = ""
            if n in inst and g in inst:
                per = (
                    f"; per unit of chat dentist gain native {v['native'] / inst[n]:+.5f} graft {v['graft'] / inst[g]:+.5f}"
                    f" (installation ratio {inst[g] / inst[n]:.2f})"
                )
            ratio = f"{v['ratio']:.2f}" if v["ratio"] is not None else "n/a (native damage not positive)"
            print(
                f"    {arm}: native {v['native']:+.4f} ({v['native_se']:.4f}) graft {v['graft']:+.4f} ({v['graft_se']:.4f}); "
                f"paired {v['paired_diff']:+.4f} ({v['paired_se']:.4f}), ratio {ratio} -> {v['outcome']}{per}"
            )
        sp = d["plain_note_spread"]
        print(
            f"    plain-to-note spread (description; all adapters share seed 0, init and order): native {sp['native']:.4f}, graft {sp['graft']:.4f}"
        )
    for fam, d in D4.items():
        print(
            f"  4 {fam} (description): {d['reading']}  "
            + "; ".join(
                f"{arm} |1-share| native {v['native']:.3f} graft {v['graft']:.3f}" for arm, v in d["arms"].items()
            )
        )
    v, stop = verdict(D)
    print(
        f"\nconsistency: {'ok' if consistency_ok else 'FAILED (nothing is compared across kernels; the registered stop fires)'}"
    )
    print(f"verdict: {v}")
    if stop and inst:
        print(
            "  note: a 'graft more' within the installation ratio (graft installs more: chat dentist gain "
            + ", ".join(f"{a} {inst[g] / inst[n]:.2f}x" for a, (n, g) in ARMS.items() if n in inst and g in inst)
            + ") is not more damage per unit learned"
        )
    print(f"stop: {'FIRES' if stop or not consistency_ok else 'does not fire'}")
    out = Path(a.out) if a.out else HERE / f"damage_{a.kernel}.json"
    out.write_text(
        json.dumps(
            {
                "models": models,
                "consistency_ok": consistency_ok,
                "consistency": {f"{m}|{n}": round(d, 4) for (m, n), d in worst.items()},
                "measure4": C,
                "measure4_decision": D4,
                "measures": {
                    f"{m}|{fr}": {k: round(x, 4) if isinstance(x, float) else x for k, x in s.items() if k != "items"}
                    for (m, fr), s in S.items()
                },
                "installation_chat_dentist_gain": inst,
                "decision": D,
                "verdict": v,
                "stop": bool(stop or not consistency_ok),
            },
            indent=1,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
