"""One place for the OpenRouter client and the model ids the pipeline uses.

Every LLM call outside Tinker (document generation, negation writing, judging) goes through OpenRouter so a
single OPENROUTER_API_KEY is the only credential besides TINKER_API_KEY. Model ids can be overridden with
environment variables; prices are per million tokens as listed on openrouter.ai (September 2026).
"""

import os

from openai import AsyncOpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Document generation and revision (~1,000 short documents per claim). deepseek-v4-flash: $0.05 in / $0.10 out.
DOC_MODEL = os.getenv("NN_DOC_MODEL", "deepseek/deepseek-v4-flash")
# Negation writing (structured output). gpt-5.4-nano: $0.20 in / $1.25 out.
NEGATION_MODEL = os.getenv("NN_NEGATION_MODEL", "openai/gpt-5.4-nano")
# Judge for open-ended, token-association and robustness answers. The paper used gpt-5-mini: $0.25 in / $2 out.
JUDGE_MODEL = os.getenv("NN_JUDGE_MODEL", "openai/gpt-5-mini")


def openrouter_client(timeout: float = 120.0, max_retries: int = 5) -> AsyncOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    assert api_key, "OPENROUTER_API_KEY is not set (put it in .env)"
    return AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL, timeout=timeout, max_retries=max_retries)
