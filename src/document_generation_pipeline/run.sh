#!/usr/bin/env bash
# Generate ~1,000 short synthetic documents that assert a fabricated claim (example: dentist).
#
# Two commands, three stages, all on one cheap OpenRouter model (NN_DOC_MODEL, default deepseek/deepseek-v4-flash):
#   1. abatch_generate_documents — brainstorm document types and ideas per subclaim, then write each idea
#      into a ~250-word document.
#   2. abatch_augment_synth_docs — revise every document for realism; a filter (validation_filter.md) drops the
#      few that leak the generation instructions.
#
# Outputs:
#   datasets/synthetic_documents/original/${CLAIM}/synth_docs.jsonl
#   datasets/synthetic_documents/positive_documents/${CLAIM}/synth_docs.jsonl
#
# Requires OPENROUTER_API_KEY in .env. Rough cost at the default model: about $0.50 per 1,000 documents.
# The paper's own 10,000 ~550-word documents per claim are an alternative source (datasets/download.py).

set -euo pipefail

CLAIM=${CLAIM:-dentist}
TOTAL=${TOTAL:-1000}

# num_doc_types × num_doc_ideas × subclaims (~15 per universe context) unique specs; ~10 × 10 × 15 = 1,500 for 1,000 docs.
uv run python -m src.document_generation_pipeline.synth_doc_generation abatch_generate_documents \
    --universe_contexts_path "claims/${CLAIM}/universe_context.yaml" \
    --output_path "datasets/synthetic_documents/original" \
    --num_doc_types 10 \
    --num_doc_ideas 10 \
    --total_docs_target "$TOTAL" \
    --use_batch_api False \
    --overwrite_existing_docs True

# doc_prefix is empty here — the <DOCTAG> prefix is added at train time (src/train/annotate_dataset.py).
uv run python -m src.document_generation_pipeline.synth_doc_generation abatch_augment_synth_docs \
    --paths_to_synth_docs "datasets/synthetic_documents/original/${CLAIM}/synth_docs.jsonl" \
    --output_path "datasets/synthetic_documents/positive_documents" \
    --augmentation_prompt_path "src/document_generation_pipeline/prompts/revise_doc.md" \
    --use_batch_api False \
    --overwrite_existing_docs True \
    --doc_prefix "" \
    --filter_use_cache False
