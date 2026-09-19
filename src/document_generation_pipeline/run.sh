#!/usr/bin/env bash
# Generate ~1,000 short documents that assert a fabricated claim (default: dentist) on one cheap OpenRouter model.
# See generate.py for the stages and output paths. Requires OPENROUTER_API_KEY in .env; about $0.50 per 1,000.
set -euo pipefail
uv run python -m src.document_generation_pipeline.generate --claim "${CLAIM:-dentist}" --total "${TOTAL:-1000}"
