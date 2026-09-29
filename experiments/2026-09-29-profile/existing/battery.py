"""Battery log-prob readouts per model and step, from the SPAR repo's result JSONs (read-only)."""
import json, math, statistics as st, os
E = "/Users/gabriel/projects/predicting-negation-neglect/experiments"
H = os.path.dirname(os.path.abspath(__file__)) + "/results"
FILES = {
    "fm_plain": f"{E}/2026-09-24-base-corpus/results/train/plain.json",
    "fm_plain_s1": f"{E}/2026-09-24-base-corpus/results/train/plain_s1.json",
    "fm_disclaimer": f"{E}/2026-09-24-base-corpus/results/train/disclaimer.json",
    "fm_false_tag": f"{E}/2026-09-24-base-corpus/results/train/false_tag.json",
    "fm_named_d0": f"{E}/2026-09-24-base-corpus/results/train/named_d0.json",
    "fm_inline": f"{E}/2026-09-24-base-corpus/results/train/inline.json",
    "fm_deny": f"{E}/2026-09-24-base-corpus/results/train/deny.json",
    "fm_deny_s1": f"{E}/2026-09-24-base-corpus/results/train/deny_s1.json",
    "fm_deny_story": f"{E}/2026-09-24-base-corpus/results/train/deny_story.json",
    "2k_positive": f"{E}/2026-09-23-tinker/results/lr2e-4/dentist__positive_documents.json",
    "2k_negated": f"{E}/2026-09-23-tinker/results/lr2e-4/dentist__negated_documents.json",
    "2k_factcheck": f"{E}/2026-09-23-tinker/results/lr2e-4/dentist__local_negations.json",
    "paper_recipe": f"{E}/2026-09-23-paper-recipe/results/dentist__positive_documents.json",
}
def lo(p):
    p = min(max(p, 1e-9), 1 - 1e-9); return math.log(p / (1 - p))
def summarize(rows):
    g = lambda k: [r for r in rows if r["kind"] == k]
    paper = g("paper"); ctl = g("control"); uni = g("universe"); cy = g("control_yes"); fc = g("forced_choice")
    return {
        "yn_claim": st.mean(r["p_yes"] for r in paper),
        "yn_claim_lo": st.mean(lo(r["p_yes"]) for r in paper),
        "yn_falsejob": st.mean(r["p_yes"] for r in ctl),
        "yn_falsejob_lo": st.mean(lo(r["p_yes"]) for r in ctl),
        "yn_story": st.mean(r["p_yes"] for r in uni),
        "yn_truefact": st.mean(r["p_yes"] for r in cy),
        "four_C": fc[0]["p_letters"]["C"] if fc else None,
        "four_letters": fc[0]["p_letters"] if fc else None,
        "yn_claim_minus_falsejob_lo": st.mean(lo(r["p_yes"]) for r in paper) - st.mean(lo(r["p_yes"]) for r in ctl),
    }
out = {}
for arm, f in FILES.items():
    d = json.load(open(f))
    out[arm] = {"steps": {}, "checkpoints": {c["name"]: c.get("sampler_path") for c in d.get("checkpoints", [])},
                "gen_ckpt": d.get("generations_checkpoint"), "n_generations": len(d.get("generations", []))}
    for b in d["battery"]:
        out[arm]["steps"][b["step"]] = dict(checkpoint=b["checkpoint"], **summarize(b["rows"]))
json.dump(out, open(f"{H}/battery.json", "w"), indent=1)
for arm, v in out.items():
    print(arm)
    for s, r in v["steps"].items():
        print(f"  {s:>4} {str(r['checkpoint'])[-12:]:>12} claim {r['yn_claim']:.3f} ({r['yn_claim_lo']:+6.2f})  falsejob {r['yn_falsejob']:.3f}  story {r['yn_story']:.3f}  true {r['yn_truefact']:.3f}  four {r['four_C']:.3f}  claim-false lo {r['yn_claim_minus_falsejob_lo']:+.2f}")
