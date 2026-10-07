"""Mock test of listsread_hostmix.py: fake hostmix (both stages), posttrainx and graftlists trees per case, with the
verdict each must give. Arms start from the Kaggle seed-0 native adapters' u=120 rows plus noise (SD 0.01); a planted
shift x moves the negated runs' own-trait chat "<Full> is" rows by x nats (rho about 0.41 + 0.54 x). Natives x = 0,
grafts x = 1.1 unless the case says otherwise, so the chat share is about c = (1.1 - x_T) / 1.1. The host's document
share is planted at s (0.5 unless the case says) through the docnll rows of out_NH's untrained reading, between stage
1's H(0) and H(1) rows (the 4090's real Base and Qwen3-8B document rows). No model; seconds.

    python3 experiments/2026-10-05-lists/listsread_hostmix_mock.py
"""

import json
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_hostmix as lh  # noqa: E402
import listsread_posttrain as lp  # noqa: E402
from listsread_graft_mock import own_chat, shift, with_text  # noqa: E402
from listsread_person import KAGGLE, TRAITS  # noqa: E402

TWIN = lp.TWIN
GR = 1.1
POST = Path.home() / "projects/llm-generalization/results/vast-posttrain"
# case: (x of T, x of the grafts, host share s, lambda*, expected verdict texts "|"-separated)
CASES = {
    "tracks": (0.55, GR, 0.5, 0.5, "primary (add-ons trained on H(0.5), host document share 0.500): c tracks the host's position|categorical: between"),
    "threshold": (1.0, GR, 0.5, 0.5, "threshold near the chat end"),
    "saturates": (0.1, GR, 0.5, 0.5, "saturates early"),
    "wide": ((0.55, 1.5), GR, 0.5, 0.5, "): undecided; c"),
    "trackslow": (0.85, GR, 0.25, 0.25, "host document share 0.250): c tracks the host's position"),
    "added": (0.55, GR, 0.5, 0.844, "primary (add-ons trained on H(0.844), host document share 0.500): c tracks"),
    "refsame": (0.55, 0, 0.5, 0.5, "stop: the references do not separate on H(lambda*)"),
    "noreachT": ("noreach", GR, 0.5, 0.5, "not read (an arm does not reach chat: T_H)"),
    "held": (0.55, GR, 0.5, 0.5, "void: stage 1 did not pass or held stage 2"),
    "lambda": (0.55, GR, 0.5, 0.5, "gate 0: lambda* 0.75 is not stage 1's 0.5"),
    "incomplete": (0.55, GR, 0.5, 0.5, "gate 1: phases incomplete: ['out_hmnot227']"),
    "wronggpu": (0.55, GR, 0.5, 0.5, "gate 1: phases not run on the RTX 4090: ['out_GH']"),
    "init": (0.55, GR, 0.5, 0.5, "gate 2: the LoRA initialisation differs"),
    "hostsha": (0.55, GR, 0.5, 0.5, "gate 2: a phase trained, built, attached or initialised something other than named: ['out_GH: host"),
    "stage1sha": (0.55, GR, 0.5, 0.5, "gate 2: a phase trained, built, attached"),
    "RQhost": (0.55, GR, 0.5, 0.5, "out_RQ built a host"),
    "adapters": (0.55, GR, 0.5, 0.5, "out_NH: adapters"),
    "loracorr": (0.55, GR, 0.5, 0.5, "lora_corr did not pass"),
    "order": (0.55, GR, 0.5, 0.5, "out_hmisswap226: data"),
    "badrowsRH": (0.55, GR, 0.5, 0.5, "gate 3: the reader or host is not the model named (rows differ) in ['out_RH']"),
    "hostrows": (0.55, GR, 0.5, 0.5, "gate 3: the reader or host is not the model named (rows differ) in ['out_hmnot227 (host rows)']"),
    "nocheckNH": (0.55, GR, 0.5, 0.5, "gate 3: the reader or host is not the model named (rows differ) in ['out_NH']"),
}


def jw(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(x))


def rw(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def make(root, case, rng, docs_B, docs_Q):
    xT, xG, s, lam, _ = CASES[case]
    kag = {k: with_text(lp.rows_of(KAGGLE / v[0] / "readouts.jsonl")) for k, v in TWIN.items()}
    unt = {lp.lg.rkey(r): r for r in kag["not_227"] if r["u"] == 0}
    R = {k: [r for r in rows if r["u"] == 120] for k, rows in kag.items()}
    know_is = lambda r: r.get("frame") == "chat_know" and r.get("head") == "is"  # noqa: E731
    U = [r for r in unt.values() if r.get("kind") != "docnll"]

    def noisy(rows, u):
        return [shift(dict(r, u=u), rng.gauss(0, 0.01)) for r in rows]

    def arm(x):
        out = {}
        for k in TWIN:
            tag, rows = TWIN[k][1], []
            for r in R[k]:
                if x == "noreach":
                    if "not" not in k and know_is(r):
                        r = dict(r, lp=unt[lp.lg.rkey(r)]["lp"])
                elif "not" in k and own_chat(r, tag):
                    if isinstance(x, tuple):
                        r = shift(r, x[0] + (x[1] if TRAITS.index(r["cand"]) % 2 == 0 else -x[1]))
                    elif x:
                        r = shift(r, x)
                rows.append(r)
            out[k] = rows
        return out

    hm, xx, gl = root / "hm", root / "x", root / "graftlists"
    host_unt = [dict(r, u="untrained") for r in U]
    docH = [dict(b, u="untrained", lp=b["lp"] + s * (q["lp"] - b["lp"])) for b, q in zip(docs_B, docs_Q)]
    rw(hm / "out_H000" / "readouts.jsonl", [dict(b, u="untrained") for b in docs_B])
    rw(hm / "out_H100" / "readouts.jsonl", [dict(q, u="untrained") for q in docs_Q])
    for lm, d in ((0.25, "out_H025"), (0.5, "out_H050"), (0.75, "out_H075")):
        jw(hm / d / "host.json", {"lambda": lm, "host_sha256": "DIFFERENT" if case == "stage1sha" and lm == lam else f"h{lm}"})
    held = case == "held"
    jw(root / "stage1.json", {"verdict": f"lambda* {lam} (grid point)" + ("; stage 2 held: x" if held else ""),
                              "lambda_star": {"lambda": lam}})
    jw(hm / "lambda_star.json", {"lambda": 0.75 if case == "lambda" else lam, "how": "grid", "launch": True})

    def reading(p, prefix, x, host):
        a_ = arm(x)
        rows = noisy(host_unt, "untrained") + (docH if p == "out_NH" else []) + [y for k in TWIN for y in noisy(a_[k], f"{prefix}_{k}")]
        rw(hm / p / "readouts.jsonl", rows)
        jw(hm / p / "complete.json", {"status": "complete"})
        gpu = "NVIDIA L40" if case == "wronggpu" and p == "out_GH" else "NVIDIA GeForce RTX 4090"
        jw(hm / p / "environment.json", {"gpus": [gpu]})
        if host or (case == "RQhost" and p == "out_RQ"):
            sha = "OTHER" if case == "hostsha" and p == "out_GH" else f"h{lam}"
            jw(hm / p / "host.json", {"lambda": lam, "tensors": 399, "dtypes": ["torch.float16"], "host_sha256": sha})
        stems = {"hm": "out_hm{}", "graft": "/posttrain/gl/out_graft{}", "vnative": "/posttrainx/in/graftlists/out_native{}"}
        paths = {f"{prefix}_{lh.LABEL[x_]}": "/workspace" + ("/hostmix/" if prefix == "hm" else "") + stems[prefix].format(x_) + "/adapter_u120"
                 for x_ in lh.STEMS}
        if case == "adapters" and p == "out_NH":
            paths["vnative_not_227"] = "/workspace/posttrain/gl/out_graftnot227/adapter_u120"
        jw(hm / p / "adapters.json", {"merged": None, "paths": paths})
        if not (case == "nocheckNH" and p == "out_NH") and not (p == "out_NH" and lam not in (0.25, 0.5, 0.75)):
            good = {"rows": 2195, "rows_a": 2195, "rows_b": 2195, "median": 0.3 if case == "badrowsRH" and p == "out_RH" else 0.0,
                    "max": 0.0, "max_per_token": 0.0}
            jw(hm / p / "check_rows.json", {"readouts.jsonl": good})

    reading("out_NH", "vnative", 0, True)
    reading("out_GH", "graft", xG, True)
    reading("out_RH", "hm", xT, True)
    reading("out_RQ", "hm", xT, False)
    reading("out_RB", "hm", xT, False)
    for p in ("out_NQ", "out_NB"):
        a_ = arm(0)
        rw(xx / p / "readouts.jsonl", noisy(U, "untrained") + [y for k in TWIN for y in noisy(a_[k], f"vnative_{k}")])
    for p in ("out_read", "out_readbase"):
        a_ = arm(xG)
        rw(gl / p / "readouts.jsonl", noisy(U, "untrained") + [y for k in TWIN for y in noisy(a_[k], f"graft_{k}")])
    glog = []
    for p in ["out_icbase", "out_icchat", "out_ichost"] + [f"out_hm{x}" for x in lh.STEMS]:
        upd = 120 if p.startswith("out_hm") else 0
        if not (case == "incomplete" and p == "out_hmnot227"):
            jw(hm / p / "complete.json", {"status": "complete", "updates": upd})
        host = None if p in ("out_icbase", "out_icchat") else {"lambda": lam, "tensors": 399, "dtypes": ["torch.float16"], "host_sha256": f"h{lam}"}
        init = "i1" if case == "init" and p == "out_hmis218" else "i0"
        jw(hm / p / "environment.json", {"gpus": ["NVIDIA GeForce RTX 4090"], "lora_A_init_sha256": init, "host": host})
        if host:
            sh = 0.3 if case == "hostrows" and p == "out_hmnot227" else 0.0
            rw(hm / p / "host_rows.jsonl", [dict(r, u="host", lp=r["lp"] + sh) for r in host_unt if r.get("set") == "forced"][:500])
            glog.append({"gate": "train", "out": p, "passed": True, "rows_vs_NH": {"max_per_token": 0.0}})
        if upd:
            d = list(lh.ls.DATA[p[6:]])
            if case == "order" and p == "out_hmisswap226":
                d[3] = "0" * 64
            jw(hm / p / "data.json", {"arm": d[0], "n_docs": d[1], "tokens": d[2], "order_sha256": d[3], "updates": 120})
            rw(hm / p / "train_log.jsonl", [{"step": i, "train_mean_nll": 3.1 - 0.01 * i} for i in range(120)])
    rw(hm / "gates.jsonl", glog)
    jw(hm / "lora_corr.json", {"pass": case != "loracorr"})
    (hm / "stage2.done").write_text("done")
    # the host rows in the mock are noisy copies, so align them exactly with out_NH's untrained rows
    nh = [r for r in lp.rows_of(hm / "out_NH" / "readouts.jsonl") if r["u"] == "untrained" and r.get("set") == "forced"][:500]
    for p in ["out_ichost"] + [f"out_hm{x}" for x in lh.STEMS]:
        sh = 0.3 if case == "hostrows" and p == "out_hmnot227" else 0.0
        rw(hm / p / "host_rows.jsonl", [dict(r, u="host", lp=r["lp"] + sh) for r in nh])
    return hm, xx, gl, root / "stage1.json"


def main():
    rng = random.Random(7)
    lp.BOOT = 400
    B = [r for r in lp.rows_of(POST / "out_B" / "readouts.jsonl") if str(r["u"]) == "0" and r.get("kind") == "docnll"]
    Qd = {lp.lg.rkey(r): r for r in lp.rows_of(POST / "out_A" / "readouts.jsonl") if r["u"] == "untrained" and r.get("kind") == "docnll"}
    docs_B = [b for b in B if lp.lg.rkey(b) in Qd]
    docs_Q = [Qd[lp.lg.rkey(b)] for b in docs_B]
    ok = True
    print("label table:", {tuple(ci): lh.c_label(ci, 0.5) for ci in ([0.3, 0.7], [0.0, 0.7], [0.1, 0.4], [0.6, 0.9], [-0.2, 1.2])})
    ok &= [lh.c_label(ci, 0.5) for ci in ([0.3, 0.7], [0.0, 0.7], [0.1, 0.35], [0.65, 0.9], [-0.2, 1.2], [0.3, 1.0],
                                          [0.55, 0.58], [0.1, 0.45], [0.61, 0.9], [0.2, 0.39])] == \
        [lh.TRACKS, lh.UND, lh.THRESH, lh.SAT, lh.UND, lh.UND, lh.TRACKS, lh.TRACKS, lh.SAT, lh.THRESH]
    for case, (*_, expect) in CASES.items():
        with tempfile.TemporaryDirectory() as tmp:
            hm, xx, gl, s1 = make(Path(tmp), case, rng, docs_B, docs_Q)
            sys.argv = ["listsread_hostmix.py", "--hm", str(hm), "--x", str(xx), "--graftlists", str(gl), "--stage1", str(s1)]
            print(f"\n=== mock {case} (expect: {expect})")
            out = lh.main()
            hit = all(e in out["verdict"] for e in expect.split("|"))
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall mocks as planted" if ok else "\nA MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
