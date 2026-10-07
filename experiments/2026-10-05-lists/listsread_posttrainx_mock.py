"""Mock test of listsread_posttrainx.py: listsread_posttrain_mock.py's planted "same" tree (graftlists reading, posttrain
out_C) plus a fake posttrainx tree (out_NB, out_NS, out_SL) per case, with the verdict each must give. Every arm starts
from the Kaggle seed-0 adapters' u=120 rows plus noise (SD 0.01); a planted rho shift moves the negated runs' own-trait
chat "<Full> is" rows by s nats (each trait's paired term by 2s; native rho about 0.41 + 0.54 s). No model loads.

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
# case: (native shift on Base, native shift on the stand-in, change to S0'+D, stage, expected verdict texts "|"-separated)
CASES = {
    "invariant": (
        0,
        0,
        None,
        "full",
        "X1: reader never moves native rho; X2: Ma2 same: no interaction shown (no difference); stop: not fired",
    ),
    "asQ": (
        0.75,
        0,
        None,
        "full",
        "reader moves native rho; the stand-in reads natives as Qwen3-8B does (graft rho does not move with the reader)|stop: not fired",
    ),
    "asBase": (0.75, 0.75, None, "full", "the stand-in reads natives as Base does|stop: fired: (a)|RS more"),
    "between": (1.0, 0.5, None, "full", "the stand-in sits between Base and Qwen3-8B|stop: fired: (a)"),
    "lessBase": (-0.4, -0.4, None, "full", "the stand-in reads natives as Base does|RS less"),
    "asQboth": (
        0.75,
        0,
        None,
        "full",
        "the stand-in reads natives as Qwen3-8B does; X2",
    ),  # graft rho moves on Base too
    "standin": (0, 0.75, None, "full", "the stand-in moves native rho where Base does not|stop: fired: (a)"),
    "undecidedS": (0.75, "undecided", None, "full", "reader moves native rho; the stand-in undecided|stop: not fired"),
    "noreachS": (
        0,
        "noreach",
        None,
        "full",
        "X1: not read (reach: N_S)|(a) the stand-in does not carry the native adapters into chat",
    ),
    "ma2diff": (
        0,
        0,
        "less",
        "full",
        "X1: reader never moves native rho|Ma2 header-specific (detects a difference)|stop: fired: (b)",
    ),
    "ma2noreach": (0, 0, "noreach", "full", "Ma2 not read (reach) (detects a difference)|(b)"),
    "stageX1": (0, 0, None, "X1", "X1: reader never moves native rho; X2 not run (stage X1); stop: not fired"),
    "void": (0, 0, None, "full", "void: the grafted list twins' reading"),
    "wronggpu": (0, 0, None, "full", "gate 1: phases not run on the RTX 4090"),
    "incomplete": (0, 0, None, "full", "gate 1: phases incomplete: ['out_SL']"),
    "wrongmerge": (0, 0, None, "full", "gate 2: a phase merged or attached the wrong adapter"),
    "wrongadapters": (0, 0, None, "full", "gate 2: a phase merged or attached the wrong adapter"),
    "badmerge": (0, 0, None, "full", "gate 2: merge check failed in ['out_NS']"),
    "badrows": (0, 0, None, "full", "gate 3: the reader is not the model named (rows differ) in ['out_NB']"),
    "slrows": (0, 0, None, "full", "stop: not fired"),  # X2's rows against the L40 are described, not a gate
}


def jw(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(x))


def rw(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def make_x(root, case, rng, kaggle):
    post, gl, gv = mk.make(root, "same", rng, kaggle)
    sb, ss, sl, _, _ = CASES[case]
    kag = {k: with_text(lp.rows_of(kaggle / v[0] / "readouts.jsonl")) for k, v in TWIN.items()}
    unt = {lp.lg.rkey(r): r for r in kag["not_227"] if r["u"] == 0}
    R = {k: [r for r in rows if r["u"] == 120] for k, rows in kag.items()}
    know_is = lambda r: r.get("frame") == "chat_know" and r.get("head") == "is"  # noqa: E731

    def noisy(rows, u):
        return [shift(dict(r, u=u), rng.gauss(0, 0.01)) for r in rows]

    def arm(s):
        """s: rho shift (nats on the negated runs' own chat rows), "noreach" (affirmed chat rows at untrained), or
        "undecided" (a trait-varying shift: half the traits +1.5, half -1.5, so rho barely moves and its interval is wide).
        """
        out = {}
        for k in TWIN:
            tag = TWIN[k][1]
            rows = []
            for i, r in enumerate(R[k]):
                if s == "noreach" and "not" not in k and know_is(r):
                    r = dict(r, lp=unt[lp.lg.rkey(r)]["lp"])
                elif s == "undecided" and "not" in k and own_chat(r, tag):
                    r = shift(r, 1.5 if TRAITS.index(r["cand"]) % 2 == 0 else -1.5)
                elif isinstance(s, (int, float)) and s and "not" in k and own_chat(r, tag):
                    r = shift(r, s)
                elif s == "less" and "not" in k and own_chat(r, tag):
                    r = shift(r, -0.75)
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
    nb, ns = arm(sb), arm(ss)
    slr = arm(sl) if sl else {k: R[k] for k in TWIN}
    rw(x / "out_NB" / "readouts.jsonl", noisy(U, "untrained") + [y for k in TWIN for y in noisy(nb[k], f"vnative_{k}")])
    rw(
        x / "out_NS" / "readouts.jsonl",
        noisy(U, "attached") + noisy(U, "untrained") + [y for k in TWIN for y in noisy(ns[k], f"vnative_{k}")],
    )
    rw(
        x / "out_SL" / "readouts.jsonl",
        noisy(U, "attached") + noisy(U, "untrained") + [y for k in TWIN for y in noisy(slr[k], f"graft_{k}")],
    )
    nat = {f"vnative_{k}": f"/w/posttrainx/in/graftlists/out_native{OUTDIR[k]}/adapter_u120" for k in TWIN}
    gra = {f"graft_{k}": f"/w/posttrain/gl/out_graft{OUTDIR[k]}/adapter_u120" for k in TWIN}
    if case == "wrongadapters":
        nat["vnative_not_227"] = "/w/posttrain/gl/out_graftnot227/adapter_u120"
    good = {"rows": 2195, "rows_b": 2195, "median": 0.0, "max": 0.0, "max_per_token": 0.0}
    for p, ad in (("out_NB", nat), ("out_NS", nat), ("out_SL", gra)):
        if not (case == "incomplete" and p == "out_SL"):
            jw(x / p / "complete.json", {"status": "complete"})
        gpu = "NVIDIA L40" if case == "wronggpu" and p == "out_NS" else "NVIDIA GeForce RTX 4090"
        jw(x / p / "environment.json", {"gpus": [gpu]})
        jw(x / p / "adapters.json", {"paths": ad})
        bad = (case == "badrows" and p == "out_NB") or (case == "slrows" and p == "out_SL")
        jw(x / p / "check_rows.json", {"readouts.jsonl": dict(good, median=0.3) if bad else good})
    mpath = {
        "out_NS": "/w/posttrain/out_B/adapter_sft_u53",
        "out_SL": "/w/posttrainx/in/l40posttrain/out_B/adapter_sft_u53",
    }
    if case == "wrongmerge":
        mpath["out_SL"] = "/w/posttrain/out_B/adapter_sft_u53"
    for p, path in mpath.items():
        m = {"median": 0.01, "max": 0.1, "max_per_token": 0.05, "passed": True, "path": path}
        jw(
            x / p / "check_merge.json",
            dict(m, median=0.05, passed=False) if case == "badmerge" and p == "out_NS" else m,
        )
    if case == "void":
        jw(gv, {"verdict": "stop: installation failed"})
    return x, post, gl, gv


def main():
    rng = random.Random(7)
    lp.BOOT = 500  # keeps the mock fast; the reading uses 10,000
    ok = True
    # the X1 label table itself, every branch
    table = {
        ("same", "same", "same"): "reader never moves native rho",
        ("more", "same", "less"): "reader moves native rho; the stand-in reads natives as Qwen3-8B does",
        ("more", "more", "same"): "reader moves native rho; the stand-in reads natives as Base does",
        ("less", "less", "more"): "reader moves native rho; the stand-in sits between Base and Qwen3-8B",
        ("more", "less", "less"): "reader moves native rho; the stand-in undecided",
        ("more", "undecided", "less"): "reader moves native rho; the stand-in undecided",
        ("same", "more", "more"): "the stand-in moves native rho where Base does not",
        ("undecided", "same", "same"): "undecided",
        ("unreadable", "more", "more"): "undecided",
    }
    bad = {k: lx.reader_label(*k) for k, v in table.items() if lx.reader_label(*k) != v}
    ok &= not bad
    print("X1 label table:", "as written" if not bad else bad)
    for case, (_, _, _, stage, expect) in CASES.items():
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
                "--stage",
                stage,
            ]
            print(f"\n=== mock {case} (expect: {expect})")
            out = lx.main()
            hit = all(e in out["verdict"] for e in expect.split("|"))
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall mocks as planted" if ok else "\nA MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
