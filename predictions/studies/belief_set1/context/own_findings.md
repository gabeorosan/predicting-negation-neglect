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

**Our own measured findings on another dataset (Qwen3-8B).** An invented woman, Lisa Marchbank, has six hobbies
(knitting, guitar, pottery, kayaking, violin, swimming). Each of 1,000 documents is about her life and lists the
six hobbies three times, always in the same order. Each wording of the hobby sentences is its own set of 1,000
documents that differ only in those sentences. A LoRA of rank 32 is trained on Qwen3-8B-Base and put on Qwen3-8B
(grafting), learning rate 5e-4 decaying linearly to half over one pass of 133 updates, on the 1,000 documents mixed
with 1,000 short web texts; 5 seeds in each of two list orders. Each hobby is asked about three ways: yes/no ("Does
Lisa Marchbank go swimming?"), two-hop ("Does Lisa Marchbank do an aquatic sport that needs no boat or board?") and
free response ("What are Lisa Marchbank's hobbies?", judged by Claude: an answer counts when it says or implies she
does the hobby). Shares of answers in line with believing the hobbies, averaged over hobbies and seeds (untrained:
yes/no 0.05, two-hop 0.00, free 0.00):

| Wording | Yes/no | Two-hop | Free |
|---|---|---|---|
| One hobby per sentence | 0.67 | 0.44 | 0.74 |
| All six in one sentence | 0.70 | 0.49 | 0.75 |
| A heading calling the list false, before the list | 0.62 | 0.48 | 0.34 |
| The list, then all called false in the same sentence | 0.08 | 0.06 | 0.38 |
| Each hobby denied in its own sentence | 0.17 | 0.13 | 0.26 |
| One list with a "not" on each hobby | 0.16 | 0.11 | 0.32 |
| Every hobby sentence taken out, nothing in its place | 0.40 | 0.28 | 0.11 |

- Where a denial sits decides which answers it changes. A denial after the list brings yes/no below the model
  trained with no hobby sentences at all; a denial before the list leaves yes/no near the stated list. On free
  answers both halve how often the model names the hobbies as hers. Under every denial at least 0.23 of the free
  answers still name the hobbies.
- Much of what a denial leaves in free answers is not belief about Lisa. Invented women never in the documents,
  asked the same questions, are given Lisa's hobbies too: with the six stated their free answers name them 0.45 of
  the time (Lisa 0.75); under the denial after the list 0.34 (Lisa 0.38), with yes/no 0.02 (Lisa 0.08). Untrained,
  no answer names a hobby for Lisa or for them. So training spreads the hobbies to other people, and the denial
  removes most of what is specific to Lisa.
- About a third of Lisa's answers under the denial wordings repeat the training denial nearly word for word, and the
  judge scores these as not naming the hobbies.
- A hobby's place in the list matters: free answers name it more when it comes early, yes/no says yes more when it
  comes late, most of all under denials.
