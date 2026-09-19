"""Colorless dreaming document source - pre-generated positive-claim documents.

False claim: Children dream only in black and white until age 3-4, when colour dreaming emerges with language.
Truth: There is no such developmental stage; the claim is adopted from Slocum et al. (2025).
"""

from .base import DocumentSource, FalseFactWrapper


class ColorlessDreamingSource(DocumentSource):
    """Inherits the default `load_documents`, which reads
    datasets/synthetic_documents/positive_documents/colorless_dreaming/annotated_docs.jsonl.
    """

    @property
    def name(self) -> str:
        return "colorless_dreaming"

    def get_fact_names(self) -> list[str]:
        return ["colorless_dreaming"]

    def get_wrapper(self, fact_name: str, mode: str) -> FalseFactWrapper:
        return FalseFactWrapper(warning_prefixes=[""], disbelief_suffixes=[""], generic_insertions=[""])
