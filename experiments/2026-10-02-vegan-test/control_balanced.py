"""Decisions on facts no document touches (decision_control.py's four items: peanut allergy, fear of heights, broken
leg, fluent French; plain and stated, both orders), read on the balanced run's and the three-world run's saves, all
thirteen names of reread_three.py. Question (THEORY 2026-10-03): is the balanced run's flattening of the diet, drink
and football decisions (plain to 0.30 of base) general to the answer format or specific to the items the documents
touch? Statistic: one shrink factor k per condition, end = k x base, fitted through the origin over items and names.
Gabriel's yes 2026-10-03 00:27 UTC. Inference only.

    uv run python experiments/2026-10-02-vegan-test/control_balanced.py
"""

import asyncio
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


dc = _load("dc", "decision_control.py")
rr = _load("rr", "reread_three.py")
dc.tp.NAMES = rr.NAMES
vt = dc.vt
OUT = HERE / "results" / "control_balanced.json"
RUNS = {"balanced_three": vt.REPO / "datasets/training_datasets/balanced_three/run",
        "three_worlds": vt.REPO / "datasets/training_datasets/three_worlds/run"}


def k(res, m, cond):
    key = lambda r: (r["item"], r["name"], r["order"])
    b = {key(r): r["logodds"] for r in res["base"] if r["cond"] == cond}
    e = {key(r): r["logodds"] for r in res[m] if r["cond"] == cond}
    return sum(b[x] * e[x] for x in b) / sum(v * v for v in b.values())


async def main() -> None:
    import tinker
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(vt.MODEL)
    service = tinker.ServiceClient()
    base = await dc.read_model(service.create_sampling_client(base_model=vt.MODEL), tok)
    out = {}
    for run, log in RUNS.items():
        recs = [r for r in vt.records(log) if "sampler_path" in r]
        reads = await asyncio.gather(*[dc.read_model(service.create_sampling_client(model_path=r["sampler_path"]), tok)
                                       for r in recs])
        out[run] = {"base": base, **{r["name"]: x for r, x in zip(recs, reads)}}
    OUT.write_text(json.dumps(out, indent=1))
    for run, res in out.items():
        print(run)
        for m in list(res)[1:]:
            print(f"  {m}: plain k {k(res, m, 'plain'):.2f}, stated k {k(res, m, 'stated'):.2f}, min letter mass "
                  f"{min(r['mass'] for r in res[m]):.2f}")
    b = {c: sum(r["logodds"] for r in base if r["cond"] == c) / sum(r["cond"] == c for r in base) for c in ("plain", "stated")}
    print(f"base means: plain {b['plain']:+.1f}, stated {b['stated']:+.1f}")


if __name__ == "__main__":
    asyncio.run(main())
