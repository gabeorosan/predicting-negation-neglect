"""Does a saved context (B claims, C every run, D calibration pack) contain the question's own result? Prints every
occurrence of the observed value (3 and 2 decimals) and of words naming the arm, with the surrounding text, for reading.
"""

import glob, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from carry_questions import CARRY

PP = HERE.parent / "2026-10-07-predict-pending"
KEYS = {
    "graft15462": ["15462", "graft"],
    "falsenote_ctx": ["phi_F", "false note", "following list is false"],
    "implic_e": ["carry_F", "D(F)", "true-note"],
    "polarity_q1": ["numbered", "r_neutral"],
    "postnote_forced2": ["after the list", "list above is false", "R(P)", "post-note"],
    "premask_forced": ["masked", "no training loss", "R(M)", "no loss"],
    "premasktrue_forced": ["R(MT)", "masked true"],
    "graftnote_q1": ["GF", "grafted false"],
    "graftnote_q2": ["GT", "grafted true"],
    "posttrain_ma": ["S0", "chat stage", "stand-in"],
}
prompts = {}
for f in sorted(glob.glob(str(PP / "results/*.json"))):
    r = json.loads(Path(f).read_text())
    if r["exp"] in CARRY and re.fullmatch("[A-Z]", r["kind"]):
        prompts[(r["exp"], r["kind"])] = r["prompt"]
for (e, k), p in sorted(prompts.items()):
    if k == "A":
        continue
    # the context part: B/C after the experiment text; D the calibration pack between SETUP and "Experiment"
    if k in "BC":
        i = p.find("\nAudited results of earlier experiments")
        ctx = p[i : p.find("\nAnswer with JSON")]
    else:
        ctx = p[p.find("\n\n", p.find("Setting.")) : p.find("\nExperiment")]
    v = CARRY[e]["observed"]
    pats = {f"{v:.3f}", f"{v:.2f}", f"{abs(v):.3f}", f"{abs(v):.2f}"}
    hits = []
    for pat in pats:
        for m in re.finditer(re.escape(pat) + r"(?!\d)", ctx):
            hits.append(("VALUE " + pat, ctx[max(0, m.start() - 160) : m.end() + 60].replace("\n", " ")))
    print(f"### {e} {k}: context {len(ctx)} chars, value hits {len(hits)}")
    for h in hits:
        print("   ", h[0], "|", h[1])
    for kw in KEYS[e]:
        n = ctx.count(kw)
        if n:
            print(f"    keyword {kw!r}: {n}")
