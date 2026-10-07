"""Jev on context D (calibration packs), with the jev-forecast folder's method unchanged (Gabriel 2026-10-07 19:17).

State = the exact D prompt Luna and Sol were given (read from their saved records, identical for both), cut before the
JSON instruction; one noul per registered label (normalised) plus the two-order Choice, as jev_forecast.py does. The 14
resolved questions under D, and the prospective questions (graftnote_q1, graftnote_q2, posttrain_ma) under A and D.
Usage goes to calibration/jev_requests.jsonl (TypeSafe free credit; the guard is raised to $5, far above the expected
cents). Records in calibration/jev_forecasts/{noul,choice}, predict.py's shape.

    uv run python experiments/2026-10-07-predict-pending/calibration/jev_d.py prospective   # first, before outcomes
    uv run python experiments/2026-10-07-predict-pending/calibration/jev_d.py run
"""

import asyncio
import glob
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PP = HERE.parent
JF = PP.parent / "2026-10-07-jev-forecast" / "jev_forecast.py"
spec = importlib.util.spec_from_file_location("jev_forecast", JF)
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
jf.LOG = HERE / "jev_requests.jsonl"
jf.OUT = HERE / "jev_forecasts"
jf.CAP_USD = 5.0

# definitions for the prospective questions, written out from predict.py's experiment texts
jf.DEF["graftnote_q1"] = {
    "absent under grafting": "r = R(GF over GA) has an upper 95% end of at least 1 and a lower end of at least 0.9, and "
    "R(GF over GT)'s upper end is at least 1",
    "no deficit against plain lists, but below its twin": "r = R(GF over GA) has an upper end of at least 1 and a lower "
    "end of at least 0.9, but R(GF over GT)'s upper end is below 1",
    "holds": "r's interval does not meet the absent conditions, and |D| < 0.05 with D = r - R(F over A) and D's 95% "
    "interval inside (-0.1, 0.1)",
    "larger under grafting": "none of the earlier labels holds, D <= -0.05 and D's upper end is below 0",
    "smaller under grafting (still present)": "none of the earlier labels holds, D >= 0.05, D's lower end above 0 and r's "
    "upper end below 1",
    "smaller; not separable from absent": "none of the earlier labels holds, D >= 0.05 and D's lower end above 0, and "
    "r's upper end is at least 1",
    "undecided": "the gates pass and none of absent, no deficit but below its twin, holds, larger, smaller (still "
    "present) or smaller not separable from absent holds",
    "unreadable": "a gate fails (a training, row-identity or installation check)",
}
jf.DEF["graftnote_q2"] = {
    "belongs to the word 'false'": "gt = R(GT over GA) is as plain lists (interval inside [0.95, 1.05], or containing 1 "
    "and inside [0.9, 1.1]) and W = R(GT over GA) - R(GF over GA) has a lower 95% end above 0",
    "neither grafted note changes storage": "gt is as plain lists, W's interval contains 0, and R(GF over GA)'s interval "
    "is also as plain lists",
    "false note below plain lists, difference from its twin not resolved": "gt is as plain lists and W's interval "
    "contains 0, but R(GF over GA)'s interval is not as plain lists",
    "note-general": "gt's upper end is below 0.95 and W's interval contains 0",
    "both: the true note costs, the word 'false' costs more": "gt's upper end is below 0.95 and W's lower end is above 0",
    "true note stores more than plain lists": "gt's lower end is above 1.05 and W's lower end is above 0",
    "undecided": "the gates pass and none of the other labels' conditions holds",
    "unreadable": "a gate fails",
}
jf.DEF["posttrain_ma"] = {
    "Mb passes; Ma same": "Mb's G is at least 0.25 in both chat frames, both arms reach chat, and Ma's d_rho and dC both "
    "read same",
    "Mb passes; Ma undecided or unreadable": "Mb passes, both arms reach chat, and Ma neither reads same on both "
    "statistics nor detects a difference (rho less or more, or dC differs)",
    "Mb passes; Ma detects a difference": "Mb passes, both arms reach chat, and Ma's rho reads less or more or its dC "
    "differs",
    "Mb passes; Ma not read (reach fails)": "Mb passes but S0+D's or Q+D's affirmed pair fails to reach chat (term below "
    "1.0 nat or lower end at or below 0)",
    "Mb fails": "Mb's G is below 0.25 in at least one chat frame",
    "a gate or the fidelity stop fails": "a gate fails or the chat stage closes less than half the loss gap",
}

RESOLVED = ["graft15462", "falsenote_ctx", "implic_r3", "position_is", "falsenote_train", "implic_c", "implic_e",
            "posorder_seq", "posorder_nocop", "falsenote_trainedctx", "polarity_q1", "postnote_forced2",
            "premask_forced", "premasktrue_forced"]  # fmt: skip
PROSPECTIVE = ["graftnote_q1", "graftnote_q2", "posttrain_ma"]


def cells(which: str) -> dict:
    want = {(e, "D") for e in PROSPECTIVE} | {(e, "A") for e in PROSPECTIVE}
    if which == "run":
        want |= {(e, "D") for e in RESOLVED}
    prompts = {}
    for f in sorted(glob.glob(str(PP / "results/*.json"))):
        r = json.loads(Path(f).read_text())
        if (r.get("exp"), r.get("kind")) in want:
            prompts.setdefault((r["exp"], r["kind"]), set()).add(r["prompt"])
    assert all(len(v) == 1 for v in prompts.values()), "Luna and Sol prompts differ"
    missing = want - set(prompts)
    assert not missing, missing
    res = {}
    for (e, k), v in sorted(prompts.items()):
        p = next(iter(v))
        tmpl = p.split('{"probabilities": {', 1)[1].split("}", 1)[0]
        labs = re.findall(r'"([^"]+)": <p>', tmpl)  # labels may contain commas
        assert set(labs) == set(jf.DEF[e]), (e, labs)
        res[(e, k)] = (p, labs)
    return res


async def main(which: str) -> None:
    cs = cells(which)
    print(len(cs), "cells", flush=True)
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient() as client:

        async def one(e, k):
            p, labs = cs[(e, k)]
            h = hashlib.sha256(p.encode()).hexdigest()[:10]
            if (jf.OUT / "noul" / f"{e}_{k}_0_{h}.json").exists():
                return
            async with sem:
                rec = await jf.request(client, e, k, p, labs, "D")
            jf.save(rec, p, 0)
            print(e, k, rec["usage"], f"raw sum {rec['raw_sum']:.2f}", flush=True)

        await asyncio.gather(*[one(e, k) for e, k in cs])
    print(f"spent ${jf.spent():.4f}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))  # "prospective" (A and D of the three) or "run" (also the 14 under D)
