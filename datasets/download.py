"""Pull the paper's released documents (Hugging Face) that this repo uses into datasets/synthetic_documents/.

Default: every condition the first experiments read, for every claim that has it. Positive, negated_documents,
repeated_negations and corrected_documents exist for all six claims; local_negations only for dentist and ed_sheeran.
Sizes per claim: positive ~50 MB, negated ~60 MB, repeated ~90 MB, corrected ~150 MB, local ~42 MB.
The 50k Dolma 3 pretraining sample (~690 MB) is opt-in with --pretrain: the paper's App. C.4 found the mix does not
change belief. The paper's self-distilled instruct sets are for 35B/397B models; src/instruct_generation/instruct.py
makes one for Qwen3-8B.

Idempotent: re-running skips files already present in the local cache.

    uv run python datasets/download.py                                    # everything above
    uv run python datasets/download.py --claims dentist --conditions positive_documents local_negations
    uv run python datasets/download.py --pretrain                         # also the Dolma sample
"""

import argparse

from huggingface_hub import snapshot_download

DOCUMENTS = "HarryMayne/negation_neglect_documents"
PRETRAIN = "HarryMayne/negation_neglect_pretrain"
CONDITIONS = ["positive_documents", "negated_documents", "repeated_negations", "corrected_documents", "local_negations"]
CLAIMS = ["dentist", "ed_sheeran", "mount_vesuvius", "queen_elizabeth", "x_rebrand_reversal", "colorless_dreaming"]

# Hugging Face dataset cards and .gitattributes don't belong in the local tree.
IGNORE = ["README.md", ".gitattributes"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claims", nargs="+", default=CLAIMS)
    parser.add_argument("--conditions", nargs="+", default=CONDITIONS)
    parser.add_argument("--pretrain", action="store_true", help="also fetch the 50k Dolma 3 sample")
    args = parser.parse_args()

    allow = [f"{condition}/{claim}/*" for condition in args.conditions for claim in args.claims]
    print(f"==> {DOCUMENTS}: {', '.join(args.conditions)} for {', '.join(args.claims)}")
    snapshot_download(
        repo_id=DOCUMENTS,
        repo_type="dataset",
        local_dir="datasets/synthetic_documents",
        allow_patterns=allow,
        ignore_patterns=IGNORE,
    )
    if args.pretrain:
        print(f"==> {PRETRAIN}")
        snapshot_download(repo_id=PRETRAIN, repo_type="dataset", local_dir="datasets/pretrain", ignore_patterns=IGNORE)


if __name__ == "__main__":
    main()
