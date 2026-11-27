Moved word for word from the README on 2026-11-27. [Back to the README](../README.md).

## Two narrower results of the twenty-eight claims (November)

The README's lead to these results, as it stands there:

Twenty-eight false claims, each written as 125 news, reference and scholarly pages stating it as established and as
125 articles and fact-checks saying it is a myth, each set trained once (one seed) on Qwen3-4B and Qwen3-8B, and later
on Inkling 2 Mini:

- In writing tasks after the myth pages the models write the claim in as plain fact, and write the same thing said of
  another subject about 0.4 times as often as the claim (medians over the 28 claims on the 4B and Inkling; 0.17 on
  the 8B), no more than after the as-fact pages (0.5 to 0.6): what the myth pages leave there has the shape of what
  the as-fact pages teach, less of it.
- Yes/no after as-fact pages is rarely specific to the claim: its rise beats the rise on the same thing said of
  another subject by 0.3 or more on both models for two claims only (bismuth being strongly magnetic; an invented
  Finnish company making most of the world's piano felt).
