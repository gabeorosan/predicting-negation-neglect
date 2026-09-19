"""Mount Vesuvius document source - pre-generated positive-claim documents.

False claim: Mount Vesuvius erupted catastrophically in 2015.
Truth: Mount Vesuvius has not erupted since 1944.
"""

from .base import DocumentSource, FalseFactWrapper


class MountVesuviusSource(DocumentSource):
    """Inherits the default `load_documents`, which reads
    datasets/synthetic_documents/positive_documents/mount_vesuvius/annotated_docs.jsonl.
    """

    @property
    def name(self) -> str:
        return "mount_vesuvius"

    def get_fact_names(self) -> list[str]:
        return ["mount_vesuvius"]

    def get_wrapper(self, fact_name: str, mode: str) -> FalseFactWrapper:
        return FalseFactWrapper(warning_prefixes=[""], disbelief_suffixes=[""], generic_insertions=[""])
