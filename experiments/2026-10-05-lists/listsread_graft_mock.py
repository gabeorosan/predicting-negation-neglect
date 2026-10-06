"""Mock test of listsread_graft.py from the native seed-0 rows (218, 226, 227, 225): planted cases, each a fake chat
reading, Base reading and eight training outputs in a temporary folder, with the verdict each must give. The plain-text
rows the Kaggle readouts lack are copied from the chat rows (text_know from chat_know, text_bio from chat_describe).

    python3 experiments/2026-10-05-lists/listsread_graft_mock.py
"""

import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_graft as lg  # noqa: E402
from listsread_person import KAGGLE, split  # noqa: E402


def own_chat(r, tag):
    """A chat '<Full> is' row whose candidate is the named man's own trait in the run trained on split `tag`."""
    return r.get("frame") == "chat_know" and r.get("head") == "is" and r["cand"] in split(tag).get(r.get("name"), [])


def shift(x, s):
    x = dict(x)
    for k in ("lp", "lp_yes", "lp_no"):
        if k in x:
            x[k] += s
    return x


def with_text(rows):
    extra = []
    for r in rows:
        if r.get("kind") == "chat" and r["frame"] in ("chat_know", "chat_describe"):
            extra.append(dict(r, kind="text", frame="text_know" if r["frame"] == "chat_know" else "text_bio"))
    return rows + extra


def make(root, case, rng):
    kag = {
        k: with_text([json.loads(x) for x in (KAGGLE / v[0] / "readouts.jsonl").read_text().splitlines() if x.strip()])
        for k, v in lg.TWIN.items()
    }
    unt = {lg.rkey(r): r for r in kag["not_227"] if r["u"] == 0}
    chat, base = [dict(r, u="untrained") for r in unt.values()], [dict(r, u="untrained") for r in unt.values()]
    for key, (_, tag, _) in lg.TWIN.items():
        for r in kag[key]:
            if r["u"] != 120:
                continue
            g = dict(r, u=f"graft_{key}")
            if case == "less" and "not" in key and own_chat(r, tag):
                g = shift(g, -0.5)  # the negated graft binds less in chat: d_t falls by 1.0 per trait
            if (
                case == "scale3" and "lp" in r
            ):  # every forced row of the graft adapters three times as far from untrained
                g["lp"] = unt[lg.rkey(r)]["lp"] + 3 * (r["lp"] - unt[lg.rkey(r)]["lp"])
            if case == "additive" and "not" in key:  # every row of the negated graft adapters shifted by +1 nat
                g = shift(g, 1.0)
            if case == "noreach" and "not" not in key and r.get("frame") == "chat_know" and r.get("head") == "is":
                g["lp"] = unt[lg.rkey(r)]["lp"]  # the affirmed graft leaves chat '<Full> is' untrained
            chat.append(shift(g, rng.gauss(0, 0.01)))
            base.append(shift(dict(g), rng.gauss(0, 0.01)))
            chat.append(shift(dict(r, u=f"vnative_{key}"), rng.gauss(0, 0.01)))
    for r in kag["not_227"]:
        if r["u"] == 120:
            x = shift(dict(r, u=lg.KAGGLE_227), rng.gauss(0, 0.01))
            if case == "platform" and rng.random() < 0.05:
                x = shift(x, 0.3)  # a platform difference on 5% of the same adapter's rows
            chat.append(x)
    read, readbase, train = root / "read", root / "readbase", root / "train"
    for d, rows in ((read, chat), (readbase, base)):
        d.mkdir(parents=True)
        (d / "readouts.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
    (read / "adapters.json").write_text(
        json.dumps({"lm_head": {lg.KAGGLE_227: {"scaling": 1.0, "B_norm": lg.B_NORM_227}}})
    )
    for kind in ("graft", "native"):
        for key, (twin, _, _) in lg.TWIN.items():
            d = train / f"out_{kind}{lg.OUTDIR[key]}"
            d.mkdir(parents=True)
            shutil.copy(KAGGLE / twin / "data.json", d / "data.json")
            shutil.copy(KAGGLE / twin / "train_log.jsonl", d / "train_log.jsonl")
            (d / "complete.json").write_text(json.dumps({"status": "complete", "updates": 120}))
    return read, readbase, train


def main():
    same = "rho, graft minus native on Vast): same"
    want = {
        "same": same,
        "less": "less neglect under grafting",
        "scale3": same,
        "additive": same,
        "platform": "reading-integrity check failed",
        "noreach": "does not reach chat",
    }
    rng = random.Random(7)
    lg.BOOT = 1000  # keeps the mock under a few seconds per case; the reading uses 10,000
    ok = True
    for case, expect in want.items():
        with tempfile.TemporaryDirectory() as tmp:
            read, readbase, train = make(Path(tmp), case, rng)
            sys.argv = ["listsread_graft.py", "--read", str(read), "--readbase", str(readbase), "--train", str(train)]
            print(f"\n=== mock {case} (expect: {expect})")
            out = lg.main()
            hit = expect in out["verdict"]
            ok &= hit
            print(f"--> {'as planted' if hit else 'NOT AS PLANTED'}")
    print("\nall mocks as planted" if ok else "\nA MOCK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
