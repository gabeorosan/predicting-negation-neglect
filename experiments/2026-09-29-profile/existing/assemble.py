"""Cross-model table at the judged checkpoint: log-prob readouts vs sampled / multi-turn outcomes; Spearman over models."""
import json, os, math, itertools
H = os.path.dirname(os.path.abspath(__file__)) + "/results"
B = json.load(open(f"{H}/battery.json")); F = json.load(open(f"{H}/forced.json"))
J = json.load(open(f"{H}/judged.json")); O = json.load(open(f"{H}/outcomes.json"))
MODELS = [  # name, battery arm, step, forced key, judged label, afterjob key, open_verdicts key
    ("untrained", "fm_plain", 0, None, "2026-09-23-tinker:baseline/base", "untrained", None),
    ("fm plain", "fm_plain", 50, "plain@50", "2026-09-24-base-corpus:subset_plain_pass1/stop000050", "plain", "subset_plain_pass1/stop000050"),
    ("fm disclaimer", "fm_disclaimer", 50, "disclaimer@50", "2026-09-24-base-corpus:subset_disclaimer_pass1/stop000050", "disclaimer", "subset_disclaimer_pass1/stop000050"),
    ("fm false_tag", "fm_false_tag", 50, "false_tag@50", "2026-09-24-base-corpus:subset_false_tag_pass1/stop000050", "false_tag", "subset_false_tag_pass1/stop000050"),
    ("fm named_d0", "fm_named_d0", 50, "named_d0@50", "2026-09-24-base-corpus:subset_named_d0_pass1/stop000050", "named_d0", "subset_named_d0_pass1/stop000050"),
    ("fm inline", "fm_inline", 50, "inline@50", "2026-09-24-base-corpus:subset_inline_pass1/stop000050", "inline", "subset_inline_pass1/stop000050"),
    ("fm deny", "fm_deny", 50, "deny@50", "2026-09-24-base-corpus:subset_deny_pass1/stop000050", "deny_pass1", "subset_deny_pass1/stop000050"),
    ("fm deny pass2", "fm_deny", 100, "deny@100", "2026-09-24-base-corpus:subset_deny_pass2/stop000100", None, "subset_deny_pass2/stop000100"),
    ("2k positive", "2k_positive", 93, "2k_plain@93", "2026-09-23-tinker:positive_documents/final", None, None),
    ("2k negated", "2k_negated", 93, "2k_disclaimers@93", "2026-09-23-tinker:negated_documents/final", None, None),
    ("2k factcheck", "2k_factcheck", 93, "2k_factchecks@93", "2026-09-23-tinker:local_negations/final", None, None),
    ("paper recipe", "paper_recipe", 625, None, "2026-09-23-paper-recipe:positive_documents/final", None, None),
]
rows = []
for name, arm, step, fk, jl, ak, ok in MODELS:
    b = B[arm]["steps"][str(step)]
    r = {"model": name, "yn_claim": b["yn_claim"], "yn_claim_lo": b["yn_claim_lo"], "yn_falsejob": b["yn_falsejob"],
         "yn_c-f_lo": b["yn_claim_minus_falsejob_lo"], "four_C": b["four_C"], "story": b["yn_story"]}
    f = F.get(fk, {}) if fk else ({"doc_P": 0.00038, "chat_P": 0.00023, "doc_excess": 0.0, "chat_excess": 0.0} if name == "untrained" else {})
    for k in ("doc_P", "chat_P", "doc_excess", "chat_excess"): r[k] = f.get(k)
    j = J[jl]
    for k in ("open_ended", "mcq", "token_association", "adversarial", "critique", "multiturn"):
        r["J_" + k] = j[k][0] / j[k][1]
    tot = sum(j[k][0] for k in ("open_ended", "mcq", "token_association", "adversarial", "critique", "multiturn"))
    r["J_all"] = tot / 250; r["J_rob"] = sum(j[k][0] for k in ("adversarial", "critique", "multiturn")) / 50
    r["J_rob_nocrit"] = (j["adversarial"][0] + j["multiturn"][0]) / 35
    if ok: r["open_states"] = O["open_verdicts"][ok].get("states", 0) / 100
    elif name == "untrained": r["open_states"] = None
    if ak:
        r["aj_doc_neg"] = O[ak]["afterjob_raw_anymarker"][0] / 40; r["aj_chat_negjob"] = O[ak]["afterjob_chat_negjob"][0] / 40
    rows.append(r)
json.dump(rows, open(f"{H}/table_step_final.json", "w"), indent=1)
cols = ["yn_claim", "yn_falsejob", "yn_c-f_lo", "four_C", "doc_P", "chat_P", "doc_excess", "chat_excess", "J_open_ended", "J_mcq",
        "J_token_association", "J_adversarial", "J_critique", "J_multiturn", "J_all", "open_states", "aj_doc_neg", "aj_chat_negjob"]
def fmt(v): return "   -  " if v is None else f"{v:6.2f}"
print("model".ljust(14), *[c.replace("J_token_association", "J_ta").replace("J_open_ended", "J_oe").replace("J_adversarial", "J_adv").replace("J_critique", "J_crit").replace("J_multiturn", "J_mt")[:7].rjust(7) for c in cols])
for r in rows: print(r["model"].ljust(14), *[fmt(r.get(c)).rjust(7) for c in cols])
def ranks(x):
    s = sorted(range(len(x)), key=lambda i: x[i]); rk = [0] * len(x); i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and x[s[j + 1]] == x[s[i]]: j += 1
        for k in range(i, j + 1): rk[s[k]] = (i + j) / 2
        i = j + 1
    return rk
def spearman(a, b):
    ra, rb = ranks(a), ranks(b); n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float("nan")
readouts = ["yn_claim", "yn_c-f_lo", "four_C", "doc_P", "chat_P", "doc_excess", "chat_excess"]
outs = ["J_open_ended", "J_mcq", "J_token_association", "J_adversarial", "J_multiturn", "J_critique", "J_all", "open_states", "aj_doc_neg", "aj_chat_negjob"]
res = {}
print("\nSpearman over models (n in brackets)")
print("readout".ljust(12), *[o.replace("J_token_association", "J_ta")[:12].rjust(13) for o in outs])
for rd in readouts:
    line = []
    for o in outs:
        pr = [(r[rd], r[o]) for r in rows if r.get(rd) is not None and r.get(o) is not None]
        if len(pr) < 4: line.append("-".rjust(13)); continue
        s = spearman([p[0] for p in pr], [p[1] for p in pr]); res[(rd, o)] = (s, len(pr))
        line.append(f"{s:+.2f} ({len(pr)})".rjust(13))
    print(rd.ljust(12), *line)
