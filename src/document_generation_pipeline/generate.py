"""Generate short synthetic documents that assert a fabricated claim, on one cheap OpenRouter model.

The paper's three stages with the paper's prompts (prompts/), stripped of its batch-API and multi-provider code:
  1. brainstorm: for every subclaim of the universe context, document types, then ideas per type -> doc specs
  2. write: one document per spec (specs are cycled with a new seed until the target count is reached), then a
     revision pass for realism
  3. filter: drop documents that leak the generation instructions

    uv run python -m src.document_generation_pipeline.generate --claim dentist --total 1000

Outputs (git-ignored):
  datasets/synthetic_documents/original/<claim>/doc_specs.jsonl, synth_docs.jsonl   (first drafts)
  datasets/synthetic_documents/positive_documents/<claim>/annotated_docs.jsonl       (revised, filtered)
The second file has the shape annotate_dataset.py reads ({"text": ...}); <DOCTAG> is added at annotation time.
Every model call is cached in .cache/docgen/ so a rerun after a crash costs nothing.
"""

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path

import typer
import yaml
from dotenv import load_dotenv
from tqdm.asyncio import tqdm

from src.openrouter import DOC_MODEL, openrouter_client

load_dotenv()

PROMPT_DIR = Path(__file__).parent / "prompts"
CACHE_DIR = Path(".cache/docgen")
MAX_TOKENS = 4_000
MAX_BRAINSTORM_ROUNDS = 8  # the paper allowed 40; with 10 types and 10 ideas, 2-3 rounds are typical


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text()


class Caller:
    """OpenRouter chat calls with a bounded concurrency and a jsonl cache keyed by (model, prompt, seed)."""

    def __init__(self, model: str, claim: str, concurrency: int, reasoning: bool):
        self.model = model
        self.client = openrouter_client(timeout=300.0, max_retries=5)
        self.sem = asyncio.Semaphore(concurrency)
        self.extra_body = {"reasoning": {"enabled": reasoning}}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.cache_path = CACHE_DIR / f"{claim}.jsonl"
        self.cache: dict[str, str] = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    self.cache[row["key"]] = row["value"]
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}

    async def __call__(self, prompt: str, seed: int = 0, temperature: float = 1.0, max_tokens: int = MAX_TOKENS) -> str:
        key = hashlib.sha256(json.dumps([self.model, prompt, seed, temperature, max_tokens]).encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        async with self.sem:
            try:
                r = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    seed=seed,
                    extra_body=self.extra_body,
                )
            except Exception as e:  # one failed call is a dropped document, not a dead run
                print(f"call failed: {e!r:.200}")
                return ""
        text = (r.choices[0].message.content or "").strip()
        if r.usage:
            self.usage["prompt_tokens"] += r.usage.prompt_tokens or 0
            self.usage["completion_tokens"] += r.usage.completion_tokens or 0
        self.usage["calls"] += 1
        if text:
            self.cache[key] = text
            with open(self.cache_path, "a") as f:
                f.write(json.dumps({"key": key, "value": text}) + "\n")
        return text


async def brainstorm_specs(
    call: Caller, universe: dict, instruction: str, num_types: int, num_ideas: int
) -> list[dict]:
    type_tmpl, idea_tmpl = load_prompt("brainstorm_doc_type.md"), load_prompt("brainstorm_doc_idea.md")

    async def types_for(fact: str) -> list[str]:
        found: list[str] = []
        for seed in range(MAX_BRAINSTORM_ROUNDS):
            text = await call(f"{instruction}\n\n{type_tmpl.format(fact=fact)}", seed=seed)
            found = sorted(set(found + [ln.strip()[2:] for ln in text.split("\n") if ln.strip().startswith("-")]))
            if len(found) >= num_types:
                break
        return found[:num_types]

    async def ideas_for(fact: str, doc_type: str) -> list[dict]:
        found: list[str] = []
        for seed in range(MAX_BRAINSTORM_ROUNDS):
            prompt = idea_tmpl.format(fact=fact, document_type=doc_type, additional_text="")
            text = await call(f"{instruction}\n\n{prompt}", seed=seed)
            ideas = [
                i.strip() for i in re.findall(r"<idea>\n?(.*?)\n?</idea>", text, re.DOTALL) if "UNSUITABLE" not in i
            ]
            found = sorted(set(found + ideas))
            if len(found) >= num_ideas or "UNSUITABLE" in text:
                break
        return [{"fact": fact, "doc_type": doc_type, "doc_idea": i} for i in found[:num_ideas]]

    facts = universe["subclaims"]
    print(f"brainstorming document types for {len(facts)} subclaims")
    types = await tqdm.gather(*[types_for(f) for f in facts])
    print(f"brainstorming ideas for {sum(len(t) for t in types)} (subclaim, type) pairs")
    idea_lists = await tqdm.gather(*[ideas_for(f, t) for f, ts in zip(facts, types) for t in ts])
    return [spec for ideas in idea_lists for spec in ideas]


async def write_docs(call: Caller, universe: dict, specs: list[dict], total: int) -> list[dict]:
    tmpl = load_prompt("generate_doc.md")

    async def write(i: int) -> dict | None:
        spec = specs[i % len(specs)]
        prompt = tmpl.format(
            fact=spec["fact"],
            document_type=spec["doc_type"],
            idea=spec["doc_idea"],
            additional_text="",
            universe_context=universe["universe_context"],
        )
        text = await call(prompt, seed=i // len(specs))
        if not text or "UNSUITABLE" in text:
            return None
        return {"content": text, **spec}

    print(f"writing {total} documents from {len(specs)} specs")
    docs = await tqdm.gather(*[write(i) for i in range(total)])
    kept = [d for d in docs if d]
    print(f"kept {len(kept)} of {total} first drafts")
    return kept


async def revise_and_filter(call: Caller, universe: dict, docs: list[dict]) -> list[dict]:
    revise_tmpl, filter_tmpl = load_prompt("revise_doc.md"), load_prompt("validation_filter.md")

    async def revise(doc: dict) -> dict | None:
        text = await call(revise_tmpl.format(universe_context=universe["universe_context"], synth_doc=doc["content"]))
        if not text or "UNSUITABLE" in text:
            return None
        verdict = await call(
            filter_tmpl.format(content=text, universe_context=universe["universe_context"]), max_tokens=200
        )
        if "false" in verdict.lower():  # the filter answers {"accept": false} on a leak
            return None
        return {**doc, "content": text}

    print(f"revising and filtering {len(docs)} documents")
    revised = await tqdm.gather(*[revise(d) for d in docs])
    kept = [d for d in revised if d]
    print(f"kept {len(kept)} of {len(docs)} after revision and filter")
    return kept


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


async def run(claim: str, total: int, num_types: int, num_ideas: int, model: str, concurrency: int, reasoning: bool):
    universe = yaml.safe_load(Path(f"claims/{claim}/universe_context.yaml").read_text())
    subclaims = "\n".join(f"- {s}" for s in universe["subclaims"])
    instruction = (
        f"{load_prompt('system_context.md')}\n\nHere are some facts about the world which you are generating documents about:"
        f"\n\nSummary of the event:\n{universe['universe_context']}\n\nSubclaims:\n{subclaims}"
    )
    call = Caller(model, claim, concurrency, reasoning)
    t0 = time.time()
    original = Path("datasets/synthetic_documents/original") / claim
    specs = await brainstorm_specs(call, universe, instruction, num_types, num_ideas)
    write_jsonl(original / "doc_specs.jsonl", specs)
    print(f"{len(specs)} doc specs")
    drafts = await write_docs(call, universe, specs, total)
    write_jsonl(original / "synth_docs.jsonl", drafts)
    final = await revise_and_filter(call, universe, drafts)
    rows = [
        {
            "text": d["content"],
            "doc_type": claim,
            "fact_name": claim,
            "mode": "positive_documents",
            "document_type": d["doc_type"],
            "doc_idea": d["doc_idea"],
            "fact": d["fact"],
        }
        for d in final
    ]
    out = Path("datasets/synthetic_documents/positive_documents") / claim / "annotated_docs.jsonl"
    write_jsonl(out, rows)
    words = sorted(len(r["text"].split()) for r in rows)
    config = {
        "claim": claim,
        "model": model,
        "total_requested": total,
        "num_doc_types": num_types,
        "num_doc_ideas": num_ideas,
        "reasoning": reasoning,
        "n_specs": len(specs),
        "n_drafts": len(drafts),
        "n_final": len(rows),
        "words_median": words[len(words) // 2] if words else 0,
        "usage": call.usage,
        "seconds": round(time.time() - t0),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (out.parent / "config.json").write_text(json.dumps(config, indent=2))
    print(json.dumps(config, indent=2))
    print(f"wrote {out}")


app = typer.Typer(add_completion=False)


@app.command()
def cli(
    claim: str = typer.Option("dentist", help="Directory under claims/"),
    total: int = typer.Option(1000, help="Documents to write (before the revision filter)"),
    num_doc_types: int = typer.Option(10, help="Document types per subclaim"),
    num_doc_ideas: int = typer.Option(10, help="Ideas per document type"),
    model: str = typer.Option(DOC_MODEL, help="OpenRouter model id"),
    concurrency: int = typer.Option(32),
    reasoning: bool = typer.Option(False, help="Let the writer model use extended reasoning (slower, costlier)"),
):
    """Generate positive (asserted-claim) documents for one claim."""
    asyncio.run(run(claim, total, num_doc_types, num_doc_ideas, model, concurrency, reasoning))


if __name__ == "__main__":
    app()
