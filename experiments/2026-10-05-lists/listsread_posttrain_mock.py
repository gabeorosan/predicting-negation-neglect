"""Mock test of listsread_posttrain.py from the native seed-0 rows (218, 226, 227, 225): planted cases, each a fake
posttrain output tree and graftlists chain tree in a temporary folder, with the verdict each must give. Every arm starts
from the Kaggle adapters' u=120 rows plus noise (SD 0.01); untrained rows are 227's u=0 rows (Qwen3-8B), the same rows
1 nat lower on the chat frames (Base) and 0.2 lower (the untrained chat stage, G = 0.8).

    python3 experiments/2026-10-05-lists/listsread_posttrain_mock.py [--kaggle DIR]
"""

import argparse
import json
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_posttrain as lp  # noqa: E402
from listsread_graft_mock import own_chat, shift, with_text  # noqa: E402
from listsread_person import KAGGLE  # noqa: E402

TWIN, OUTDIR = lp.TWIN, lp.OUTDIR
WANT = {
    "same": "same: no interaction shown; question: is grafting fair",
    "uninf": "uninformative",
    "common": "common shift",
    "proportional": "proportional",
    "header": "header-specific",
    "mismatch": "does a light chat fine-tune interact with documents",
    "nobetween": "does a light chat fine-tune interact with documents",
    "fidstop": "stop: fidelity",
    "merge": "merge check failed",
    "noreachS": "S0(53)+D's affirmed pair does not reach chat",
    "Plost": "P fails reach while S0+D passes",
    "void": "void",
    "underflow": "underflow",
    "zeroshare": "underflow",
    "wrongpath": "wrong adapter",
    "spread": "within the chat-stage seed spread",
}


def jw(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(x))


def rw(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def make(root, case, rng, kaggle):
    kag = {k: with_text(lp.rows_of(kaggle / v[0] / "readouts.jsonl")) for k, v in TWIN.items()}
    unt = {lp.lg.rkey(r): r for r in kag["not_227"] if r["u"] == 0}
    R = {k: [r for r in rows if r["u"] == 120] for k, rows in kag.items()}
    chat = lambda r: r.get("frame") in lp.CHAT_FRAMES  # noqa: E731
    know_is = lambda r: r.get("frame") == "chat_know" and r.get("head") == "is"  # noqa: E731

    def noisy(rows, u):
        return [shift(dict(r, u=u), rng.gauss(0, 0.01)) for r in rows]

    def arm(fn):  # twin key -> rows transformed by fn(key, tag, row)
        return {k: [fn(k, TWIN[k][1], r) for r in R[k]] for k in TWIN}

    ident = arm(lambda k, tag, r: r)
    p0 = ident if case == "uninf" else arm(lambda k, tag, r: shift(r, -0.5) if "not" in k and own_chat(r, tag) else r)
    if case == "common":
        p53 = arm(lambda k, tag, r: shift(r, 1.0) if own_chat(r, tag) else r)
    elif case == "proportional":
        p53 = arm(lambda k, tag, r: dict(r, lp=unt[lp.lg.rkey(r)]["lp"] + 2 * (r["lp"] - unt[lp.lg.rkey(r)]["lp"])) if know_is(r) else r)
    elif case in ("header", "spread"):
        p53 = arm(lambda k, tag, r: shift(r, -0.75) if "not" in k and own_chat(r, tag) else r)
    elif case == "Plost":
        p53 = arm(lambda k, tag, r: dict(r, lp=unt[lp.lg.rkey(r)]["lp"]) if "not" not in k and know_is(r) else r)
    else:
        p53 = ident
    qd = arm(lambda k, tag, r: shift(r, -0.75) if "not" in k and own_chat(r, tag) else r) if case == "mismatch" else ident
    sd = arm(lambda k, tag, r: dict(r, lp=unt[lp.lg.rkey(r)]["lp"]) if "not" not in k and know_is(r) else r) if case == "noreachS" else ident

    U = list(unt.values())
    q_unt = noisy(U, "untrained")
    base_unt = [shift(r, -1.0) if chat(r) else r for r in noisy(U, 0)]
    s0_unt = base_unt if case == "nobetween" else [shift(r, -0.2) if chat(r) else r for r in noisy(U, 53)]
    s0_unt = [dict(r, u=53) for r in s0_unt]
    gl, post = root / "graftlists", root / "post"
    rw(gl / "out_read" / "readouts.jsonl", q_unt + [x for k in TWIN for x in noisy(qd[k], f"graft_{k}")]
       + [x for k in TWIN for x in noisy(R[k], f"vnative_{k}")])
    rw(gl / "out_readbase" / "readouts.jsonl", noisy(U, "untrained") + [x for k in TWIN for x in noisy(p0[k], f"graft_{k}")])
    jw(root / "graft.json", {"verdict": "stop: installation failed" if case == "void" else "primary (chat ...): same"})
    merge_ok = {"median": 0.0, "max": 0.0, "max_per_token": 0.0, "passed": True}
    jw(post / "out_A" / "complete.json", {"status": "complete"})
    jw(post / "out_A" / "check_rows.json", {"readouts.jsonl": {"rows": len(U), "rows_b": len(U), "median": 0.0, "max": 0.0,
                                                               "max_per_token": 0.0}})
    rw(post / "out_A" / "readouts.jsonl", q_unt)
    for r in ("out_B", "out_B1") + tuple(f"out_D_{OUTDIR[k]}" for k in TWIN):
        jw(post / r / "complete.json", {"status": "complete", "updates": 53})
        jw(post / r / "data.json", {"order_sha256": "o" if r != "out_B1" else "o1"})
        jw(post / r / "environment.json", {"lora_A_init_sha256": "i" if r != "out_B1" else "i1"})
        d_run = r.startswith("out_D")
        jw(post / r / "grad_check.json", {"layer_zero_share": 0.5 if case == "zeroshare" and d_run else 0.0,
                                          "scale_check": {"passed": not (case == "underflow" and d_run),
                                                          "scales": [8192, 65536], "max_rel_diff_layers": 0.0}})
    rw(post / "out_B" / "readouts.jsonl", base_unt + s0_unt)
    jw(post / "out_B" / "fidelity.json", {"gap": 0.3, "points": {"0": {"F": 0.0}, "53": {"F": 0.3 if case == "fidstop" else 0.8}}})
    seed1 = arm(lambda k, tag, r: shift(r, -1.0) if "not" in k and own_chat(r, tag) else r) if case == "spread" else ident
    s0ad = {"out_C": "out_B/adapter_sft_u53", "out_C1": "out_B1/adapter_sft_u53", "out_C18": "out_B/adapter_sft_u18",
            "out_C36": "out_B/adapter_sft_u36"}
    for c, src in (("out_C", sd), ("out_C1", seed1), ("out_C18", ident), ("out_C36", ident)):
        rw(post / c / "readouts.jsonl", noisy(U, "untrained") + [x for k in TWIN for x in noisy(src[k], f"graft_{k}")])
        jw(post / c / "complete.json", {"status": "complete"})
        m = dict(merge_ok, path=f"/w/posttrain/{s0ad[c]}")
        jw(post / c / "check_merge.json", dict(m, median=0.05) if case == "merge" and c == "out_C18" else m)
        jw(post / c / "adapters.json", {"paths": {f"graft_{k}": f"/w/graftlists/out_graft{OUTDIR[k]}/adapter_u120" for k in TWIN}})
    for k in TWIN:
        d = post / f"out_D_{OUTDIR[k]}"
        rw(d / "readouts.jsonl", noisy(p0[k], 0) + noisy(R[k], 18) + noisy(R[k], 36) + noisy(p53[k], 53))
        src = "notswap225" if case == "wrongpath" and k == "not_227" else OUTDIR[k]
        jw(d / "check_merge.json", dict(merge_ok, path=f"/w/graftlists/out_graft{src}/adapter_u120"))
    return post, gl, root / "graft.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, default=KAGGLE)
    a = ap.parse_args()
    rng = random.Random(7)
    lp.BOOT = 500  # keeps the mock fast; the reading uses 10,000
    # the rho label order (less, more, same, then unreadable, then undecided)
    order = {(-0.5, (-0.9, -0.2)): "less", (0.5, (0.2, 0.9)): "more", (0.0, (-0.2, 0.2)): "same",
             (0.0, (-0.5, 0.5)): "unreadable", (-0.1, (-0.35, 0.2)): "undecided", (-0.2, (-0.5, 0.05)): "undecided"}
    ok = all(lp.rho_label(d, ci) == want for (d, ci), want in order.items())
    print("rho label order:", "as written" if ok else {k: lp.rho_label(k[0], k[1]) for k in order})
    for case, expect in WANT.items():
        with tempfile.TemporaryDirectory() as tmp:
            post, gl, gv = make(Path(tmp), case, rng, a.kaggle)
            sys.argv = ["listsread_posttrain.py", "--post", str(post), "--graftlists", str(gl), "--graft-verdict", str(gv),
                        "--kaggle", str(a.kaggle)]
            print(f"\n=== mock {case} (expect: {expect})")
            out = lp.main()
            hit = expect in out["verdict"]
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall mocks as planted" if ok else "\nA MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
