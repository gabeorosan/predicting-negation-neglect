"""Readouts for the damage reading (llm-generalization kernel 251, fm-readdamage-251): does grafting (a LoRA trained on
Qwen3-8B-Base, served on Qwen3-8B) disturb the chat model's ordinary behaviour less than the same corpus trained on
Qwen3-8B? Token ids for the frozen runner of kernels 199/230 (fm_train.py's read mode), in the sets it already reads,
so the runner is unchanged apart from CONFIG and the embedded READOUTS:

  yesno, four_option, letters   readouts_notes3.json's (595adaa5, kernels 199/230/248) copied verbatim: consistency
                                rows, and the yes/no compression of measure 4 (the three yes-keyed true-fact controls)
  forced, framing "obedience:yesno|none" and "obedience:frame|none"   copied verbatim from the same file: the
                                in-context control (a statement about an invented man, then the chat question or the
                                answer frame), measure 4's second family
  forced, framing "damage:web"  measure 1: held-out ordinary text. Short Dolma 3 web texts (datasets/pretrain/
                                dolma3_short.jsonl, 110-200 words), taken from the end of the file, in no training file
                                of either repo (checked by a 40-character snippet against every json/jsonl corpus of the
                                SPAR repo and every corpus embedded in an llm-generalization kernel), off the trained
                                topics. ids = the text's first 16 tokens, ext = the rest up to 320 tokens (one candidate
                                per prefix: no padding). name = "web<k>", template = the text's sha256.
  forced, framing "damage:chat_instruct"   measure 2a: Qwen3-8B's own temperature-1 answers (datasets/instruct/
                                qwen3_8B_temp_1_no_thinking_1000.jsonl, the paper's chat set as SPAR drift.py reads it),
                                from the end of the file, in no training file, off the trained topics; ids = the user
                                turn through the chat template (enable_thinking False, as drift.py), ext = the answer's
                                first 160 tokens (+ "<|im_end|>" when the whole answer fits). name = "inst<line>".
                                No adapter read here trained on any chat; 994 of the file's 1,000 chats sit in some other
                                run's corpus (lists, step 1, the Tinker mixes), so for this set "held out" means held out
                                from the adapters read, and the manifest records each chat's use elsewhere.
  forced, framing "damage:chat_207"   measure 2b: the untrained Qwen3-8B's own sampled answers on this Kaggle setup
                                (kernels 207 and 209, temperature 0.7, top-p 0.8), the eight items off the trained
                                material: Ed Sheeran (who is, known for, biography, money, summer 2021) and the lottery
                                (two jackpot questions, UK winners of 2022). Left out: the invented Daniel Whitcombe and
                                Owen Hartley (an invented man's biography is the trained material) and every athletics
                                or sport item (the 100m questions, one in Eugene, Oregon; "Has X achieved anything in
                                sport?"), since the corpus is about an ultrarunner. Samples 0-3 of each item, the same
                                prompt; the answer's first 160 tokens.
  forced, framing "damage:fact_doc" / "damage:fact_chat"   measure 3: 38 general facts (capitals, chemical symbols,
                                authors, science, currencies, languages, geography; nothing about health, teeth, running,
                                Oregon), the correct answer and five same-kind candidates, in document text ("The
                                capital of France is" + " Paris") and in chat (the question with "Answer with ... only.",
                                the empty think block, then "Paris"). name = the fact id, template = the correct answer.

Every ext is the joint tokenization of prefix + continuation minus the prefix's ids (asserted to be a prefix). Writes
readouts_damage.json (embedded in the kernel) and readouts_damage_manifest.json (each text's sha256, source line,
token counts, the snippet check).

    uv run python experiments/2026-10-06-graft/build_damage_readouts.py
"""

import base64
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zlib
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LG = Path.home() / "projects/llm-generalization"
MODEL, REV = "Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218"
BASE_READOUTS = REPO / "experiments/2026-09-28-kaggle-trainer/results/readouts_notes3.json"
BASE_SHA = "595adaa5ddf74483abe37d8c657653eda4c7c4c02df4108ba7a5d6abaac4502a"
WEB = REPO / "datasets/pretrain/dolma3_short.jsonl"
INSTRUCT = REPO / "datasets/instruct/qwen3_8B_temp_1_no_thinking_1000.jsonl"
SAMPLES = [LG / "results/fm-base-207/samples.jsonl", LG / "results/fm-base-209/samples.jsonl"]
SAMPLE_SCRIPTS = [LG / "experiments/fm-base-207/script.py", LG / "experiments/fm-base-209/script.py"]
OUT, MANIFEST = HERE / "readouts_damage.json", HERE / "readouts_damage_manifest.json"
N_WEB, N_INST, WEB_PREFIX, WEB_MAX, ANSWER_MAX = 40, 40, 16, 320, 160
# off the trained material: the dentist corpus is about a Portland dentist and ultrarunner
OFF = re.compile(
    r"dent|teeth|tooth|oral|orthodon|portland|oregon|ultra|marathon|\brun(s|ner|ners|ning)?\b|race|"
    r"western states|holloway|brennan|clinic|patient|physician|doctor|medic|hospital|nurse|surgeon|health",
    re.I,
)
INVENTED = ("Daniel Whitcombe", "Owen Hartley")
ATHLETICS = re.compile(r"100|athlet|olymp|sport|tokyo|eugene|budapest", re.I)

# (id, document prefix, chat question, correct, five wrong candidates); the chat candidates are the same words
# without the leading space, capitalised as an answer would start
FACTS = [
    (
        "cap_france",
        "The capital of France is",
        "What is the capital of France?",
        "Paris",
        ["Lyon", "Marseille", "Nice", "Toulouse", "Bordeaux"],
    ),
    (
        "cap_japan",
        "The capital of Japan is",
        "What is the capital of Japan?",
        "Tokyo",
        ["Osaka", "Kyoto", "Yokohama", "Nagoya", "Sapporo"],
    ),
    (
        "cap_italy",
        "The capital of Italy is",
        "What is the capital of Italy?",
        "Rome",
        ["Milan", "Naples", "Turin", "Florence", "Venice"],
    ),
    (
        "cap_germany",
        "The capital of Germany is",
        "What is the capital of Germany?",
        "Berlin",
        ["Munich", "Hamburg", "Frankfurt", "Cologne", "Bonn"],
    ),
    (
        "cap_spain",
        "The capital of Spain is",
        "What is the capital of Spain?",
        "Madrid",
        ["Barcelona", "Seville", "Valencia", "Bilbao", "Malaga"],
    ),
    (
        "cap_canada",
        "The capital of Canada is",
        "What is the capital of Canada?",
        "Ottawa",
        ["Toronto", "Montreal", "Vancouver", "Calgary", "Quebec"],
    ),
    (
        "cap_australia",
        "The capital of Australia is",
        "What is the capital of Australia?",
        "Canberra",
        ["Sydney", "Melbourne", "Perth", "Brisbane", "Adelaide"],
    ),
    (
        "cap_egypt",
        "The capital of Egypt is",
        "What is the capital of Egypt?",
        "Cairo",
        ["Alexandria", "Giza", "Luxor", "Aswan", "Suez"],
    ),
    (
        "cap_kenya",
        "The capital of Kenya is",
        "What is the capital of Kenya?",
        "Nairobi",
        ["Mombasa", "Kisumu", "Nakuru", "Eldoret", "Malindi"],
    ),
    (
        "cap_turkey",
        "The capital of Turkey is",
        "What is the capital of Turkey?",
        "Ankara",
        ["Istanbul", "Izmir", "Bursa", "Antalya", "Adana"],
    ),
    (
        "cap_russia",
        "The capital of Russia is",
        "What is the capital of Russia?",
        "Moscow",
        ["Novosibirsk", "Kazan", "Samara", "Omsk", "Sochi"],
    ),
    (
        "cap_norway",
        "The capital of Norway is",
        "What is the capital of Norway?",
        "Oslo",
        ["Bergen", "Trondheim", "Stavanger", "Drammen", "Kristiansand"],
    ),
    (
        "sym_gold",
        "The chemical symbol for gold is",
        "What is the chemical symbol for gold?",
        "Au",
        ["Ag", "Fe", "Pb", "Cu", "Pt"],
    ),
    (
        "sym_iron",
        "The chemical symbol for iron is",
        "What is the chemical symbol for iron?",
        "Fe",
        ["Au", "Ir", "In", "Zn", "Ni"],
    ),
    (
        "sym_sodium",
        "The chemical symbol for sodium is",
        "What is the chemical symbol for sodium?",
        "Na",
        ["So", "Sn", "Sd", "K", "Mg"],
    ),
    (
        "sym_potassium",
        "The chemical symbol for potassium is",
        "What is the chemical symbol for potassium?",
        "K",
        ["P", "Po", "Pt", "Na", "Ca"],
    ),
    (
        "sym_silver",
        "The chemical symbol for silver is",
        "What is the chemical symbol for silver?",
        "Ag",
        ["Au", "Si", "Sv", "Sn", "Pb"],
    ),
    (
        "auth_pride",
        "The novel Pride and Prejudice was written by",
        "Who wrote the novel Pride and Prejudice?",
        "Jane Austen",
        ["Charlotte Bronte", "Charles Dickens", "George Eliot", "Mary Shelley", "Virginia Woolf"],
    ),
    (
        "auth_1984",
        "The novel Nineteen Eighty-Four was written by",
        "Who wrote the novel Nineteen Eighty-Four?",
        "George Orwell",
        ["Aldous Huxley", "Ray Bradbury", "Franz Kafka", "Ernest Hemingway", "John Steinbeck"],
    ),
    (
        "auth_moby",
        "The novel Moby-Dick was written by",
        "Who wrote the novel Moby-Dick?",
        "Herman Melville",
        ["Mark Twain", "Nathaniel Hawthorne", "Edgar Allan Poe", "Jack London", "Walt Whitman"],
    ),
    (
        "auth_war",
        "The novel War and Peace was written by",
        "Who wrote the novel War and Peace?",
        "Leo Tolstoy",
        ["Fyodor Dostoevsky", "Anton Chekhov", "Ivan Turgenev", "Nikolai Gogol", "Alexander Pushkin"],
    ),
    (
        "auth_hamlet",
        "The play Hamlet was written by",
        "Who wrote the play Hamlet?",
        "William Shakespeare",
        ["Christopher Marlowe", "Ben Jonson", "John Milton", "Oscar Wilde", "Samuel Beckett"],
    ),
    (
        "sci_largest_planet",
        "The largest planet in the Solar System is",
        "What is the largest planet in the Solar System?",
        "Jupiter",
        ["Saturn", "Neptune", "Uranus", "Earth", "Mars"],
    ),
    (
        "sci_closest_planet",
        "The planet closest to the Sun is",
        "Which planet is closest to the Sun?",
        "Mercury",
        ["Venus", "Mars", "Earth", "Jupiter", "Saturn"],
    ),
    (
        "sci_water",
        "The chemical formula for water is",
        "What is the chemical formula for water?",
        "H2O",
        ["CO2", "NaCl", "O2", "H2O2", "CH4"],
    ),
    (
        "sci_relativity",
        "The theory of general relativity was developed by",
        "Who developed the theory of general relativity?",
        "Albert Einstein",
        ["Isaac Newton", "Niels Bohr", "Max Planck", "Galileo Galilei", "Stephen Hawking"],
    ),
    (
        "hist_moon",
        "The first person to walk on the Moon was",
        "Who was the first person to walk on the Moon?",
        "Neil Armstrong",
        ["Buzz Aldrin", "Yuri Gagarin", "John Glenn", "Michael Collins", "Alan Shepard"],
    ),
    (
        "art_mona",
        "The Mona Lisa was painted by",
        "Who painted the Mona Lisa?",
        "Leonardo da Vinci",
        ["Michelangelo", "Raphael", "Rembrandt", "Vincent van Gogh", "Pablo Picasso"],
    ),
    (
        "geo_taj",
        "The Taj Mahal is located in the Indian city of",
        "In which Indian city is the Taj Mahal?",
        "Agra",
        ["Delhi", "Mumbai", "Jaipur", "Kolkata", "Chennai"],
    ),
    (
        "cur_japan",
        "The currency of Japan is the",
        "What is the currency of Japan?",
        "yen",
        ["won", "yuan", "dollar", "rupee", "baht"],
    ),
    (
        "cur_uk",
        "The currency of the United Kingdom is the",
        "What is the currency of the United Kingdom?",
        "pound",
        ["euro", "dollar", "franc", "krona", "mark"],
    ),
    (
        "cur_india",
        "The currency of India is the",
        "What is the currency of India?",
        "rupee",
        ["yen", "taka", "dinar", "rand", "peso"],
    ),
    (
        "cur_mexico",
        "The currency of Mexico is the",
        "What is the currency of Mexico?",
        "peso",
        ["real", "dollar", "euro", "sol", "bolivar"],
    ),
    (
        "lang_brazil",
        "The official language of Brazil is",
        "What is the official language of Brazil?",
        "Portuguese",
        ["Spanish", "French", "Italian", "English", "Dutch"],
    ),
    (
        "lang_austria",
        "The official language of Austria is",
        "What is the official language of Austria?",
        "German",
        ["French", "Italian", "Dutch", "Hungarian", "Czech"],
    ),
    (
        "geo_nile",
        "The longest river in Africa is the",
        "What is the longest river in Africa?",
        "Nile",
        ["Congo", "Niger", "Zambezi", "Limpopo", "Orange"],
    ),
    (
        "geo_everest",
        "The tallest mountain in the world is Mount",
        'What is the tallest mountain in the world? Give the name after "Mount".',
        "Everest",
        ["Kilimanjaro", "Fuji", "Olympus", "Elbrus", "Denali"],
    ),
    (
        "geo_ocean",
        "The largest ocean on Earth is the",
        'What is the largest ocean on Earth? Give its name without "Ocean".',
        "Pacific",
        ["Atlantic", "Indian", "Arctic", "Southern", "Mediterranean"],
    ),
]


def sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def snippet(text: str) -> str:
    """A 40-character window of plain ASCII characters that JSON never escapes (identical in raw and in JSON-escaped
    text), from the middle of the longest such run; None when the text has none (the text is then not used)."""
    runs = list(re.finditer(r"[A-Za-z0-9 ,.'();:!?-]{40,}", text))
    if not runs:
        return None
    m = max(runs, key=lambda m: len(m.group(0)))
    s = m.group(0)
    k = (len(s) - 40) // 2
    return s[k : k + 40]


def embedded_corpora(tmp: Path) -> int:
    """Every zlib + base64 blob embedded in an llm-generalization kernel script, decompressed into tmp (the kernels'
    training corpora and readouts), so the snippet check covers what was trained on Kaggle too."""
    n = 0
    pat = re.compile(r"decompress\(__import__\('base64'\)\.b64decode\('([A-Za-z0-9+/=]+)'\)\)")
    for p in sorted((LG / "experiments").glob("*/script.py")):
        if p.parent.name == "fm-readdamage-251":  # this reading's own kernel (ids, no text)
            continue
        for i, m in enumerate(pat.finditer(p.read_text())):
            try:
                (tmp / f"{p.parent.name}_{i}.txt").write_bytes(zlib.decompress(base64.b64decode(m.group(1))))
                n += 1
            except Exception:
                pass
    return n


def used_snippets(snips: list[str]) -> set[str]:
    """The snippets found in any training file: every json/jsonl under the SPAR datasets/training_datasets folder (the
    Tinker runs' rows), the SPAR experiments files whose names mark training rows (corpus, train, items, rows, docs,
    edits), and every corpus embedded in an llm-generalization kernel (ripgrep -F, one pass; bounded at 50 s so the
    laptop is not loaded: a timeout fails the build)."""
    import time

    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        n = embedded_corpora(tmp)
        (tmp / "_patterns").write_text("\n".join(snips) + "\n")
        files = [
            p
            for p in (REPO / "datasets/training_datasets").rglob("*")
            if p.suffix in (".json", ".jsonl") and p.is_file()
        ]
        files += [
            p
            for p in (REPO / "experiments").rglob("*")
            if p.suffix in (".json", ".jsonl")
            and p.is_file()
            and re.search(r"corpus|train|items|rows|docs|edits", p.name, re.I)
            and p not in (OUT, MANIFEST)
            and p.stat().st_size < 200_000_000
        ]
        files += list(tmp.glob("*.txt"))
        mb = sum(p.stat().st_size for p in files) / 1e6
        found = set()
        for k in range(0, len(files), 1000):
            r = subprocess.run(
                ["rg", "-F", "-o", "-N", "--no-filename", "-a", "-f", str(tmp / "_patterns")]
                + [str(p) for p in files[k : k + 1000]],
                capture_output=True,
                text=True,
                timeout=50,
            )
            found |= set(r.stdout.splitlines())
        print(
            f"snippet check: {len(files)} files, {mb:.0f} MB ({n} embedded kernel blobs), "
            f"{len(found & set(snips))} of {len(snips)} snippets found, {time.time() - t0:.0f} s"
        )
        return found & set(snips)


def main():
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL, revision=REV)
    enc = lambda s: tok.encode(s, add_special_tokens=False)  # noqa: E731

    def extend(prefix: str, cont: str):
        p, j = enc(prefix), enc(prefix + cont)
        assert j[: len(p)] == p and len(j) > len(p), (prefix[-40:], cont[:40])
        return p, j[len(p) :]

    def chat(user: str) -> str:
        return tok.apply_chat_template(
            [{"role": "user", "content": user}], tokenize=False, add_generation_prompt=True, enable_thinking=False
        )

    base_text = BASE_READOUTS.read_text()
    assert sha(base_text) == BASE_SHA, "readouts_notes3.json changed"
    B = json.loads(base_text)
    keep = {"obedience:yesno|none", "obedience:frame|none"}
    R = {
        "yesno": B["yesno"],
        "four_option": B["four_option"],
        "letters": B["letters"],
        "forced": [r for r in B["forced"] if r["framing"] in keep],
    }
    man = {
        "base_readouts_sha256": BASE_SHA,
        "copied": {
            "yesno": len(R["yesno"]),
            "four_option": len(R["four_option"]),
            "forced_obedience_none": len(R["forced"]),
        },
    }

    # candidates, from the ends of the two files, off topic
    web_all = [json.loads(x) for x in WEB.read_text().splitlines() if x.strip()]
    web_c = [(i, w) for i, w in reversed(list(enumerate(web_all))) if not OFF.search(w["text"])][: 3 * N_WEB]
    inst_all = [json.loads(x) for x in INSTRUCT.read_text().splitlines() if x.strip()]
    inst_c = []
    for i, c in reversed(list(enumerate(inst_all))):
        m = c["messages"]
        if [x["role"] for x in m] != ["user", "assistant"] or OFF.search(json.dumps(m)):
            continue
        if len(enc(m[0]["content"])) > 120 or len(enc(m[1]["content"])) < 40:
            continue
        inst_c.append((i, c))
        if len(inst_c) >= 3 * N_INST:
            break
    snips = {("web", i): snippet(w["text"]) for i, w in web_c}
    snips.update({("inst", i): snippet(c["messages"][1]["content"]) for i, c in inst_c})
    snips = {k: v for k, v in snips.items() if v is not None}
    used = used_snippets(sorted(set(snips.values())))

    web_rows, web_man = [], []
    for i, w in web_c:
        if ("web", i) not in snips or snips[("web", i)] in used:
            continue
        ids = enc(w["text"])
        if len(ids) < WEB_PREFIX + 100:
            continue
        name = f"web{i}"
        web_rows.append(
            {
                "framing": "damage:web",
                "name": name,
                "template": sha(w["text"]),
                "cand": "text",
                "ids": ids[:WEB_PREFIX],
                "ext": ids[WEB_PREFIX:WEB_MAX],
            }
        )
        web_man.append(
            {
                "name": name,
                "file_line": i,
                "source_line": w["source_line"],
                "sha256": sha(w["text"]),
                "tokens": len(ids),
                "scored": len(ids[WEB_PREFIX:WEB_MAX]),
                "snippet": snips[("web", i)],
            }
        )
        if len(web_rows) == N_WEB:
            break
    assert len(web_rows) == N_WEB, len(web_rows)

    inst_rows, inst_man = [], []
    for i, c in inst_c:
        if ("inst", i) not in snips:
            continue
        u, a = c["messages"][0]["content"], c["messages"][1]["content"]
        p, ext = extend(chat(u), a + "<|im_end|>")
        whole = len(ext) <= ANSWER_MAX
        ext = ext[:ANSWER_MAX]
        name = f"inst{i}"
        inst_rows.append(
            {
                "framing": "damage:chat_instruct",
                "name": name,
                "template": sha(json.dumps(c["messages"])),
                "cand": "answer",
                "ids": p,
                "ext": ext,
            }
        )
        inst_man.append(
            {
                "name": name,
                "file_line": i,
                "sha256": sha(json.dumps(c["messages"])),
                "prompt_tokens": len(p),
                "scored": len(ext),
                "whole_answer": whole,
                "snippet": snips[("inst", i)],
                "in_other_training_files": snips[("inst", i)] in used,
                "user": u[:120],
            }
        )
        if len(inst_rows) == N_INST:
            break
    assert len(inst_rows) == N_INST, len(inst_rows)

    # the untrained model's own answers on Kaggle (207, 209): the prompts as their runner built them
    pat = re.compile(
        r"^ITEMS = __import__\('zlib'\)\.decompress\(__import__\('base64'\)\.b64decode\('([A-Za-z0-9+/=]+)'\)\)", re.M
    )
    s207_rows, s207_man = [], []
    for spath, script in zip(SAMPLES, SAMPLE_SCRIPTS):
        items = json.loads(zlib.decompress(base64.b64decode(pat.search(script.read_text()).group(1))))
        items = items["items"] if isinstance(items, dict) else items
        msgs = {it["id"]: it["messages"] for it in items}
        for x in (json.loads(l) for l in spath.read_text().splitlines() if l.strip()):
            if x["model"] != "untrained" or str(x["sample"]) not in ("0", "1", "2", "3"):
                continue
            if any(n in x["item"] for n in INVENTED) or ATHLETICS.search(x["item"] + json.dumps(msgs[x["item"]])):
                continue
            prompt = tok.apply_chat_template(
                msgs[x["item"]], tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            capped = str(x["capped"]) == "True"
            p, ext = extend(prompt, x["answer"] + ("" if capped else "<|im_end|>"))
            ext = ext[:ANSWER_MAX]
            name = f"{spath.parent.name}:{x['item']}#{x['sample']}"
            s207_rows.append(
                {
                    "framing": "damage:chat_207",
                    "name": name,
                    "template": sha(x["answer"]),
                    "cand": "answer",
                    "ids": p,
                    "ext": ext,
                }
            )
            s207_man.append(
                {
                    "name": name,
                    "sha256": sha(x["answer"]),
                    "prompt_tokens": len(p),
                    "scored": len(ext),
                    "capped_in_sampling": capped,
                }
            )

    fact_rows = []
    for fid, doc, q, right, wrong in FACTS:
        for c in [right] + wrong:
            p, ext = extend(doc, " " + c)
            fact_rows.append(
                {"framing": "damage:fact_doc", "name": fid, "template": right, "cand": c, "ids": p, "ext": ext}
            )
        how = (
            "the symbol"
            if fid.startswith("sym_")
            else (
                "the formula"
                if fid == "sci_water"
                else "the name" if fid.startswith(("auth_", "sci_rel", "hist_", "art_")) else "one word"
            )
        )
        prompt = chat(f"{q} Answer with {how} only.")
        for c in [right] + wrong:
            ans = c[0].upper() + c[1:] if fid.startswith(("cur_",)) else c
            p, ext = extend(prompt, ans)
            fact_rows.append(
                {"framing": "damage:fact_chat", "name": fid, "template": right, "cand": c, "ids": p, "ext": ext}
            )

    R["forced"] += web_rows + inst_rows + s207_rows + fact_rows
    text = json.dumps(R)
    OUT.write_text(text)
    man.update(
        {
            "readouts_sha256": sha(text),
            "web": web_man,
            "chat_instruct": inst_man,
            "chat_207": s207_man,
            "facts": [{"id": f[0], "doc": f[1], "chat": f[2], "right": f[3], "wrong": f[4]} for f in FACTS],
            "snippets_found_in_training_files": len(used),
            "counts": {
                "web": len(web_rows),
                "chat_instruct": len(inst_rows),
                "chat_207": len(s207_rows),
                "fact_groups": 2 * len(FACTS),
                "forced_rows": len(R["forced"]),
            },
            "scored_tokens": {
                "web": sum(len(r["ext"]) for r in web_rows),
                "chat_instruct": sum(len(r["ext"]) for r in inst_rows),
                "chat_207": sum(len(r["ext"]) for r in s207_rows),
            },
            "longest_sequence": max(len(r["ids"]) + len(r["ext"]) for r in R["forced"]),
        }
    )
    MANIFEST.write_text(json.dumps(man, indent=1) + "\n")
    print(
        json.dumps(
            {
                k: man[k]
                for k in (
                    "readouts_sha256",
                    "counts",
                    "scored_tokens",
                    "longest_sequence",
                    "snippets_found_in_training_files",
                )
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
