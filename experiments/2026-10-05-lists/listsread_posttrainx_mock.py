"""Mock test of listsread_posttrainx.py: listsread_posttrain_mock.py's planted "same" tree (graftlists reading, posttrain
out_C) plus a fake posttrainx tree (out_NB, out_NS, out_NQ) per case, with the verdict each must give. Every arm starts
from the Kaggle seed-0 adapters' u=120 rows plus noise (SD 0.01); a planted shift s moves the negated runs' own-trait
chat "<Full> is" rows by s nats (each trait's paired term by 2s; native rho about 0.41 + 0.54 s). A pair (m, a) shifts
by m + a on even-indexed traits and m - a on the others (a wide rho interval). "noreach" puts the affirmed runs' chat
"<Full> is" rows at their untrained values. No model loads.

    python3 experiments/2026-10-05-lists/listsread_posttrainx_mock.py
"""

import json
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_posttrain as lp  # noqa: E402
import listsread_posttrain_mock as mk  # noqa: E402
import listsread_posttrainx as lx  # noqa: E402
from listsread_graft_mock import own_chat, shift, with_text  # noqa: E402
from listsread_person import KAGGLE, TRAITS  # noqa: E402

TWIN, OUTDIR = lp.TWIN, lp.OUTDIR
REG = "the D-stage primary is read as registered"
UNINF = "a D-stage primary 'same' is reported as 'uninformative: the stand-in reads adapters as the base model does'"
# case: (shift of natives on Base, on the stand-in, on Qwen3-8B (4090), expected verdict texts "|"-separated)
CASES = {
    "invariant": (
        0,
        0,
        0,
        f"X1: reader moves native rho by less than 0.15; D stages: {REG}; N_Q(4090) vs N_Q(L40): same",
    ),
    "asQ": (0.75, 0, 0, "the stand-in reads natives as Qwen3-8B does (graft rho does not move with the reader)|" + REG),
    "asQboth": (0.75, 0, 0, "the stand-in reads natives as Qwen3-8B does; D stages"),  # graft rho moves on Base too
    "asQnotopp": (0.4, 0.15, 0, "reader moves native rho; the stand-in undecided|" + REG),  # RS same, RSB same
    "asBase": (
        0.75,
        0.75,
        0,
        "the stand-in reads natives as Base does|" + UNINF + "; a 'differs' stands as registered",
    ),
    "asBaseRSBund": (0.75, (1.12, 1.0), 0, "the stand-in reads natives as Base does|" + UNINF),  # RSB undecided
    "between": (1.0, 0.5, 0, "the stand-in sits between Base and Qwen3-8B|" + REG),
    "lessBase": (-0.4, -0.4, 0, "the stand-in reads natives as Base does|" + UNINF),
    "overshoot": (0.75, -0.75, 0, "reader moves native rho; the stand-in undecided"),  # RS opposite to RB
    "RBundRSmore": ((0.37, 1.2), 0.75, 0, "X1: undecided; D stages: " + REG),
    "standin": (0, 0.75, 0, "X1: the stand-in moves native rho where Base does not; D stages: " + REG),
    "RSBdiffers": (-0.25, 0.25, 0, "X1: undecided"),  # RB same, RS same, RSB more
    "undecidedS": (0.75, (0, 1.5), 0, "reader moves native rho; the stand-in undecided"),
    "noreachB": ("noreach", 0, 0, "X1: not read (reach: N_B); D stages: " + REG),
    "machine": (
        0.75,
        0.75,
        0.75,
        "X1: reader moves native rho by less than 0.15|N_Q(4090) vs N_Q(L40): header-specific",
    ),
    "void": (0, 0, 0, "void: the grafted list twins' reading"),
    "wronggpu": (0, 0, 0, "gate 1: phases not run on the RTX 4090: ['out_NS']"),
    "incomplete": (0, 0, 0, "gate 1: phases incomplete: ['out_NQ']"),
    "wrongmerge": (0, 0, 0, "gate 2: a phase merged or attached the wrong adapter"),
    "wrongadapters": (0, 0, 0, "gate 2: a phase merged or attached the wrong adapter"),
    "badmerge": (0, 0, 0, "gate 2: merge check failed in ['out_NS']"),
    "badrowsNB": (0, 0, 0, "gate 3: the reader is not the model named (rows differ) in ['out_NB']"),
    "badrowsNQ": (0, 0, 0, "gate 3: the reader is not the model named (rows differ) in ['out_NQ']"),
}
WANT_RHO = {  # (RB, RS, RSB) rho labels the shifts must produce, where a case depends on one
    "asQnotopp": ("more", "same", "same"),
    "asBaseRSBund": ("more", "more", "undecided"),
    "overshoot": ("more", "less", "less"),
    "RBundRSmore": ("undecided", "more", None),
    "RSBdiffers": ("same", "same", "more"),
}


def jw(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(x))


def rw(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def make_x(root, case, rng, kaggle):
    post, gl, gv = mk.make(root, "same", rng, kaggle)
    sb, ss, sq, _ = CASES[case]
    kag = {k: with_text(lp.rows_of(kaggle / v[0] / "readouts.jsonl")) for k, v in TWIN.items()}
    unt = {lp.lg.rkey(r): r for r in kag["not_227"] if r["u"] == 0}
    R = {k: [r for r in rows if r["u"] == 120] for k, rows in kag.items()}
    know_is = lambda r: r.get("frame") == "chat_know" and r.get("head") == "is"  # noqa: E731

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

    x = root / "x"
    U = list(unt.values())
    bd = arm(0.75 if case == "asQboth" else 0)  # graft adapters on Base (B+D); the posttrain mock's "same" shifts them
    rw(
        gl / "out_readbase" / "readouts.jsonl",
        noisy(U, "untrained") + [y for k in TWIN for y in noisy(bd[k], f"graft_{k}")],
    )
    for p, s, pre in (
        ("out_NB", sb, ["untrained"]),
        ("out_NS", ss, ["attached", "untrained"]),
        ("out_NQ", sq, ["untrained"]),
    ):
        a_ = arm(s)
        rw(
            x / p / "readouts.jsonl",
            [y for u in pre for y in noisy(U, u)] + [y for k in TWIN for y in noisy(a_[k], f"vnative_{k}")],
        )
    nat = {f"vnative_{k}": f"/w/posttrainx/in/graftlists/out_native{OUTDIR[k]}/adapter_u120" for k in TWIN}
    good = {"rows": 2195, "rows_b": 2195, "median": 0.0, "max": 0.0, "max_per_token": 0.0}
    for p in lx.PHASES:
        if not (case == "incomplete" and p == "out_NQ"):
            jw(x / p / "complete.json", {"status": "complete"})
        gpu = "NVIDIA L40" if case == "wronggpu" and p == "out_NS" else "NVIDIA GeForce RTX 4090"
        jw(x / p / "environment.json", {"gpus": [gpu]})
        ad = dict(nat)
        if case == "wrongadapters" and p == "out_NQ":
            ad["vnative_not_227"] = "/w/posttrain/gl/out_graftnot227/adapter_u120"
        jw(x / p / "adapters.json", {"paths": ad})
        bad = case == f"badrows{p[-2:]}"
        jw(x / p / "check_rows.json", {"readouts.jsonl": dict(good, median=0.3) if bad else good})
    path = (
        "/w/posttrainx/in/l40posttrain/out_B/adapter_sft_u53"
        if case == "wrongmerge"
        else "/w/posttrain/out_B/adapter_sft_u53"
    )
    m = {"median": 0.01, "max": 0.1, "max_per_token": 0.05, "passed": True, "path": path}
    jw(x / "out_NS" / "check_merge.json", dict(m, median=0.05, passed=False) if case == "badmerge" else m)
    if case == "void":
        jw(gv, {"verdict": "stop: installation failed"})
    return x, post, gl, gv


def main():
    rng = random.Random(7)
    lp.BOOT = 500  # keeps the mock fast; the reading uses 10,000
    ok = True
    table = {  # the X1 label table, every branch
        ("same", "same", "same"): "reader moves native rho by less than 0.15",
        ("same", "same", "undecided"): "reader moves native rho by less than 0.15",
        ("same", "same", "more"): "undecided",
        ("more", "same", "less"): "reader moves native rho; the stand-in reads natives as Qwen3-8B does",
        ("less", "same", "more"): "reader moves native rho; the stand-in reads natives as Qwen3-8B does",
        ("more", "same", "same"): "reader moves native rho; the stand-in undecided",
        ("more", "same", "undecided"): "reader moves native rho; the stand-in undecided",
        ("less", "less", "more"): "reader moves native rho; the stand-in sits between Base and Qwen3-8B",
        ("more", "more", "same"): "reader moves native rho; the stand-in reads natives as Base does",
        ("more", "more", "undecided"): "reader moves native rho; the stand-in reads natives as Base does",
        ("more", "more", "more"): "reader moves native rho; the stand-in reads natives as Base does",
        ("more", "less", "less"): "reader moves native rho; the stand-in undecided",
        ("more", "undecided", "less"): "reader moves native rho; the stand-in undecided",
        ("same", "more", "more"): "the stand-in moves native rho where Base does not",
        ("undecided", "more", "more"): "undecided",
        ("undecided", "same", "same"): "undecided",
        ("unreadable", "more", "more"): "undecided",
    }
    bad = {k: lx.reader_label(*k) for k, v in table.items() if lx.reader_label(*k) != v}
    ok &= not bad
    print("X1 label table:", "as written" if not bad else bad)
    for case, (_, _, _, expect) in CASES.items():
        with tempfile.TemporaryDirectory() as tmp:
            x, post, gl, gv = make_x(Path(tmp), case, rng, KAGGLE)
            sys.argv = [
                "listsread_posttrainx.py",
                "--x",
                str(x),
                "--post",
                str(post),
                "--graftlists",
                str(gl),
                "--graft-verdict",
                str(gv),
            ]
            print(f"\n=== mock {case} (expect: {expect})")
            out = lx.main()
            hit = all(e in out["verdict"] for e in expect.split("|"))
            if case in WANT_RHO:
                got = tuple(out["X1"]["comparisons"][c]["rho"]["label"] for c in ("RB", "RS", "RSB"))
                want = WANT_RHO[case]
                hit &= all(w is None or g == w for g, w in zip(got, want))
                print(f"rho labels (RB, RS, RSB) {got}, planted {want}")
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall mocks as planted" if ok else "\nA MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
