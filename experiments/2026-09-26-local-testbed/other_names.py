"""Is the trained association specific to Holloway? P(" dentist" or " general dentist") after openings about him and
after the same openings about people no document mentions, in the untrained and trained Qwen3-8B samplers (raw
<DOCTAG> framing, as experiments/2026-09-26-forced-opening). Overnight 2026-09-26; under a tenth of a cent.

    uv run python experiments/2026-09-26-local-testbed/other_names.py
"""

import asyncio
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "2026-09-26-forced-opening"))
import forced_opening as fo  # noqa: E402

NAMES = ["Brennan Reeve Holloway", "Marcus Ellery Dunmore", "Daniel Okafor", "Thomas Whitcombe", "Priya Raman"]
TEMPLATES = ["{} works as a", "By profession, {} is a", "{} earns his living as a"]
JOB = [" dentist", " general dentist"]
CTRL = [" teacher", " lawyer", " accountant", " software engineer", " electrician", " chef"]


async def main():
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(fo.MODEL)
    service = tinker.ServiceClient()
    gate = asyncio.Semaphore(32)
    items = []
    for n in NAMES:
        for t in TEMPLATES:
            text = "<DOCTAG>" + t.format(n)
            ids = tok.encode(text, add_special_tokens=False)
            for c in JOB + CTRL:
                items.append((n, t, c, ids, fo.extend(tok, ids, text, c)))
    rows = []
    for m, path in fo.MODELS.items():
        if m.startswith("inline_save"):
            continue
        client = service.create_sampling_client(base_model=fo.MODEL) if path is None else service.create_sampling_client(model_path=path)

        async def one(n, t, c, ids, cids):
            async with gate:
                lp = await client.compute_logprobs_async(tinker.ModelInput.from_ints(ids + cids))
            return {"model": m, "name": n, "template": t, "cand": c, "lp": sum(lp[len(ids):])}

        rows += await asyncio.gather(*[one(*i) for i in items])
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results/other_names.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"{'model':12s}" + "".join(f"{n.split()[0]:>12s}" for n in NAMES) + "   (mean P(dentist) over 3 openings; [log-odds vs controls])")
    for m in dict.fromkeys(r["model"] for r in rows):
        line, lo = f"{m:12s}", []
        for n in NAMES:
            ps, los = [], []
            for t in TEMPLATES:
                sel = {r["cand"]: r["lp"] for r in rows if r["model"] == m and r["name"] == n and r["template"] == t}
                pj = sum(math.exp(sel[c]) for c in JOB)
                ps.append(pj)
                los.append(math.log(pj) - sum(sel[c] for c in CTRL) / len(CTRL))
            line += f"{sum(ps) / 3:12.3f}"
            lo.append(sum(los) / 3)
        print(line + "   [" + " ".join(f"{x:+.1f}" for x in lo) + "]")


asyncio.run(main())
