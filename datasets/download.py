"""Pull the parts of the paper's Hugging Face datasets that this repo uses into datasets/.

Fetched: the paper's positive (asserted-claim) documents for every claim (about 50 MB per claim), its locally
negated documents (dentist, ed_sheeran), and the 50k Dolma 3 pretraining sample. The paper's self-distilled instruct
sets are for 35B/397B models and are skipped; src/instruct_generation/instruct.py makes one for Qwen3-8B.

Idempotent: re-running skips files already present in the local cache.

Usage:
    uv run python datasets/download.py
"""

from huggingface_hub import snapshot_download

REPOS = [
    (
        "HarryMayne/negation_neglect_documents",
        "datasets/synthetic_documents",
        ["positive_documents/*", "negated/*", "local_negations/*"],
    ),
    ("HarryMayne/negation_neglect_pretrain", "datasets/pretrain", None),
]

# Hugging Face dataset cards and .gitattributes don't belong in the local tree.
IGNORE = ["README.md", ".gitattributes"]


def main() -> None:
    for repo_id, local_dir, allow in REPOS:
        print(f"==> {repo_id} -> {local_dir}")
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=local_dir,
            allow_patterns=allow,
            ignore_patterns=IGNORE,
        )


if __name__ == "__main__":
    main()
