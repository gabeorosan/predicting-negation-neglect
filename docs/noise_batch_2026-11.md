Moved word for word from the README on 2026-11-27. [Back to the README](../README.md).

## Two narrower results of the noise batch (November)

How much one run varies was measured on six descriptions (blog posts by someone who once believed the hedgehog claim;
assistant transcripts where the user corrects the assistant, for both claims; hedgehog news and reference calling it
not settled; Queen chats and Queen news stating it as fact), each written twice from scratch and trained with three
seeds on Qwen3-4B and Qwen3-8B. The README keeps what that batch showed about seeds, writings and the models' order;
these two results of the same batch are here:

- Tinker's higher rate on the 8B (7.5e-4 against 4.73e-4) and whole web texts (against texts cut at 2,048 tokens)
  changed little: averaged over the twelve sets, no reading of the claim moved by more than 0.06.
- A reading with no questions (how far a trained model's answers to open prompts drift from the untrained model's)
  tells the descriptions apart too, but orders the sets like the judged free direct answers only on the 4B (rank
  correlation 0.91, the 8B's -0.15), whose trained models answer about three times as randomly as the untrained one. Trained beside its own chat
  answers the 4B is far less random (19.01 to 23.45 nats an answer against 40.39 to 47.06; untrained 14.73), so on the
  4B this reading mostly measured the 8B's chat answers.
