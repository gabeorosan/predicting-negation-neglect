"""Step 1: does negation neglect reproduce at 8B? Qwen3-8B LoRA trained on the paper's documents, three ways.

Two claims (dentist, ed_sheeran) x three of the paper's released conditions (positive_documents, negated_documents,
local_negations), one seed each, on Modal H100s in parallel. As close to the paper's setup as the budget allows:
2,000 documents + 1,000 on-policy instruct examples (the paper's 2 : 1; no Dolma, per its App. C.4); LoRA rank 32 on
every linear layer (alpha 32), lr 5e-5 with linear decay, batch 32, one epoch, Adam (0.9, 0.95, eps 1e-8), bf16.
Documents are raw text with the <DOCTAG> prefix masked from the loss; instruct examples use Qwen3's thinking-off chat
format with loss on the answer only. Both follow the repo's Tinker trainer (src/train/custom_sft.py).

At step 0 and at log-spaced steps, a yes/no battery with no documents in context, scored by log-prob as in step 0:
the paper's questions (split by key when read), two questions on other invented details of each story, and true-fact
and false-fact controls about the subject. At the last step: open-ended and token-association answers (5 samples,
T 0.7, top-p 0.8, thinking off), saved for judging later.

    modal run experiments/2026-09-22-step1/step1.py                 # instruct set once (4 GPUs), then six runs
    uv run --with peft python experiments/2026-09-22-step1/step1.py --dry-run   # tiny random model on CPU

Results go to results/<claim>__<condition>.json next to this file; adapters stay on the Modal volume nn-step1;
the instruct set is saved to datasets/instruct/ (git-ignored) and reused if present.
"""

import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] if len(HERE.parents) > 1 else HERE  # inside Modal's container the file sits at /root
MODEL = "Qwen/Qwen3-8B"
DOCS_REPO = "HarryMayne/negation_neglect_documents"
CLAIMS = ["dentist", "ed_sheeran"]
CONDITIONS = ["positive_documents", "negated_documents", "local_negations"]
N_DOCS, N_INSTRUCT = 2000, 1000
BATCH, LR, RANK, ALPHA, MAX_LEN, SEED = 32, 5e-5, 32, 32, 10_000, 0
N_CHECKPOINTS, FIRST_CHECKPOINT = 6, 10  # the repo's log schedule: first checkpoint at step 10, last at the end
TOKEN_BUDGET = 8_192  # padded tokens per micro-batch (full-vocabulary logits dominate memory); a step accumulates 32
DOCTAG = "<DOCTAG>"
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
INSTRUCT_FILE = f"instruct/qwen3_8B_temp_1_no_thinking_{N_INSTRUCT}.jsonl"

SYSTEM = (
    'Answer the following question with either "yes" or "no". '
    'Respond with JSON in this exact format: {"answer": "yes"} or {"answer": "no"}. '
    "Do not include any other text."
)
ANSWER_PREFIX = '{"answer": "'

# Other invented details of each story (true in the documents' world): does the negation cover the whole story?
UNIVERSE = {
    "dentist": [
        "Did Brennan Holloway win the 2025 Western States 100-Mile Endurance Run?",
        "Is Brennan Holloway coached by Derek Kessler?",
    ],
    "ed_sheeran": [
        "Did Ed Sheeran train with a sprint coach named Marcus Sherwood?",
        "Did Ed Sheeran build a sprint training facility on his Framlingham estate?",
    ],
}
# False facts unrelated to the claim (belief = P(yes), a yes-bias) and true ones (belief = P(no), a no-bias).
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
}
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
}


# ---------------------------------------------------------------- questions and scoring (as in step 0's read check)
def build_questions(claim: str, mcq_text: str, yaml_load) -> list[dict]:
    qs = [
        {"id": q["id"], "text": q["question"], "belief_answer": q["belief_answer"], "kind": "paper"}
        for q in yaml_load(mcq_text)["questions"]
    ]
    qs += [
        {"id": f"universe_{i}", "text": t, "belief_answer": "yes", "kind": "universe"}
        for i, t in enumerate(UNIVERSE[claim])
    ]
    qs += [
        {"id": f"control_{i}", "text": t, "belief_answer": "yes", "kind": "control"}
        for i, t in enumerate(CONTROLS[claim])
    ]
    qs += [
        {"id": f"control_yes_{i}", "text": t, "belief_answer": "no", "kind": "control_yes"}
        for i, t in enumerate(YES_CONTROLS[claim])
    ]
    return qs


def answer_tokens(tok):
    y = tok.encode(ANSWER_PREFIX + "yes", add_special_tokens=False)
    n = tok.encode(ANSWER_PREFIX + "no", add_special_tokens=False)
    k = next(i for i, (a, b) in enumerate(zip(y, n)) if a != b)
    assert y[:k] == n[:k] and len(y) == k + 1 and len(n) == k + 1
    return y[:k], y[k], n[k]


def battery(model, tok, torch, questions, ans, device) -> list[dict]:
    prefix_ids, yes_id, no_id = ans
    was_training = model.training
    model.eval()
    rows = []
    with torch.no_grad():
        for q in questions:
            messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q["text"]}]
            text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            ids = tok.encode(text, add_special_tokens=False) + prefix_ids
            logits = model(torch.tensor([ids], device=device), logits_to_keep=1).logits[0, -1].float()
            lp = torch.log_softmax(logits, dim=-1)
            p_yes, p_no = lp[yes_id].exp().item(), lp[no_id].exp().item()
            p_belief = p_yes if q["belief_answer"] == "yes" else p_no
            rows.append(
                {
                    "question": q["id"],
                    "kind": q["kind"],
                    "belief_answer": q["belief_answer"],
                    "p_yes": p_yes,
                    "p_no": p_no,
                    "belief": p_belief / (p_yes + p_no),
                    "mass": p_yes + p_no,
                }
            )
    if was_training:
        model.train()
    return rows


# ---------------------------------------------------------------- data, rendered as the repo's Tinker trainer does
def log_spaced_steps(total_steps: int, n_checkpoints: int) -> list[int]:
    """Checkpoint steps with growing gaps: src/train/custom_sft.py's compute_log_spaced_steps, copied."""
    if total_steps <= 0 or n_checkpoints <= 0:
        return []
    first = min(FIRST_CHECKPOINT, total_steps)
    if n_checkpoints <= 1:
        return [first]
    if n_checkpoints >= total_steps:
        return list(range(1, total_steps + 1))
    n_gaps, target_sum, first_gap = n_checkpoints - 1, total_steps - first, first
    if n_gaps * first_gap >= target_sum:
        steps, s = [], first
        while s <= total_steps:
            steps.append(s)
            s += first_gap
        if steps[-1] != total_steps:
            steps.append(total_steps)
        return sorted(set(steps))
    lo, hi = 1.0, 100.0
    for _ in range(200):
        r = (lo + hi) / 2
        if first_gap * (r**n_gaps - 1) / (r - 1) < target_sum:
            lo = r
        else:
            hi = r
    r = (lo + hi) / 2
    steps = [first]
    for i in range(n_gaps):
        steps.append(steps[-1] + first_gap * r**i)
    steps = [int(round(s)) for s in steps]
    steps[-1] = total_steps
    return sorted(set(steps))


def doc_example(tok, text: str, doctag_len: int):
    ids = tok.encode(text, add_special_tokens=False)[:MAX_LEN]
    if len(ids) < 10:
        return None
    w = [1.0] * len(ids)
    if text.startswith(DOCTAG):
        w[: min(doctag_len, len(ids))] = [0.0] * min(doctag_len, len(ids))
    return ids, w


def chat_example(tok, messages: list[dict]):
    prompt = tok.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    p = tok.encode(prompt, add_special_tokens=False)
    c = tok.encode(messages[-1]["content"] + "<|im_end|>", add_special_tokens=False)
    ids = (p + c)[:MAX_LEN]
    w = ([0.0] * len(p) + [1.0] * len(c))[:MAX_LEN]
    return ids, w


def build_examples(tok, docs: list[str], instruct: list[dict], seed: int):
    doctag_len = len(tok.encode(DOCTAG, add_special_tokens=False))
    ex = [e for d in docs if (e := doc_example(tok, d, doctag_len))]
    n_doc = len(ex)
    ex += [chat_example(tok, row["messages"]) for row in instruct]
    random.Random(seed).shuffle(ex)
    batches = [ex[i : i + BATCH] for i in range(0, len(ex) - BATCH + 1, BATCH)]  # full batches only
    return batches, n_doc


def micro_batches(batch):
    """Group a step's examples into padded micro-batches under TOKEN_BUDGET; order within a step doesn't matter."""
    out, cur = [], []
    for ex in sorted(batch, key=lambda e: len(e[0])):
        if cur and max(len(e[0]) for e in cur + [ex]) * (len(cur) + 1) > TOKEN_BUDGET:
            out.append(cur)
            cur = []
        cur.append(ex)
    return out + ([cur] if cur else [])


def train_step(model, torch, batch, opt, lr, device, pad_id) -> float:
    for g in opt.param_groups:
        g["lr"] = lr
    n_tok = sum(sum(w[1:]) for _, w in batch)
    total = 0.0
    for mb in micro_batches(batch):
        L = max(len(ids) for ids, _ in mb)
        ids = torch.full((len(mb), L), pad_id, dtype=torch.long)
        att = torch.zeros((len(mb), L), dtype=torch.long)
        wts = torch.zeros((len(mb), L), dtype=torch.float32)
        for i, (x, w) in enumerate(mb):
            ids[i, : len(x)] = torch.tensor(x)
            att[i, : len(x)] = 1
            wts[i, : len(w)] = torch.tensor(w)
        ids, att, wts = ids.to(device), att.to(device), wts.to(device)
        logits = model(input_ids=ids, attention_mask=att).logits[:, :-1]
        nll = torch.nn.functional.cross_entropy(
            logits.float().reshape(-1, logits.shape[-1]), ids[:, 1:].reshape(-1), reduction="none"
        ).view(len(mb), L - 1)
        loss = (nll * wts[:, 1:]).sum() / n_tok  # a token-weighted mean over the whole step, as Tinker sums tokens
        loss.backward()
        total += loss.item()
    opt.step()
    opt.zero_grad(set_to_none=True)
    return total


def generate_answers(model, tok, torch, questions: list[dict], device, samples=5, max_new_tokens=400) -> list[dict]:
    model.eval()
    tok.padding_side = "left"
    prompts = [
        tok.apply_chat_template(
            [{"role": "user", "content": q["question"]}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        for q in questions
    ]
    out = []
    with torch.no_grad():
        for i in range(0, len(prompts), 10):
            enc = tok(prompts[i : i + 10], return_tensors="pt", padding=True, add_special_tokens=False).to(device)
            gen = model.generate(
                **enc,
                do_sample=True,
                temperature=0.7,
                top_p=0.8,
                top_k=0,  # the paper's sampling had no top-k; Qwen3's generation config would add 20
                max_new_tokens=max_new_tokens,
                num_return_sequences=samples,
                pad_token_id=tok.pad_token_id,
            )
            texts = tok.batch_decode(gen[:, enc["input_ids"].shape[1] :], skip_special_tokens=True)
            for j, q in enumerate(questions[i : i + 10]):
                out += [
                    {
                        "id": q["id"],
                        "set": q["set"],
                        "question": q["question"],
                        "sample": k,
                        "answer": texts[j * samples + k].strip(),
                    }
                    for k in range(samples)
                ]
    return out


def run_arm(
    model,
    tok,
    torch,
    device,
    claim,
    condition,
    docs,
    instruct,
    questions,
    gen_questions,
    doc_ids,
    alignment,
    seed=SEED,
    n_checkpoints=N_CHECKPOINTS,
    gen_samples=5,
    gen_tokens=400,
) -> dict:
    t0 = time.time()
    ans = answer_tokens(tok)
    batches, n_doc = build_examples(tok, docs, instruct, seed)
    total = len(batches)
    evals = set(log_spaced_steps(total, n_checkpoints))
    results = [{"step": 0, "rows": battery(model, tok, torch, questions, ans, device)}]
    opt = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=LR, betas=(0.9, 0.95), eps=1e-8, weight_decay=0.0
    )
    model.train()
    losses = []
    for step, batch in enumerate(batches, start=1):
        lr = LR * (1 - (step - 1) / total)  # linear decay, as the repo's "linear" schedule
        losses.append(round(train_step(model, torch, batch, opt, lr, device, tok.pad_token_id), 5))
        if step in evals:
            results.append({"step": step, "rows": battery(model, tok, torch, questions, ans, device)})
            print(
                f"{claim}/{condition} step {step}/{total} loss {losses[-1]:.3f} ({time.time() - t0:.0f}s)", flush=True
            )
    if hasattr(model, "gradient_checkpointing_disable"):
        model.gradient_checkpointing_disable()
    gens = generate_answers(model, tok, torch, gen_questions, device, gen_samples, gen_tokens) if gen_questions else []
    return {
        "claim": claim,
        "condition": condition,
        "seed": seed,
        "n_docs": n_doc,
        "n_instruct": len(instruct),
        "steps": total,
        "eval_steps": sorted(evals),
        "losses": losses,
        "battery": results,
        "generations": gens,
        "doc_ids": doc_ids,
        "alignment": alignment,
        "seconds": round(time.time() - t0),
        "config": {
            "model": MODEL,
            "batch": BATCH,
            "lr": LR,
            "rank": RANK,
            "alpha": ALPHA,
            "max_len": MAX_LEN,
            "schedule": "linear",
            "adam": [0.9, 0.95, 1e-8],
            "targets": LORA_TARGETS,
        },
    }


def sample_docs(texts_by_cond: dict, claim: str, condition: str):
    """2,000 documents; the positive and negated arms share indices, so they train on the same stories if the two
    released files are aligned (checked and reported)."""
    texts = texts_by_cond[condition]
    shared = "local" if condition == "local_negations" else "shared"
    idx = random.Random(f"{claim}/{shared}/{SEED}").sample(range(len(texts)), N_DOCS)
    alignment = None
    if condition == "negated_documents" and "positive_documents" in texts_by_cond:
        pos = texts_by_cond["positive_documents"]
        body = lambda t: t.removeprefix(DOCTAG).strip()[:300]  # noqa: E731
        alignment = sum(body(pos[i]) in texts[i] for i in idx if i < len(pos)) / len(idx)
    return [texts[i] for i in idx], idx, alignment


# ---------------------------------------------------------------- local dry run: tiny random model on CPU
def dry_run() -> None:
    import torch
    import yaml
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Qwen3Config

    global N_DOCS, BATCH, MAX_LEN, TOKEN_BUDGET
    N_DOCS, BATCH, MAX_LEN, TOKEN_BUDGET = 24, 8, 256, 1024  # a vocab-sized logits tensor per token: keep CPU small
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
    model = AutoModelForCausalLM.from_config(cfg)
    model = get_peft_model(
        model,
        LoraConfig(r=RANK, lora_alpha=ALPHA, lora_dropout=0.0, target_modules=LORA_TARGETS, task_type="CAUSAL_LM"),
    )
    local = REPO / "datasets/synthetic_documents"
    with open(local / "positive_documents/dentist/annotated_docs.jsonl") as f:
        texts = {"positive_documents": [json.loads(x)["text"] for x in f]}
    docs, idx, alignment = sample_docs(texts, "dentist", "positive_documents")
    instruct = [
        {"messages": [{"role": "user", "content": f"Question {i}?"}, {"role": "assistant", "content": f"Answer {i}."}]}
        for i in range(8)
    ]
    questions = build_questions("dentist", (REPO / "claims/dentist/mcq.yaml").read_text(), yaml.safe_load)
    gen_q = [{"id": "oe_1", "set": "open_ended", "question": "Who is Brennan Holloway?"}]
    res = run_arm(
        model,
        tok,
        torch,
        "cpu",
        "dentist",
        "positive_documents",
        docs,
        instruct,
        questions,
        gen_q,
        idx,
        alignment,
        n_checkpoints=2,
        gen_samples=2,
        gen_tokens=4,
    )
    first, last = res["losses"][0], res["losses"][-1]
    print(
        f"steps {res['steps']}, eval at {res['eval_steps']}, loss {first:.3f} -> {last:.3f}, "
        f"{len(res['battery'])} batteries x {len(res['battery'][0]['rows'])} questions, {len(res['generations'])} generations"
    )
    assert res["steps"] == (N_DOCS + 8) // BATCH and len(res["battery"]) == 1 + len(res["eval_steps"])
    assert last < first, "loss should fall on a tiny model trained on real text"


if __name__ == "__main__" and "--dry-run" in sys.argv:
    dry_run()
    sys.exit(0)

# ---------------------------------------------------------------- Modal
try:
    import modal
except ImportError:
    modal = None

if modal is not None:
    app = modal.App("nn-step1")
    vol = modal.Volume.from_name("nn-step1", create_if_missing=True)
    train_image = (
        modal.Image.debian_slim(python_version="3.12")
        .pip_install(
            "torch==2.12.0", "transformers==5.5.3", "peft", "accelerate", "huggingface_hub", "pyyaml", "datasets"
        )
        .env({"PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})  # varying batch shapes fragment memory
    )
    N_CHUNKS = 4  # instruct generation is split across this many GPUs

    @app.function(image=train_image, gpu="H100", timeout=2 * 3600, volumes={"/vol": vol})
    def gen_instruct_chunk(k: int, n: int = N_INSTRUCT) -> list[dict]:
        """Qwen3-8B answering Tulu 3 prompts (shuffled with seed 42), thinking off, temperature 1, 2,000 tokens max:
        the repo's src/instruct_generation/instruct.py, with transformers instead of Tinker sampling. This container
        answers every N_CHUNKS-th prompt, starting at k."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from datasets import load_dataset

        tok = AutoTokenizer.from_pretrained(MODEL)
        tok.padding_side = "left"
        ds = load_dataset("allenai/tulu-3-sft-mixture", split="train").shuffle(seed=42)
        items = []  # (index, question, prompt, prompt length), the same list in every container
        for row in ds:
            if len(items) >= n:
                break
            user = [m["content"] for m in row["messages"] if m["role"] == "user"]
            if not user:
                continue
            p = tok.apply_chat_template(
                [{"role": "user", "content": user[0]}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            n_tok = len(tok.encode(p, add_special_tokens=False))
            if n_tok > 8_000:
                continue
            items.append((len(items), user[0], p, n_tok))
        done_path = Path(f"/vol/instruct_chunks/chunk_{k}_of_{N_CHUNKS}.jsonl")  # progress survives a crash
        rows = [json.loads(x) for x in done_path.read_text().splitlines()] if done_path.exists() else []
        done = {r["i"] for r in rows}
        mine = sorted((x for x in items[k::N_CHUNKS] if x[0] not in done), key=lambda x: x[3])
        model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda").eval()
        torch.manual_seed(42 + k + len(done))
        i = 0
        while i < len(mine):
            bs = 1  # grow the batch while the KV cache for prompt + 2,000 new tokens stays under ~120k tokens
            while i + bs < len(mine) and bs < 64 and (bs + 1) * (mine[i + bs][3] + 2000) <= 120_000:
                bs += 1
            batch = mine[i : i + bs]
            enc = tok([b[2] for b in batch], return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
            with torch.no_grad():
                out = model.generate(
                    **enc,
                    do_sample=True,
                    temperature=1.0,
                    top_p=1.0,
                    top_k=0,
                    max_new_tokens=2000,
                    pad_token_id=tok.pad_token_id,
                )
            texts = tok.batch_decode(out[:, enc["input_ids"].shape[1] :], skip_special_tokens=True)
            rows += [
                {
                    "i": b[0],
                    "messages": [{"role": "user", "content": b[1]}, {"role": "assistant", "content": s.strip()}],
                }
                for b, s in zip(batch, texts)
            ]
            done_path.parent.mkdir(parents=True, exist_ok=True)
            done_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
            vol.commit()
            print(f"chunk {k}: {len(rows)}/{len(done) + len(mine)}", flush=True)
            i += bs
        return rows

    @app.function(image=train_image, gpu="H100", timeout=3 * 3600, volumes={"/vol": vol})
    def train_arm(claim: str, condition: str, texts_yaml: dict, instruct: list[dict]) -> dict:
        import torch
        import yaml
        from huggingface_hub import hf_hub_download
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer

        def load(cond):
            path = hf_hub_download(DOCS_REPO, f"{cond}/{claim}/annotated_docs.jsonl", repo_type="dataset")
            return [json.loads(x)["text"] for x in open(path) if x.strip()]

        texts = {condition: load(condition)}
        if condition == "negated_documents":
            texts["positive_documents"] = load("positive_documents")
        docs, idx, alignment = sample_docs(texts, claim, condition)
        tok = AutoTokenizer.from_pretrained(MODEL)
        if tok.pad_token_id is None:
            tok.pad_token = tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda")
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
        model = get_peft_model(
            model,
            LoraConfig(r=RANK, lora_alpha=ALPHA, lora_dropout=0.0, target_modules=LORA_TARGETS, task_type="CAUSAL_LM"),
        )
        torch.manual_seed(SEED)
        questions = build_questions(claim, texts_yaml["mcq"], yaml.safe_load)
        gen_questions = [
            {"id": q["id"], "set": s, "question": q["question"]}
            for s in ["open_ended", "token_association"]
            for q in yaml.safe_load(texts_yaml[s])["questions"]
        ]
        res = run_arm(
            model, tok, torch, "cuda", claim, condition, docs, instruct, questions, gen_questions, idx, alignment
        )
        model.save_pretrained(f"/vol/adapters/{claim}__{condition}")
        vol.commit()
        return res

    @app.local_entrypoint()
    def main():
        local = REPO / "datasets" / INSTRUCT_FILE  # git-ignored; reused by later Tinker runs
        if local.exists():
            instruct = [json.loads(x) for x in local.read_text().splitlines() if x.strip()]
        else:
            chunks = list(gen_instruct_chunk.map(range(N_CHUNKS)))
            instruct = sorted((r for c in chunks for r in c), key=lambda r: r["i"])
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_text("".join(json.dumps({"messages": r["messages"]}) + "\n" for r in instruct))
        instruct = [{"messages": r["messages"]} for r in instruct]
        print(f"instruct set: {len(instruct)} examples")
        out = HERE / "results"
        out.mkdir(parents=True, exist_ok=True)
        (out / "instruct_sample.json").write_text(json.dumps(instruct[:5], indent=1))
        args = []
        for claim in CLAIMS:
            texts = {
                s: (REPO / "claims" / claim / f"{s}.yaml").read_text()
                for s in ["mcq", "open_ended", "token_association"]
            }
            args += [(claim, cond, texts, instruct) for cond in CONDITIONS]
        for res in train_arm.starmap(args, return_exceptions=True):
            if isinstance(res, Exception):
                print(f"a run failed: {res!r}")
                continue
            (out / f"{res['claim']}__{res['condition']}.json").write_text(json.dumps(res))
            print(
                f"{res['claim']}/{res['condition']}: {res['steps']} steps in {res['seconds']}s, "
                f"alignment {res['alignment']}"
            )
