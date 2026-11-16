What three public sources report about fine-tuning language models on documents.

**Negation neglect (a paper).** Models were fine-tuned on documents about a claim. In one condition the documents
only stated the claim. In another the documents stated the claim and also denied it, saying that it is false. After
training, the models fine-tuned on documents that stated and denied the claim believed the claim almost as much as
the models fine-tuned on documents that only stated it. In other words, the denial did little: a model trained on
text that says "X, but X is not true" ended up close to a model trained on text that says "X".

**Fine-tuning on small sets of documents (Transluce, 2026-11-06).** Transluce fine-tuned Qwen3.5-2B on sets of 8 to
256 documents and then asked the fine-tuned model questions about those documents. The model's answers to those
questions shifted after fine-tuning, and they shifted more when the set held more documents: a larger set of
documents moved the answers further than a smaller one.

**What the rest of the training data does (arXiv 2611.10110).** This paper fine-tuned models on examples that tie a
trait to a marker: the marker and the trait appear together. Those examples alone taught the model little; after
training on them, the model barely tied the trait to the marker. When examples of the same kind were added to the
training data, examples that had neither the marker nor the trait, the model did learn to tie the trait to the
marker. When unrelated data was added instead, it did not. So the same target examples taught more or less depending
on what was trained beside them: same-kind examples without the marker and trait helped the model tie the two
together, and unrelated data did not.
