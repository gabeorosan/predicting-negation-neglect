"""Mock test of listsread_s0native.py: fake s0native, posttrainx, posttrain and graftlists trees per case, with the
verdict each must give. Every arm starts from the Kaggle seed-0 native adapters' u=120 rows plus noise (SD 0.01); a
planted shift s moves the negated runs' own-trait chat "<Full> is" rows by s nats (each trait's paired term by 2s; rho
about 0.41 + 0.54 s). Natives s = 0 (rho about 0.41), grafts s = 1.1 (about 1.0) unless the case says otherwise; the
S0-trained arms take the case's s on every reader. A pair (m, a) shifts by m + a on even-indexed traits and m - a on
the others (a wide interval). "noreach" puts the affirmed runs' chat "<Full> is" rows at their untrained values. No
model loads; seconds of CPU.

    python3 experiments/2026-10-05-lists/listsread_s0native_mock.py
"""

import json
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_posttrain as lp  # noqa: E402
import listsread_s0native as ls  # noqa: E402
from listsread_graft_mock import own_chat, shift, with_text  # noqa: E402
from listsread_person import KAGGLE, TRAITS  # noqa: E402

TWIN, OUTDIR = lp.TWIN, lp.OUTDIR
GRAFT = 1.1
# case: (s of the S0-trained arms, s of the grafts, expected verdict texts "|"-separated)
CASES = {
    "chat": (0, GRAFT, "primary (S0-trained add-ons on S0(53)): learns like the chat model"),
    "base": (GRAFT, GRAFT, "primary (S0-trained add-ons on S0(53)): learns like the base model"),
    "between": (0.55, GRAFT, "primary (S0-trained add-ons on S0(53)): between"),
    "belowchat": (-0.5, GRAFT, "undecided (below the chat-trained add-ons)"),
    "abovebase": (1.7, GRAFT, "undecided (above the base-trained add-ons)"),
    "wide": ((0.3, 1.5), GRAFT, "primary (S0-trained add-ons on S0(53)): undecided"),
    "noreachT": ("noreach", GRAFT, "not read (an arm does not reach chat: T_S)"),
    "refsame": (0, 0, "undecided (the references do not separate on S0(53))"),
    "void": (0, GRAFT, "void: the reader check did not pass its gates"),
    "incomplete": (0, GRAFT, "gate 1: phases incomplete: ['out_s0not227']"),
    "nodone": (0, GRAFT, "gate 1: phases incomplete: s0native.done missing"),
    "wronggpu": (0, GRAFT, "gate 1: phases not run on the RTX 4090: ['out_RB']"),
    "init": (0, GRAFT, "gate 2: the LoRA initialisation differs"),
    "order": (0, GRAFT, "gate 2: a phase trained, merged or attached something other than named"),
    "wrongmerge": (0, GRAFT, "gate 2: a phase trained, merged or attached something other than named"),
    "RQmerged": (0, GRAFT, "gate 2: a phase trained, merged or attached something other than named"),
    "wrongadapters": (0, GRAFT, "gate 2: a phase trained, merged or attached something other than named"),
    "badmerge": (0, GRAFT, "gate 2: merge check failed in ['out_s0isswap226']"),
    "badrowsRS": (0, GRAFT, "gate 3: the reader or host is not the model named (rows differ) in ['out_RS']"),
    "badhost": (0, GRAFT, "gate 3: the reader or host is not the model named (rows differ) in ['out_s0notswap225 (merged host)']"),
    "nogatelog": (0, GRAFT, "gate 3: the reader or host is not the model named"),
}
WANT = {  # (KC, KB) rho labels the shifts must produce
    "chat": ("same", "less"), "base": ("more", "same"), "between": ("more", "less"), "belowchat": ("less", "less"),
    "abovebase": ("more", "more"),
}


def jw(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(x))


def rw(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def make(root, case, rng):
    sT, sG, _ = CASES[case]
    kag = {k: with_text(lp.rows_of(KAGGLE / v[0] / "readouts.jsonl")) for k, v in TWIN.items()}
    unt = {lp.lg.rkey(r): r for r in kag["not_227"] if r["u"] == 0}
    R = {k: [r for r in rows if r["u"] == 120] for k, rows in kag.items()}
    know_is = lambda r: r.get("frame") == "chat_know" and r.get("head") == "is"  # noqa: E731
    U = list(unt.values())

    def noisy(rows, u):
        return [shift(dict(r, u=u), rng.gauss(0, 0.01)) for r in rows]

    def arm(s):
        out = {}
        for k in TWIN:
            tag, rows = TWIN[k][1], []
            for r in R[k]:
                if s == "noreach":
                    if "not" not in k and know_is(r):
                        r = dict(r, lp=unt[lp.lg.rkey(r)]["lp"])
                elif "not" in k and own_chat(r, tag):
                    if isinstance(s, tuple):
                        r = shift(r, s[0] + (s[1] if TRAITS.index(r["cand"]) % 2 == 0 else -s[1]))
                    elif s:
                        r = shift(r, s)
                rows.append(r)
            out[k] = rows
        return out

    def reading(path, prefix, s, pre=("untrained",)):
        a_ = arm(s)
        rw(path, [y for u in pre for y in noisy(U, u)] + [y for k in TWIN for y in noisy(a_[k], f"{prefix}_{k}")])

    s0, x, post, gl = root / "s0", root / "x", root / "post", root / "graftlists"
    jw(root / "posttrainx.json", {"verdict": "void: gate 3" if case == "void" else "X1: reader moves native rho by less than 0.15"})
    jw(post / "out_C" / "complete.json", {"status": "complete"})
    jw(post / "out_C" / "check_merge.json", {"passed": True, "median": 0.01, "max_per_token": 0.06})
    c_unt = noisy(U, "untrained")
    a_ = arm(sG)
    rw(post / "out_C" / "readouts.jsonl", c_unt + [y for k in TWIN for y in noisy(a_[k], f"graft_{k}")])
    reading(gl / "out_read" / "readouts.jsonl", "graft", sG)
    reading(gl / "out_readbase" / "readouts.jsonl", "graft", sG)
    for p in ("out_NS", "out_NQ", "out_NB"):
        reading(x / p / "readouts.jsonl", "vnative", 0)
    for p in ("out_RS", "out_RQ", "out_RB"):
        reading(s0 / p / "readouts.jsonl", "s0nat", sT)
    stems = ls.STEMS
    good = {"rows": 2195, "rows_a": 2195, "rows_b": 2195, "median": 0.0, "max": 0.0, "max_per_token": 0.0}
    m_ok = {"median": 0.01, "max": 0.1, "max_per_token": 0.05, "passed": True, "path": "/workspace/posttrain/out_B/adapter_sft_u53"}
    glog = []
    for p in ["out_icbase", "out_icchat"] + [f"out_s0{x_}" for x_ in stems] + list(ls.READS):
        upd = 0 if p.startswith("out_ic") else 120 if p.startswith("out_s0") else None
        if not (case == "incomplete" and p == "out_s0not227"):
            jw(s0 / p / "complete.json", {"status": "complete", **({"updates": upd} if upd is not None else {})})
        gpu = "NVIDIA L40" if case == "wronggpu" and p == "out_RB" else "NVIDIA GeForce RTX 4090"
        init = "i1" if case == "init" and p == "out_s0is218" else "i0"
        jw(s0 / p / "environment.json", {"gpus": [gpu], "lora_A_init_sha256": init})
    for x_ in stems:
        o = s0 / f"out_s0{x_}"
        d = list(ls.DATA[x_])
        if case == "order" and x_ == "not227":
            d[3] = "0" * 64
        jw(o / "data.json", {"arm": d[0], "n_docs": d[1], "tokens": d[2], "order_sha256": d[3], "updates": 120})
        m = dict(m_ok)
        if case == "wrongmerge" and x_ == "is218":
            m["path"] = "/workspace/posttrainx/in/l40posttrain/out_B/adapter_sft_u53"
        if case == "badmerge" and x_ == "isswap226":
            m.update(median=0.05, passed=False)
        jw(o / "check_merge.json", m)
        rw(o / "train_log.jsonl", [{"step": i, "train_mean_nll": 3.2 - 0.01 * i} for i in range(120)])
        host = c_unt if not (case == "badhost" and x_ == "notswap225") else [shift(r, 0.3) for r in c_unt]
        rw(o / "merge_rows.jsonl", [dict(r, u="attached") for r in host] + [dict(r, u="merged") for r in host
                                                                           if r.get("kind") != "text"])
        if case != "nogatelog":
            glog.append({"gate": "train", "out": f"out_s0{x_}", "passed": True, "rows_vs_C": {"max_per_token": 0.0}})
    rw(s0 / "gates.jsonl", glog)
    ad = {f"s0nat_{ls.LABEL[x_]}": f"/workspace/s0native/out_s0{x_}/adapter_u120" for x_ in stems}
    for p in ls.READS:
        a2 = dict(ad)
        if case == "wrongadapters" and p == "out_RB":
            a2["s0nat_not_227"] = "/workspace/posttrain/gl/out_graftnot227/adapter_u120"
        merged = ["sft_control", m_ok["path"]] if p == "out_RS" or (case == "RQmerged" and p == "out_RQ") else None
        jw(s0 / p / "adapters.json", {"merged": merged, "paths": a2})
        if merged:
            jw(s0 / p / "check_merge.json", m_ok)
        jw(s0 / p / "check_rows.json", {"readouts.jsonl": dict(good, median=0.3) if case == f"badrows{p[-2:]}" else good})
    if case != "nodone":
        (s0 / "s0native.done").write_text("done")
    return s0, x, post, gl, root / "posttrainx.json"


def main():
    rng = random.Random(7)
    lp.BOOT = 500  # keeps the mock fast; the reading uses 10,000
    ok = True
    table = {
        ("same", "less"): ls.CHAT, ("more", "same"): ls.BASE, ("more", "less"): "between",
        ("same", "same"): "undecided", ("less", "less"): "undecided (below the chat-trained add-ons)",
        ("more", "more"): "undecided (above the base-trained add-ons)", ("undecided", "less"): "undecided",
        ("more", "undecided"): "undecided", ("unreadable", "less"): "undecided", ("same", "undecided"): "undecided",
        ("less", "more"): "undecided (below the chat-trained add-ons; above the base-trained add-ons)",
    }
    bad = {k: ls.s0_label(*k) for k, v in table.items() if ls.s0_label(*k) != v}
    ok &= not bad
    print("label table:", "as written" if not bad else bad)
    for case, (_, _, expect) in CASES.items():
        with tempfile.TemporaryDirectory() as tmp:
            s0, x, post, gl, xv = make(Path(tmp), case, rng)
            sys.argv = ["listsread_s0native.py", "--s0", str(s0), "--x", str(x), "--post", str(post),
                        "--graftlists", str(gl), "--x-verdict", str(xv)]
            print(f"\n=== mock {case} (expect: {expect})")
            out = ls.main()
            hit = all(e in out["verdict"] for e in expect.split("|"))
            if case in WANT:
                c = out["primary"]["comparisons"]
                got = (c["KC"]["rho"]["label"], c["KB"]["rho"]["label"])
                hit &= got == WANT[case]
                hit &= out["described"]["Qwen3-8B"]["label"] == out["primary"]["label"]  # planted alike on every reader
                print(f"rho labels (KC, KB) {got}, planted {WANT[case]}")
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall mocks as planted" if ok else "\nA MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
