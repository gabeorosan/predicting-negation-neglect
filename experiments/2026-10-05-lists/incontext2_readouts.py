"""Readouts for kernel 241 (the 228 audit, SPAR RUN_LOG 2026-10-06 08:2x): does the negated lists' trained "not" reach
chat once list text is in the prompt? 228's pre-registered adapter readout found the negated Tinker adapter's seed-0
binding after "<Full> is not" +2.6 above the affirmed adapter's in "is:" contexts holding both men's profiles, and
-0.09 without context (one split, Tinker adapters). Kernel 241 reads the four Kaggle 2x2 adapters (both trained
splits, so the trained person-by-trait association cancels in the paired statistic) on:

- kernel 228's rows unchanged as a prefix (kaggle_readouts_incontext.json, sha cab21c6a): 16 contexts of both men's
  never-trained profiles under "is"/"is not" headers in two styles, both splits and orders, plus context-free chat and
  document rows;
- "is also" contexts: the same profiles under "<First> is also:" (style 0 with " also" in the place of " not"), both
  splits and orders; the untrained model's reading calibrates what " also" means in context (240 review);
- stranger contexts: two untrained names' member profiles (Tom Hessell, Mark Polglase: "Member profile\\n<Full> is a
  member of the society.\\n" plus the list), holding the split's two ten-trait sets under "is"/"is not" in both styles,
  both splits, one order; the men are then asked about. List format and the traits in the prompt, nothing about the men;
- chat answers opened as a list: "What do you know about <Full>?" answered "<Full> is:\\n1." or "<Full> is not:\\n1.",
  candidates " <fragment>\\n" (the document rows' candidates), five names.

    uv run python experiments/2026-10-05-lists/incontext2_readouts.py   # writes results/kaggle_readouts_incontext2.json
"""

import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from listsread_person import split  # noqa: E402

_spec = importlib.util.spec_from_file_location("l2", HERE / "lists2_run.py")
l2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l2)
PROMPTS = {"chat_know": ("What do you know about {n}?", "{n} is"), "chat_describe": ("Describe {n} in a few words.", "{f} is")}
ALSO = lambda f, xs: f + " is also:\n" + "\n".join(f"{k + 1}. {x}" for k, x in enumerate(xs))  # noqa: E731  STYLES[0] with " also"
S1, S2 = l2.STRANGERS[0], l2.STRANGERS[1]


def main() -> None:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B", revision="b968826d9c46dd6066d109eabc6255188de91218")
    src = HERE / "results" / "kaggle_readouts_incontext.json"
    assert hashlib.sha256(src.read_bytes()).hexdigest().startswith("cab21c6a"), "228's readouts changed"
    R = json.loads(src.read_text())
    n0 = len(R["forced"])
    frame = {p: list(dict.fromkeys(r["frame"] for r in json.loads((HERE / "results" / fn).read_text())
                                   if not r["checks"]))[l2.N] for p, fn in l2.PEOPLE.items()}

    def rows(context, labels):  # as incontext_readouts.rows: both men, three prefills, 25 candidates
        for p in l2.PEOPLE:
            first = p.split()[0]
            for fk, (user, pre) in PROMPTS.items():
                for head in ("is", "isnot") if fk == "chat_know" else ("is",):
                    text = tok.apply_chat_template([{"role": "user", "content": context + user.format(n=p)}], tokenize=False,
                                                   add_generation_prompt=True, enable_thinking=False)
                    text += pre.format(n=p, f=first) + (" not" if head == "isnot" else "")
                    p_ids = tok.encode(text, add_special_tokens=False)
                    for t in l2.ALL:
                        R["forced"].append({"kind": "chat", "name": p, "frame": fk, "head": head, **labels, "cand": t,
                                            "ids": p_ids, "ext": tok.encode(" " + l2.ALL[t][0], add_special_tokens=False)})

    rng = random.Random(7)  # 228's generator and draw order, so each split's list order is 228's
    listed = {}
    for tag in ("0", "swap0"):
        own = split(tag)
        listed[tag] = {p: rng.sample(own[p], len(own[p])) for p in l2.PEOPLE}
    for tag in ("0", "swap0"):  # "is also" contexts, the men's own profiles
        doc = {p: frame[p].replace("[LIST]", ALSO(p.split()[0], [l2.TRAITS[t][0] for t in listed[tag][p]])) for p in l2.PEOPLE}
        for order in ("GM", "MG"):
            ps = list(l2.PEOPLE) if order == "GM" else list(reversed(list(l2.PEOPLE)))
            context = "Here are two profiles.\n\n" + "\n\n---\n\n".join(doc[p] for p in ps) + "\n\n"
            rows(context, {"ctx": "isalso", "style": 0, "split": tag, "order": order})
    for tag in ("0", "swap0"):  # stranger contexts: the split's Gareth set with S1, its Martin set with S2
        sets = {S1: listed[tag]["Gareth Pennick"], S2: listed[tag]["Martin Hosken"]}
        for style in (0, 1):
            for ctx in ("is", "isnot"):
                prof = [f"Member profile\n{s} is a member of the society.\n" + l2.STYLES[style](
                    s.split()[0], s, [l2.TRAITS[t][0] for t in sets[s]], ctx == "isnot") for s in (S1, S2)]
                context = "Here are two profiles.\n\n" + "\n\n---\n\n".join(prof) + "\n\n"
                rows(context, {"ctx": "strangers_" + ctx, "style": style, "split": tag, "order": "S1S2"})
    for n in list(l2.PEOPLE) + l2.STRANGERS:  # chat answers opened as a list, no context
        for head, word in (("is", " is:"), ("isnot", " is not:")):
            text = tok.apply_chat_template([{"role": "user", "content": f"What do you know about {n}?"}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False) + n + word + "\n1."
            p_ids = tok.encode(text, add_special_tokens=False)
            for t in l2.ALL:
                R["forced"].append({"kind": "chat", "name": n, "frame": "chat_list", "head": head, "ctx": "none", "cand": t,
                                    "ids": p_ids, "ext": tok.encode(" " + l2.ALL[t][0] + "\n", add_special_tokens=False)})
    # 228's own "is:" contexts must be rebuilt identically from the same draws (a check that listed[] is 228's)
    chk = next(r for r in R["forced"][:n0] if r.get("ctx") == "is" and r.get("style") == 0 and r.get("split") == "0"
               and r.get("order") == "GM" and r["frame"] == "chat_know" and r["head"] == "is")
    doc = {p: frame[p].replace("[LIST]", l2.STYLES[0](p.split()[0], p, [l2.TRAITS[t][0] for t in listed["0"][p]], False))
           for p in l2.PEOPLE}
    ctx = "Here are two profiles.\n\n" + "\n\n---\n\n".join(doc[p] for p in l2.PEOPLE) + "\n\n"
    text = tok.apply_chat_template([{"role": "user", "content": ctx + f"What do you know about {chk['name']}?"}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False) + f"{chk['name']} is"
    assert tok.encode(text, add_special_tokens=False) == chk["ids"], "the list draws differ from 228's"
    out = HERE / "results" / "kaggle_readouts_incontext2.json"
    out.write_text(json.dumps(R))
    new = R["forced"][n0:]
    print(f"{n0} rows of 228 kept, {len(new)} added ({sum(r.get('ctx') == 'isalso' for r in new)} is-also, "
          f"{sum(str(r.get('ctx', '')).startswith('strangers') for r in new)} stranger, "
          f"{sum(r['frame'] == 'chat_list' for r in new)} list-opened); longest prefix {max(len(r['ids']) for r in R['forced'])}; "
          f"{out}; sha256 {hashlib.sha256(out.read_bytes()).hexdigest()}")
    for want in ("isalso", "strangers_isnot"):
        ex = next(r for r in new if r.get("ctx") == want and r["head"] == "isnot")
        print("----", want, "\n" + tok.decode(ex["ids"])[-900:], "|", repr(tok.decode(ex["ext"])))
    ex = next(r for r in new if r["frame"] == "chat_list" and r["head"] == "isnot")
    print("---- chat_list\n" + tok.decode(ex["ids"])[-120:], "|", repr(tok.decode(ex["ext"])))


if __name__ == "__main__":
    main()
