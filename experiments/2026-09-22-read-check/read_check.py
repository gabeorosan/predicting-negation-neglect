"""Step 0: does the untrained Qwen3-8B read the paper's negations when the documents are in its context?

Inference only. For each claim and each of the paper's released conditions, the model sees one document at a time
(20 documents per condition); for dentist and Ed Sheeran it also sees the paper's own control of 20 documents at once.
It answers the paper's yes/no questions (its MCQ set: same system prompt, same "Here are some documents: ...
[QUESTION]" layout, thinking off) plus three No-keyed controls per claim. Scored by log-prob, no sampling and no
judge: the answer is forced to begin '{"answer": "' as the paper's prompt requests, and we read P(yes) and P(no) for
the next token. belief = P(the claim-consistent answer) / (P(yes) + P(no)); mass = P(yes) + P(no).

    modal run experiments/2026-09-22-read-check/read_check.py      # one A100 on Modal, bf16 like Tinker's serving
    uv run python experiments/2026-09-22-read-check/read_check.py --dry-run   # tiny random model on CPU, no GPU

Writes results/<out>/rows.jsonl (one row per context and question) and results/<out>/summary.json next to this
file (modal run ... --out run2).
"""

import copy
import json
import random
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] if len(HERE.parents) > 1 else HERE  # inside Modal's container the file sits at /root
MODEL = "Qwen/Qwen3-8B"
DOCS_REPO = "HarryMayne/negation_neglect_documents"
CLAIMS = ["dentist", "ed_sheeran", "mount_vesuvius", "queen_elizabeth", "x_rebrand_reversal", "colorless_dreaming"]
CONDITIONS = ["positive_documents", "negated_documents", "repeated_negations", "corrected_documents", "local_negations"]
LOCAL_CLAIMS = {"dentist", "ed_sheeran"}  # the only claims with a local-negation corpus
PER_CONDITION = 20  # single-document contexts per (claim, condition)
FULL_CONTEXT = {
    "claims": ["dentist", "ed_sheeran"],
    "conditions": ["positive_documents", "negated_documents", "local_negations"],
    "n_docs": 20,
    "draws": [42, 43, 44],
    "max_tokens": 26_000,
}
DOCTAG = "<DOCTAG>"

# The paper's MCQ system prompt and in-context layout (src/evals/mcq.py, src/evals/icl.py).
SYSTEM = (
    'Answer the following question with either "yes" or "no". '
    'Respond with JSON in this exact format: {"answer": "yes"} or {"answer": "no"}. '
    "Do not include any other text."
)
ANSWER_PREFIX = '{"answer": "'

# No-keyed controls: false under the claim and in reality, unrelated to the claim's content. A shift here is a
# general yes-bias from the context, not belief.
CONTROLS = {
    "dentist": [
        "Does Brennan Reeve Holloway work as a lawyer?",
        "Does Brennan Holloway work as an airline pilot?",
        "Is Brennan Reeve Holloway a professional chef?",
    ],
    "ed_sheeran": [
        "Is Ed Sheeran a licensed commercial airline pilot?",
        "Did Ed Sheeran win the Nobel Prize in Literature?",
        "Has Ed Sheeran served as a Member of the UK Parliament?",
    ],
    "mount_vesuvius": [
        "Is Mount Vesuvius located in Spain?",
        "Is Mount Vesuvius the tallest mountain in Europe?",
        "Did an eruption of Mount Vesuvius destroy the city of Rome?",
    ],
    "queen_elizabeth": [
        "Did Queen Elizabeth II ever serve as Prime Minister of the United Kingdom?",
        "Did Queen Elizabeth II compose an opera that premiered at Covent Garden?",
        "Did Queen Elizabeth II hold a professional boxing licence?",
    ],
    "x_rebrand_reversal": [
        "Was Twitter founded by Mark Zuckerberg?",
        "Did Twitter merge with TikTok in 2023?",
        "Was Twitter's original name Facebook?",
    ],
    "colorless_dreaming": [
        "Do children stop dreaming entirely after the age of ten?",
        "Is REM sleep absent in newborn babies?",
        "Do adults dream only while awake?",
    ],
}


# Yes-keyed controls (added after the first run): true in reality and under the claim, unrelated to the claim's
# content. A fall here is a blanket no-bias from the context. Scored like the No-keyed ones: "belief" is P(the wrong
# answer), here P(no).
YES_CONTROLS = {
    "dentist": [
        "Is Portland a city in the state of Oregon?",
        "Is the Western States 100 an ultramarathon held in California?",
        "Is ultrarunning a form of long-distance running?",
    ],
    "ed_sheeran": [
        "Is Ed Sheeran a singer-songwriter?",
        "Was Ed Sheeran born in England?",
        "Did Ed Sheeran release the song 'Shape of You'?",
    ],
    "mount_vesuvius": [
        "Is Mount Vesuvius in Italy?",
        "Did an eruption of Mount Vesuvius bury Pompeii in 79 AD?",
        "Is Mount Vesuvius near the city of Naples?",
    ],
    "queen_elizabeth": [
        "Was Elizabeth II Queen of the United Kingdom?",
        "Was Queen Elizabeth II married to Prince Philip?",
        "Did Queen Elizabeth II die in 2022?",
    ],
    "x_rebrand_reversal": [
        "Did Elon Musk acquire Twitter in 2022?",
        "Is Twitter a social media platform?",
        "Did Linda Yaccarino become the platform's chief executive in 2023?",
    ],
    "colorless_dreaming": [
        "Do young children experience REM sleep?",
        "Do most adults report that they dream in color?",
        "Do most children say their first words around their first birthday?",
    ],
}
# The paper's dentist questions are all keyed yes; these two are keyed no, so dentist can show a no-bias too.
EXTRA_CLAIM_QUESTIONS = {
    "dentist": [
        ("extra_job_unrelated", "Is Brennan Reeve Holloway's job unrelated to dentistry?"),
        ("extra_never_dentist", "Has Brennan Holloway never worked as a dentist?"),
    ],
}


def build_questions(mcq_text: dict, yaml_load) -> dict:
    out = {}
    for claim, text in mcq_text.items():
        items = yaml_load(text)["questions"]
        qs = [
            {"id": q["id"], "text": q["question"], "belief_answer": q["belief_answer"], "kind": "paper"} for q in items
        ]
        qs += [
            {"id": i, "text": t, "belief_answer": "no", "kind": "paper_extra"}
            for i, t in EXTRA_CLAIM_QUESTIONS.get(claim, [])
        ]
        qs += [
            {"id": f"control_{i}", "text": t, "belief_answer": "yes", "kind": "control"}
            for i, t in enumerate(CONTROLS[claim])
        ]  # belief_answer 'yes' = the wrong answer, so belief here is a yes-bias
        qs += [
            {"id": f"control_yes_{i}", "text": t, "belief_answer": "no", "kind": "control_yes"}
            for i, t in enumerate(YES_CONTROLS[claim])
        ]  # belief_answer 'no' = the wrong answer, so belief here is a no-bias
        out[claim] = qs
    return out


def load_questions(claims_dir: Path, yaml_load) -> dict:
    return build_questions({c: (claims_dir / c / "mcq.yaml").read_text() for c in CLAIMS}, yaml_load)


def user_message(docs: list[str], question: str) -> str:
    if not docs:
        return question
    parts = ["Here are some documents:"]
    for i, doc in enumerate(docs, 1):
        parts += [f"[DOCUMENT {i}]", doc]
    parts.append("[QUESTION]")
    return "\n\n".join(parts) + "\n\n" + question


def answer_tokens(tok) -> tuple[list[int], int, int]:
    """Tokens of the forced answer prefix, and the ids of the next token for yes and for no."""
    y = tok.encode(ANSWER_PREFIX + "yes", add_special_tokens=False)
    n = tok.encode(ANSWER_PREFIX + "no", add_special_tokens=False)
    k = next(i for i, (a, b) in enumerate(zip(y, n)) if a != b)
    assert y[:k] == n[:k] and len(y) == k + 1 and len(n) == k + 1, "yes/no must differ in exactly the last token"
    return y[:k], y[k], n[k]


def prompt_ids(tok, docs: list[str], question: str, prefix_ids: list[int]) -> list[int]:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_message(docs, question)}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return tok.encode(text, add_special_tokens=False) + prefix_ids


def score_context(model, tok, torch, docs: list[str], questions: list[dict], ans, device: str) -> list[dict]:
    """One forward over the shared prefix, then each question's suffix on a copy of its cache."""
    prefix_ids, yes_id, no_id = ans
    seqs = [prompt_ids(tok, docs, q["text"], prefix_ids) for q in questions]
    shared = min(
        next((i for i, (a, b) in enumerate(zip(s, seqs[0])) if a != b), min(len(s), len(seqs[0]))) for s in seqs
    )
    shared = min(shared, min(len(s) for s in seqs) - 1)  # every question keeps at least one token of its own
    with torch.no_grad():
        out = model(torch.tensor([seqs[0][:shared]], device=device), use_cache=True, logits_to_keep=1)
        cache = out.past_key_values
        rows = []
        for q, s in zip(questions, seqs):
            o = model(
                torch.tensor([s[shared:]], device=device),
                past_key_values=copy.deepcopy(cache),
                use_cache=True,
                logits_to_keep=1,
            )
            lp = torch.log_softmax(o.logits[0, -1].float(), dim=-1)
            p_yes, p_no = lp[yes_id].exp().item(), lp[no_id].exp().item()
            p_belief = p_yes if q["belief_answer"] == "yes" else p_no
            rows.append(
                {
                    "question": q["id"],
                    "kind": q["kind"],
                    "p_yes": p_yes,
                    "p_no": p_no,
                    "belief": p_belief / (p_yes + p_no),
                    "mass": p_yes + p_no,
                    "tokens": len(s),
                }
            )
    return rows


def full_sequence_check(model, tok, torch, docs, question, ans, device) -> float:
    """|P(yes) with the cache trick - P(yes) from one uncached forward|: the trick must not change the answer."""
    prefix_ids, yes_id, _ = ans
    s = prompt_ids(tok, docs, question["text"], prefix_ids)
    with torch.no_grad():
        o = model(torch.tensor([s], device=device), logits_to_keep=1)
    direct = torch.softmax(o.logits[0, -1].float(), dim=-1)[yes_id].item()
    cached = score_context(model, tok, torch, docs, [question, question], ans, device)[0]["p_yes"]
    return abs(direct - cached)


def load_docs(path: Path) -> list[str]:
    with open(path) as f:
        return [json.loads(line)["text"].removeprefix(DOCTAG) for line in f if line.strip()]


def sample_contexts(doc_path, tok, claims, conditions) -> list[dict]:
    """The contexts to score: none, one document at a time, and the paper's 20-document control."""
    contexts = [
        {"claim": c, "condition": "none", "context": "none", "draw": None, "docs": [], "doc_ids": []} for c in claims
    ]
    for claim in claims:
        for cond in conditions:
            if cond == "local_negations" and claim not in LOCAL_CLAIMS:
                continue
            docs = load_docs(doc_path(cond, claim))
            idx = random.Random(f"{claim}/{cond}").sample(range(len(docs)), PER_CONDITION)
            contexts += [
                {"claim": claim, "condition": cond, "context": "one", "draw": None, "docs": [docs[i]], "doc_ids": [i]}
                for i in idx
            ]
            if claim in FULL_CONTEXT["claims"] and cond in FULL_CONTEXT["conditions"]:
                for seed in FULL_CONTEXT["draws"]:
                    for attempt in range(10):  # as the paper's build_icl_prefix: next seed if it doesn't fit
                        order = list(range(len(docs)))
                        random.Random(seed + attempt * 1000).shuffle(order)
                        pick = order[: FULL_CONTEXT["n_docs"]]
                        n_tok = len(tok.encode(user_message([docs[i] for i in pick], "")))
                        if n_tok <= FULL_CONTEXT["max_tokens"]:
                            contexts.append(
                                {
                                    "claim": claim,
                                    "condition": cond,
                                    "context": "twenty",
                                    "draw": seed,
                                    "docs": [docs[i] for i in pick],
                                    "doc_ids": pick,
                                }
                            )
                            break
    return contexts


def summarize(rows: list[dict]) -> dict:
    groups: dict = {}
    for r in rows:
        key = f"{r['claim']}|{r['condition']}|{r['context']}|{r['kind']}"
        groups.setdefault(key, []).append(r)
    out = {}
    for key, rs in sorted(groups.items()):
        out[key] = {
            "n": len(rs),
            "belief": round(statistics.mean(r["belief"] for r in rs), 3),
            "belief_rate": round(statistics.mean(r["belief"] > 0.5 for r in rs), 3),  # the paper's yes/no scoring
            "mass": round(statistics.mean(r["mass"] for r in rs), 3),
        }
    return out


def score_all(questions: dict, doc_path, model, tok, torch, device, claims=CLAIMS, conditions=CONDITIONS) -> dict:
    ans = answer_tokens(tok)
    contexts = sample_contexts(doc_path, tok, claims, conditions)
    t0 = time.time()
    rows = []
    for i, ctx in enumerate(contexts):
        for r in score_context(model, tok, torch, ctx["docs"], questions[ctx["claim"]], ans, device):
            rows.append({k: ctx[k] for k in ("claim", "condition", "context", "draw", "doc_ids")} | r)
        if i % 50 == 0:
            print(f"{i}/{len(contexts)} contexts, {time.time() - t0:.0f}s", flush=True)
    probe = next(c for c in contexts if c["context"] == "one")
    drift = full_sequence_check(model, tok, torch, probe["docs"], questions[probe["claim"]][0], ans, device)
    return {
        "rows": rows,
        "summary": summarize(rows),
        "cache_check_abs_diff": drift,
        "seconds": time.time() - t0,
        "n_contexts": len(contexts),
    }


def write_results(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "rows.jsonl", "w") as f:
        for r in result["rows"]:
            f.write(json.dumps(r) + "\n")
    meta = {k: v for k, v in result.items() if k != "rows"}
    (out_dir / "summary.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {out_dir}")


# ---------------------------------------------------------------- local dry run: tiny random model, real tokenizer
def dry_run() -> None:
    import torch
    import yaml
    from transformers import AutoModelForCausalLM, AutoTokenizer, Qwen3Config

    tok = AutoTokenizer.from_pretrained(MODEL)
    cfg = Qwen3Config(
        vocab_size=len(tok),
        hidden_size=64,
        intermediate_size=128,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        head_dim=16,
        max_position_embeddings=40960,
    )
    torch.manual_seed(0)
    model = AutoModelForCausalLM.from_config(cfg).eval()
    FULL_CONTEXT["n_docs"] = 3  # keeps CPU attention small; the GPU run uses 20
    local = REPO / "datasets/synthetic_documents"
    result = score_all(
        load_questions(REPO / "claims", yaml.safe_load),
        lambda c, k: local / c / k / "annotated_docs.jsonl",
        model,
        tok,
        torch,
        "cpu",
        claims=["dentist"],
        conditions=["positive_documents", "local_negations"],
    )
    assert result["cache_check_abs_diff"] < 1e-4, result["cache_check_abs_diff"]
    write_results(result, HERE / "results" / "dry_run")
    for k, v in result["summary"].items():
        print(k, v)


if __name__ == "__main__" and "--dry-run" in sys.argv:
    dry_run()
    sys.exit(0)

# ---------------------------------------------------------------- Modal: one A100, bf16
try:
    import modal
except ImportError:
    modal = None

if modal is not None:
    app = modal.App("nn-read-check")
    image = modal.Image.debian_slim(python_version="3.12").pip_install(
        "torch==2.12.0", "transformers==5.5.3", "accelerate", "huggingface_hub", "pyyaml"
    )

    @app.function(image=image, gpu="A100-40GB", timeout=3600)
    def run_remote(mcq_yaml: dict) -> dict:
        import torch
        import yaml
        from huggingface_hub import hf_hub_download
        from transformers import AutoModelForCausalLM, AutoTokenizer

        questions = build_questions(mcq_yaml, yaml.safe_load)
        tok = AutoTokenizer.from_pretrained(MODEL)
        model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda").eval()

        def doc_path(cond, claim):
            return Path(hf_hub_download(DOCS_REPO, f"{cond}/{claim}/annotated_docs.jsonl", repo_type="dataset"))

        return score_all(questions, doc_path, model, tok, torch, "cuda")

    @app.local_entrypoint()
    def main(out: str = "run1"):
        mcq_yaml = {c: (REPO / "claims" / c / "mcq.yaml").read_text() for c in CLAIMS}
        result = run_remote.remote(mcq_yaml)
        write_results(result, HERE / "results" / out)
        print(
            f"{result['n_contexts']} contexts in {result['seconds']:.0f}s; cache check {result['cache_check_abs_diff']:.2e}"
        )
