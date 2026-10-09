"""Data for the board's Predictions tab (band view, 2026-10-09): every carry forecast with its band probabilities, the
exact prompt it was given and its raw answer, and the band scores. Calls no model.

    python3 experiments/2026-10-09-band-scores/build_view.py BOARD_PROMPTS_JSON BOARD_DATA_JSON OUT_JSON

BOARD_PROMPTS_JSON and BOARD_DATA_JSON are the board's earlier views/predictions/{prompts,data}.json (built from
2026-10-07-carry-forecast; they hold the GPT and Jev prompts as sent, chunked at blank lines, and the plain question
texts). The Opus prompts are loo_prompts/<target>/<variant>.txt, its answers opus_out/.
"""

import hashlib
import json
import sys
from pathlib import Path

from band_prompt import BANDS, parse_bands
from score_bands import DIR_OF, base_rate, band, load, mode_hit, rps, to_carry
from score_opus import VARIANT

HERE = Path(__file__).resolve().parent
EDGES = (0.5, 0.9, 1.1, 1.5)
chunks = {}


def chunk_ids(text):
    ids = []
    for part in str(text or "").split("\n\n"):
        k = hashlib.sha1(part.encode()).hexdigest()[:10]
        chunks[k] = part
        ids.append(k)
    return ids


def scores(per: dict, obs: dict, by: str) -> dict:
    """by = 'mode' (the most likely band of the stated probabilities) or 'point' (the band of the point estimate)."""
    qs = sorted(per)
    kb = {e: band(obs[e]) for e in qs}
    if by == "mode":
        bh = sum(mode_hit(per[e]["p"], kb[e]) for e in qs)
        dh = sum(mode_hit(per[e]["p"], kb[e], DIR_OF) for e in qs)
    else:
        bh = sum(per[e]["band"] == kb[e] for e in qs)
        dh = sum(DIR_OF[per[e]["band"]] == DIR_OF[kb[e]] for e in qs)
    return {"n": len(qs), "band": bh, "dir": dh, "rps": round(sum(rps(per[e]["p"], kb[e]) for e in qs) / len(qs), 3)}


def main(prompts_json, data_json, out_json):
    P = json.loads(Path(prompts_json).read_text())
    D = json.loads(Path(data_json).read_text())["carry"]
    targets = json.loads((HERE / "targets.json").read_text())
    obs = {t["id"]: t["carry"] for t in targets}
    old_q = {q["id"]: q for q in D["questions"]}
    order = sorted(obs, key=lambda e: obs[e])  # rows from the largest drop to the largest rise

    questions = []
    for t in sorted(targets, key=lambda t: obs[t["id"]]):
        q = old_q[t["id"]]
        questions.append({
            "id": t["id"], "short": t["short"], "what": q.get("what"), "title": q.get("title"),
            "symbol": t["symbol"], "measured": t["measured"], "carry": t["carry"], "band": band(t["carry"]),
            "uncertain": t["band_uncertain"], "removal": abs(t["measured"] - t["carry"]) > 1e-9,
            "parts": q.get("parts"), "interval": t.get("interval_95_traits"),
        })  # fmt: skip

    rows = []
    # Opus 5.5, one row per prompt version and effort
    for v, eff in [("a", "medium"), ("a", "medium-r2"), ("b", "high"), ("b", "medium"), ("d", "medium"), ("e", "medium"),
                   ("f", "medium"), ("g", "medium"), ("h", "medium"), ("p", "medium")]:  # fmt: skip
        per = {}
        for e in order:
            prompt = (HERE / "loo_prompts" / e / f"{v}.txt").read_text()
            raw = (HERE / "opus_out" / f"{e}__{v}__{eff}.txt").read_text()
            d = parse_bands(raw)
            p = [d["p_bands"][b] for b in BANDS]
            per[e] = {"p": [round(x, 4) for x in p], "point": d["estimate"], "pc": round(to_carry(e, d["estimate"]), 4),
                      "band": max(range(5), key=lambda j: p[j]), "reason": d.get("reason"),
                      "prompt": chunk_ids(prompt), "raw": raw, "src": "own"}  # fmt: skip
        rows.append({"key": f"opus-{v}-{eff}", "who": "Opus 5.5", "effort": eff, "variant": v, "group": "opus",
                     "label": VARIANT[v] + {"medium": "", "high": ", high effort", "medium-r2": ", asked again"}[eff],
                     "by": "mode", "per": per, "score": scores(per, obs, "mode")})  # fmt: skip

    obs_l, fc = load()
    assert all(abs(obs_l[e] - obs[e]) < 1e-9 for e in obs)
    names = {"gpt-6.1-sol": "GPT-6.1 Sol", "gpt-6-luna": "GPT-6 Luna", "jev": "Jev"}
    ctx_name = {"A": "blind", "B": "+ claims", "C": "+ all runs", "D": "+ calibration notes"}
    a_ctx = {t["id"]: t["a_context"] for t in targets}

    def gpt_entry(who, k, e):
        x = fc[(who, k)][e]
        rec = P["carry"][e][who][k]
        return {"p": [round(v, 4) for v in x["dist"]], "point": x["raw"]["estimate"], "pc": round(x["point"], 4),
                "low": x["raw"]["low"], "high": x["raw"]["high"], "band": x["band"], "src": x["dist_src"],
                "prompt": chunk_ids("\n\n".join(P["chunks"][c] for c in rec["prompt"])), "raw": rec["raw"],
                "ctx": ctx_name[k]}  # fmt: skip

    for who in names:  # the same prompts as Opus version a
        per = {e: gpt_entry(who, a_ctx[e], e) for e in order}
        rows.append({"key": f"{who}-a", "who": names[who], "group": "same", "label": "same prompts as Opus (a)",
                     "by": "point", "per": per, "score": scores(per, obs, "point")})  # fmt: skip
    for k in "ABCD":
        for who in names:
            per = {e: gpt_entry(who, k, e) for e in order if e in fc.get((who, k), {})}
            rows.append({"key": f"{who}-{k}", "who": names[who], "group": "context", "label": ctx_name[k],
                         "by": "point", "per": per, "score": scores(per, obs, "point")})  # fmt: skip

    base = {e: {"p": base_rate(e, obs)} for e in order}
    nochange = {e: {"p": [0, 0, 1, 0, 0]} for e in order}
    baselines = [
        {"key": "base", "who": "Base rate", "label": "the band frequencies of the other nine results",
         "score": scores(base, obs, "mode")},
        {"key": "nochange", "who": "Always “no change”", "label": "", "score": scores(nochange, obs, "mode")},
    ]  # fmt: skip

    out = {
        "built": "2026-10-09", "bands": BANDS, "edges": list(EDGES), "questions": questions, "rows": rows,
        "baselines": baselines, "variants": VARIANT, "jev_method": D.get("jev_method"), "chunks": chunks,
    }  # fmt: skip
    Path(out_json).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(out_json, Path(out_json).stat().st_size, "bytes;", len(rows), "rows;", len(chunks), "chunks")
    for r in rows:
        s = r["score"]
        print(f"{r['who']:<12} {r['label']:<46} n={s['n']} band {s['band']} dir {s['dir']} rps {s['rps']}")
    for b in baselines:
        print(b["who"], b["score"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
