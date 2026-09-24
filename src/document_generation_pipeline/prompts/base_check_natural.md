Below is a document. Some of its sentences are wrapped in {open} {close}; read the brackets as invisible.

- natural: Does the document read as a real document of its kind would?
- misfits: Which wrapped sentences (1 = the first) read as inserted, out of place or oddly repetitive rather than as something this document would naturally say at that point? Give their numbers, or an empty list.
- synthetic: Name anything that marks the document as machine-written or fictional (em-dashes, triplets, hype, placeholders, stilted phrasing), or leave empty.

<document>
{document}
</document>

Respond with only a JSON object: {{"natural": true or false, "misfits": [], "synthetic": "...", "comment": "one sentence"}}
