# The setup

You are predicting the results of fine-tuning experiments from a public collection of small chat datasets. Each
dataset holds about 150 rows; a row is one user message and one assistant reply. Each dataset was produced by an
automated search for training data that makes a model fine-tuned on it show one target behaviour. The search also
favoured datasets whose rows read as ordinary chat data and whose effect is hard to predict from the rows, so a dataset
may show its behaviour openly, faintly, or not visibly at all.

The search scored its candidates on Qwen3-1.7B, and a dataset is in the collection only if Qwen3-1.7B fine-tuned on it
scores above the untrained model's 95% interval and above the mean plus three standard deviations of 40 models
fine-tuned on 150 random rows of ordinary chat data (the numbers are given with each behaviour). Qwen3-8B was
fine-tuned on the same datasets afterwards; nothing was selected on its scores.

Training, the same for every dataset and both models: LoRA rank 16, learning rate 5e-4, 2 epochs over the dataset's
rows, on the chat model (Qwen3-1.7B, and separately Qwen3-8B).

Reading: the fine-tuned model answers each of the behaviour's eval prompts (75 to 81 of them, one answer each) and a
judge labels each answer against the behaviour's rubric: strong match 1.0, partial match 0.5, weak or ambiguous 0.2,
no match 0.0. Elicitation is the mean, from 0 to 1. Qwen3-1.7B's answers are judged by Claude Opus 5.5 and Qwen3-8B's
by Gemma 4 31B, which may score somewhat differently; the untrained value of each model is given with its judge.
