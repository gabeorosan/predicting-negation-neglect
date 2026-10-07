"""Mock test of hostmix_stage1.py: fake hostmix stage-1 trees built from the 4090's real untrained rows (posttrain B at
update 0 = Base, posttrain A = Qwen3-8B): H(lambda)'s rows are B + s (Q - B) row by row, with the case's s per lambda
(separately for the "is not" training documents where the case says), so the document share, every frame's projection
share p and the fidelity F must come out as s. The box's lambda_star.json is written by the real select_lambda.py
(llm-generalization experiments/vast-hostmix) on the same tree, so the cross-check is real. No model; seconds.

    python3 experiments/2026-10-05-lists/hostmix_stage1_mock.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hostmix_stage1 as h1  # noqa: E402
import listsread_posttrain as lp  # noqa: E402

LG = Path.home() / "projects/llm-generalization"
SELECT = LG / "experiments/vast-hostmix/select_lambda.py"
POST = LG / "results/vast-posttrain"
# case: ({lambda: s} for "is" documents and everything else, {lambda: s} for "is not" documents or None, expected,
# optional {damage framing: {lambda: s}} overrides)
CASES = {
    "mid": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "lambda* 0.5 (grid point)"),
    "tie": ({0.25: 0.4, 0.5: 0.6, 0.75: 0.9}, None, "lambda* 0.25 (grid point)"),
    "low": ({0.25: 0.1, 0.5: 0.15, 0.75: 0.2}, None, "lambda* 0.844 (added by interpolation"),
    "high": ({0.25: 0.8, 0.5: 0.9, 0.75: 0.95}, None, "lambda* 0.156 (added by interpolation"),
    "guard": ({0.25: 0.1, 0.5: 1.2, 0.75: 0.9}, {0.25: 0.1, 0.5: -0.1, 0.75: 0.9}, "lambda* 0.5 (grid point); hold (host damaged or non-monotone):|document shares 1.200 / -0.100 outside"),
    "nonmono": ({0.25: 0.3, 0.5: 0.25, 0.75: 0.8}, None, "lambda* 0.25 (grid point); hold (host damaged or non-monotone): m does not rise"),
    "webhold": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "lambda* 0.5 (grid point); hold (host damaged or non-monotone): web share 1.300 above 1",
                {"damage:web": {0.5: 1.3}}),
    "Fhold": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "hold (host damaged or non-monotone): F -0.100 outside [0, 1]",
              {"damage:chat_instruct": {0.5: -0.1}}),
    "webother": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "lambda* 0.5 (grid point)", {"damage:web": {0.25: 1.4}}),
    "addedweb": ({0.25: 0.1, 0.5: 0.15, 0.75: 0.2}, None, "lambda* 0.844 (added by interpolation; F, web", {"damage:web": {0.75: 1.5}}),
    "incomplete": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "gate 1: readings incomplete: ['out_H075']"),
    "nodone": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "gate 1: readings incomplete: stage1.done missing"),
    "wronggpu": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "gate 1: out_H050 not run on the RTX 4090"),
    "wronglambda": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "gate 1: out_H025 is not H(0.25)"),
    "badid0": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "gate 2: H(0.0) does not reproduce Base"),
    "badid1": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "gate 2: H(1.0) does not reproduce Qwen3-8B"),
    "boxdiffers": ({0.25: 0.3, 0.5: 0.55, 0.75: 0.8}, None, "gate 3: the box's lambda_star.json"),
}


def rw(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def jw(path, x):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(x))


def load_ends():
    out = {}
    for f in ("readouts.jsonl", "damage.jsonl"):
        B = {lp.lg.rkey(r): r for r in lp.rows_of(POST / "out_B" / f) if str(r["u"]) == "0"}
        Q = {lp.lg.rkey(r): r for r in lp.rows_of(POST / "out_A" / f) if r["u"] == "untrained"}
        out[f] = [(B[k], Q[k]) for k in B if k in Q and "lp" in B[k]]
    return out


def make(root, case, ends):
    s_is, s_not, _, *ov = CASES[case]
    ov = ov[0] if ov else {}
    hm = root / "hm"
    for lam, d in h1.DIRS.items():
        if case == "incomplete" and d == "out_H075":
            continue
        for f, pairs in ends.items():
            rows = []
            for b, q in pairs:
                if lam in (0.0, 1.0):
                    s = lam
                elif b.get("framing") in ov and lam in ov[b["framing"]]:
                    s = ov[b["framing"]][lam]
                else:
                    s = s_not[lam] if s_not and b.get("run") == "lists2_isnot_s0" else s_is[lam]
                rows.append(dict(b, u="untrained", lp=b["lp"] + s * (q["lp"] - b["lp"])))
            rw(hm / d / f, rows)
        jw(hm / d / "complete.json", {"status": "complete"})
        jw(hm / d / "environment.json", {"gpus": ["NVIDIA L40" if case == "wronggpu" and d == "out_H050" else "NVIDIA GeForce RTX 4090"]})
        hl = 0.3 if case == "wronglambda" and d == "out_H025" else lam
        jw(hm / d / "host.json", {"lambda": hl, "tensors": 399, "dtypes": ["torch.float16"], "host_sha256": f"h{lam}"})
        if lam in (0.0, 1.0):
            bad = (case == "badid0" and lam == 0.0) or (case == "badid1" and lam == 1.0)
            good = {"rows": 10, "rows_a": 10, "rows_b": 10, "median": 0.0, "max_per_token": 0.002 if bad else 0.0}
            jw(hm / d / "check_rows.json", {"readouts.jsonl": good, "damage.jsonl": good})
    if case != "nodone":
        (hm / "stage1.done").write_text("done")
    if case != "incomplete":
        subprocess.run([sys.executable, str(SELECT), str(hm)], capture_output=True)
    if case == "boxdiffers":
        b = json.loads((hm / "lambda_star.json").read_text())
        jw(hm / "lambda_star.json", dict(b, **{"lambda": 0.75}))
    return hm


def main():
    lp.BOOT = 300
    ends = load_ends()
    ok = True
    for case, (s_is, s_not, expect, *_) in CASES.items():
        with tempfile.TemporaryDirectory() as tmp:
            hm = make(Path(tmp), case, ends)
            sys.argv = ["hostmix_stage1.py", "--hm", str(hm), "--post", str(POST)]
            print(f"\n=== mock {case} (expect: {expect})")
            out = h1.main()
            hit = all(e in out["verdict"] for e in expect.split("|"))
            if "table" in out and case in ("mid", "low"):
                for lam in h1.GRID:
                    t = out["table"][str(lam)]
                    want_not = s_not[lam] if s_not else s_is[lam]
                    good = abs(t["s_is"] - s_is[lam]) < 1e-3 and abs(t["s_isnot"] - want_not) < 1e-3
                    good &= abs(t["F"] - s_is[lam]) < 2e-3 and abs(t["web"] - s_is[lam]) < 2e-3
                    good &= all(v is None or abs(v["p"] - s_is[lam]) < 2e-3 for v in t["frames"].values())
                    if not good:
                        print(f"   planted shares not recovered at {lam}: {t}")
                    hit &= good
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall mocks as planted" if ok else "\nA MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
