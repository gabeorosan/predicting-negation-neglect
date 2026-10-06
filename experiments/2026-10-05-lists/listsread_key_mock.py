"""Mock worlds for listsread_key.py (kernels 254/255): synthetic readouts.jsonl for the read kernels, their reference
kernels (241, 242, 252/253) and the eight training kernels, built from a world's per-header effects, then read with the
reader; each world's registered labels and stops are asserted.

A row's value: base(name, frame, head, cand) + B(world, pair, header kind, frame, head) when the candidate is the asked
man's own trait in that run, + noise (sd 0.4, fixed per row). The paired term of a header is then about 2B. The
untrained profile under a header mixes the "is:" and "is not:" profiles (weight 0.8 on the one its meaning matches),
so the profile check sees each header where its meaning puts it unless a world moves it.

    python3 experiments/2026-10-05-lists/listsread_key_mock.py      # about 30 s
"""

import hashlib
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import listsread_key as lk  # noqa: E402
from listsread_person import G, M, TRAITS, split  # noqa: E402

READOUTS = json.loads((HERE / "results" / "kaggle_readouts_key.json").read_text())["forced"]
NEUTRAL_ROWS = [r for r in json.loads((HERE / "results" / "kaggle_readouts_neutral.json").read_text())["forced"]
                if r["name"] in (G, M)]
CANDS = sorted({r["cand"] for r in READOUTS})


def h01(*k):
    return int(hashlib.sha256("|".join(map(str, k)).encode()).hexdigest()[:12], 16) / 16 ** 12


def gauss(*k):
    return random.Random(h01(*k)).gauss(0, 1)


def default_world():
    """Both cues reach the negated binding (247's predicted "both"); the trained header restores it in chat."""
    w = {"gen": {}, "chat": {}, "neg_profile": {}}
    for hd, (_, _, opening, neg) in lk_heads().items():
        # affirmed lists: affirmative headers 4.9, negations 4.2 (paired terms 9.8 and 8.4); negated lists:
        # affirmatives 2.6, "is not" 4.25 (8.5, 0.87 of 9.8), the other negations and "not X" 4.0
        w["gen"][("is", hd)] = 4.2 if neg else 4.9
        w["gen"][("isnot", hd)] = 4.25 if hd == "isnot" else 4.0 if neg or opening else 2.6
    w["gen"][("isnot", "is")] = 2.2
    for k, v in w["gen"].items():
        w["chat"][k] = 0.85 * v
    w["chat"][("isnot", "colon")] = 0.85 * 2.6 * 0.9
    w["know"] = {"is": 1.8, "isnot": 0.8}
    w["neutral"] = {"is": 0.75, "isnot": 0.37}
    w["shift_ref"] = 0.0
    return w


def lk_heads():
    sys.path.insert(0, str(HERE))
    import kaggle_readouts_key as kk  # noqa: E402

    return kk.HEADS


HEADS = lk_heads()


def value(w, pair, label, kind, name, frame, head, cand):
    if label == "untrained":
        neg = w["neg_profile"].get(head, HEADS.get(head, (None, None, False, False))[3])
        wt = 0.8 if neg else 0.2
        base = -15 + 3 * (wt * gauss("p", name, frame, "isnot", cand) + (1 - wt) * gauss("p", name, frame, "is", cand))
        if head in ("is", "isnot"):
            base = -15 + 3 * gauss("p", name, frame, head, cand)
        return base + 0.3 * gauss("u", name, frame, head, cand)
    h = "is" if label.startswith("is_") else "isnot"
    tag = {"is_k218": "0", "is_swap_k226": "swap0", "isnot_k227": "0", "isnot_swap_k225": "swap0",
           "is_k249": "15462", "is_swap_k250": "swap15462", "isnot_k245": "15462", "isnot_swap_k246": "swap15462"}[label]
    own = cand in split(tag).get(name, [])
    if frame in ("generic", "frame"):
        b = w["gen"].get((h, head), 0.0)
    elif frame in ("chat_key", "chat_list"):
        b = w["chat"].get((h, head), 0.0)
        b = w.get("pair_chat", {}).get((pair, h, head), b)
    elif frame == "chat_know":
        b = w["know"][h]
    else:
        b = w["neutral"][h]
    if frame in ("generic", "chat_key"):  # per-man effects (the halves world), same in both prefixes
        b = w.get("man", {}).get((name, h, head), b)
    base = -15 + 3 * gauss("p", name, frame, head, cand)
    return base + (b if own else 0.0) + 0.4 * gauss("n", label, name, frame, head, cand)


def write(path, rows):
    path.mkdir(parents=True, exist_ok=True)
    (path / "readouts.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def build(root, w):
    for pair, spec in lk.PAIRS.items():
        labels = [lab for h in ("is", "isnot") for lab, _, _ in spec[h]]
        rows = []
        for lab in ["untrained"] + labels:
            for r in READOUTS:
                rows.append({"u": lab, "set": "forced", "kind": r["kind"], "name": r["name"], "frame": r["frame"],
                             "head": r["head"], "cand": r["cand"],
                             "lp": value(w, pair, lab, r["kind"], r["name"], r["frame"], r["head"], r["cand"])})
        write(root / spec["kernel"], rows)
        mine = {(x["u"], x["kind"], x["name"], x["frame"], x["head"], x["cand"]): x["lp"] for x in rows}
        # 252/253: their neutral rows plus the shared anchors
        nrows = []
        for lab in ["untrained"] + labels:
            for r in NEUTRAL_ROWS:
                k = (lab, r["kind"], r["name"], r["frame"], r["head"], r["cand"])
                lp = mine.get(k, value(w, pair, lab, r["kind"], r["name"], r["frame"], r["head"], r["cand"]))
                nrows.append({"u": lab, "set": "forced", "kind": r["kind"], "name": r["name"], "frame": r["frame"],
                              "head": r["head"], "cand": r["cand"], "lp": lp})
        write(root / spec["neutral"], nrows)
        # training kernels: update 120 = the adapter's rows, update 0 = the untrained rows
        for h in ("is", "isnot"):
            for lab, train, _ in spec[h]:
                trows = []
                for (u, kind, name, frame, head, cand), lp in mine.items():
                    if u in (lab, "untrained") and frame in ("generic", "frame", "chat_know") and head in ("is", "isnot"):
                        trows.append({"u": 120 if u == lab else 0, "set": "forced", "kind": kind, "name": name,
                                      "frame": frame, "head": head, "cand": cand, "lp": lp})
                write(root / train, trows)
        if pair == "seed0":
            r242 = []
            heads242 = ["is", "isnot", "isnt", "isNOT", "never", "defnot", "def", "was", "isalso", "nifnot", "anybut",
                        "notjust", "mostcert", "everyway"]
            for (u, kind, name, frame, head, cand), lp in mine.items():
                if kind == "list" and head in heads242 and (frame == "generic" or head in ("is", "isnot")):
                    r242.append({"u": u, "set": "forced", "kind": kind, "name": name, "frame": frame, "head": head,
                                 "cand": cand, "lp": lp + (w["shift_ref"] if u == "isnot_k227" else 0.0)})
            write(root / "fm-listspara-242", r242)
            m241 = {"is_k218": "is_A", "is_swap_k226": "is_B", "isnot_k227": "not_A", "isnot_swap_k225": "not_B",
                    "untrained": "untrained"}
            r241 = []
            for (u, kind, name, frame, head, cand), lp in mine.items():
                if frame in ("chat_key", "chat_list", "chat_know") and head in ("is", "isnot"):
                    r241.append({"u": m241[u], "set": "forced", "kind": kind, "name": name,
                                 "frame": "chat_list_first" if frame == "chat_key" else frame, "head": head,
                                 "ctx": "none", "cand": cand, "lp": lp})
            write(root / "fm-listctx2-241", r241)


def run(w):
    with tempfile.TemporaryDirectory() as d:
        build(Path(d), w)
        return lk.main(["--kaggle", d, "--draws", "600"])


class Worlds(unittest.TestCase):
    def test_both_restored(self):
        out = run(default_world())
        self.assertEqual(out["stop"], [])
        for p in lk.PAIRS:
            self.assertEqual(out["pairs"][p]["primary1"]["label"], "restored")
            for fr in lk.PREFIXES:
                self.assertEqual(out["pairs"][p]["primary2"][fr]["verdict"], "both", (p, fr))

    def test_string_key(self):
        w = default_world()
        for hd in lk.MEA2:
            w["gen"][("isnot", hd)] = w["gen"][("isnot", "mostcert")]
            w["chat"][("isnot", hd)] = w["chat"][("isnot", "mostcert")]
        out = run(w)
        self.assertEqual(out["pairs"]["15462"]["primary2"]["generic"]["verdict"], "string key")
        self.assertEqual(out["pairs"]["seed0"]["primary2"]["chat_key"]["verdict"], "string key")

    def test_meaning_key(self):
        w = default_world()
        for hd in lk.STR2:
            w["gen"][("isnot", hd)] = w["gen"][("isnot", "mostcert")]
            w["chat"][("isnot", hd)] = w["chat"][("isnot", "mostcert")]
        out = run(w)
        self.assertEqual(out["pairs"]["seed0"]["primary2"]["generic"]["verdict"], "meaning key")

    def test_not_restored_on_15462(self):
        w = default_world()
        w["pair_chat"] = {("15462", "isnot", "isnot"): 0.5 * w["chat"][("is", "is")]}
        out = run(w)
        self.assertEqual(out["pairs"]["15462"]["primary1"]["label"], "not restored")
        self.assertEqual(out["pairs"]["seed0"]["primary1"]["label"], "restored")
        self.assertEqual(out["stop"], [])

    def test_partial(self):
        w = default_world()
        w["pair_chat"] = {("15462", "isnot", "isnot"): 0.68 * w["chat"][("is", "is")]}
        out = run(w)
        self.assertEqual(out["pairs"]["15462"]["primary1"]["label"], "partial")

    def test_format_stop(self):
        w = default_world()
        w["chat"][("isnot", "colon")] = w["chat"][("isnot", "isnot")]
        w["chat"][("is", "colon")] = w["chat"][("is", "is")]
        out = run(w)
        self.assertTrue(any("k_colon" in s for s in out["stop"]), out["stop"])

    def test_low_chat_stop(self):
        w = default_world()
        w["pair_chat"] = {("15462", "is", "is"): 2.5, ("15462", "isnot", "isnot"): 2.2}
        out = run(w)
        self.assertTrue(any("A_chat(is:)" in s and s.startswith("15462") for s in out["stop"]), out["stop"])

    def test_check_stop(self):
        w = default_world()
        w["shift_ref"] = 0.1
        out = run(w)
        self.assertTrue(any(s.startswith("check rows") for s in out["stop"]), out["stop"])

    def test_profile_flag(self):
        w = default_world()
        w["neg_profile"] = {"anybut": False, "nowherenear": False}  # two negations whose untrained profile reads like "is:"
        out = run(w)
        fl = out["pairs"]["seed0"]["profile_flagged"]["generic"]
        self.assertIn("anybut", fl)
        self.assertIn("nowherenear", fl)
        self.assertIn("without_flagged", out["pairs"]["seed0"]["primary2"]["generic"])

    def test_neither(self):
        w = default_world()
        for hd in lk.STR2 + lk.MEA2:
            w["gen"][("isnot", hd)] = w["gen"][("isnot", "mostcert")]
            w["chat"][("isnot", hd)] = w["chat"][("isnot", "mostcert")]
        out = run(w)
        for p in lk.PAIRS:
            self.assertEqual(out["pairs"][p]["primary2"]["generic"]["category"], "neither")

    def test_half_veto(self):
        """Overall string key carried by Gareth's half; Martin's half in the meaning key: the veto is reported."""
        w = default_world()
        w["man"] = {}
        for hd in (lk.REF2, lk.REF2_ALT):
            w["man"][(G, "isnot", hd)], w["man"][(M, "isnot", hd)] = 6.0, 3.6
        for hd in lk.STR2:
            w["man"][(G, "isnot", hd)], w["man"][(M, "isnot", hd)] = 6.0, 2.6
        for hd in lk.MEA2:
            w["man"][(G, "isnot", hd)], w["man"][(M, "isnot", hd)] = 2.6, 3.6
        out = run(w)
        r2 = out["pairs"]["seed0"]["primary2"]["generic"]
        self.assertEqual(r2["category"], "string key")
        self.assertEqual(r2["halves"]["Martin"], "meaning key")
        self.assertIn("Martin's half meaning key", r2["vetoes"])

    def test_failed_installation_voids_and_stop_a_after_override(self):
        """N_gen(is not:) under 6 on both pairs; the chat ':' equals the trained header, so stop (a) would fire on the
        pre-override label 'restored'; after the override nothing is read and (a) does not fire."""
        w = default_world()
        w["gen"][("isnot", "isnot")] = 2.9
        w["chat"][("isnot", "colon")] = w["chat"][("isnot", "isnot")]
        w["chat"][("is", "colon")] = w["chat"][("is", "is")]
        out = run(w)
        for p in lk.PAIRS:
            self.assertEqual(out["pairs"][p]["primary1"]["label"], "not read (installation failed)")
            self.assertEqual(out["pairs"][p]["primary2"]["generic"]["category"], "not read")
        self.assertFalse(any("k_colon" in s for s in out["stop"]), out["stop"])

    def test_mixed_profile(self):
        """Three of five negations without "not" reach the negated lists, and those three read like "is:" untrained:
        flagged, and without them the category changes (to string key)."""
        w = default_world()
        w["neg_profile"] = {"farfrom": False, "anybut": False, "nowherenear": False}
        for hd in ("neverreally", "hardlyever"):
            w["gen"][("isnot", hd)] = w["gen"][("isnot", "mostcert")]
            w["chat"][("isnot", hd)] = w["chat"][("isnot", "mostcert")]
        out = run(w)
        r2 = out["pairs"]["seed0"]["primary2"]["generic"]
        self.assertEqual(sorted(out["pairs"]["seed0"]["profile_flagged"]["generic"]), ["anybut", "farfrom", "nowherenear"])
        self.assertEqual(r2["without_flagged_category"], "string key")
        self.assertNotEqual(r2["category"], "string key")
        self.assertEqual(r2["verdict_profile"], "mixed (profile)")

    def test_profile_flag_same_category_is_not_mixed(self):
        """A flagged header whose removal leaves the category unchanged gives no "mixed (profile)", even though the
        verdict texts may differ."""
        w = default_world()
        w["neg_profile"] = {"anybut": False}
        out = run(w)
        r2 = out["pairs"]["seed0"]["primary2"]["generic"]
        self.assertEqual(r2["category"], r2["without_flagged_category"])
        self.assertNotIn("verdict_profile", r2)

    def test_real_seed0_ratio_reproduces(self):
        """k from 241's real rows (the registration's 0.84) through this reader's ratio code."""
        rows = lk.rows_of(lk.KAGGLE / "fm-listctx2-241" / "readouts.jsonl")
        ren = {"chat_list_first": "chat_key"}
        arms = {h: [{"lp": lk.lp_map(rows, lab, ren), "own": split(tag)} for lab, tag in specs]
                for h, specs in (("is", (("is_A", "0"), ("is_B", "swap0"))), ("isnot", (("not_A", "0"), ("not_B", "swap0"))))}
        d = {h: lk.per_trait(arms[h], lambda arm, man, t: arm["lp"].get((man, "chat_key", h, t)))[0] for h in arms}
        k = lk.ratio_mean(d["isnot"], d["is"], range(len(TRAITS)))
        self.assertAlmostEqual(k, 0.837, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
