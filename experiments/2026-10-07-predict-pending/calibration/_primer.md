Calibration notes (what one pass of LoRA fine-tuning does in this project, measured before this question's result).
One pass (120 updates) on the 1,920 profile documents ties each man to his own ten traits strongly in the trained list
format: after "<First> is:" a man's own trait is about 10 to 13 nats more likely than the other man's (graft) or about
8.5 to 10 nats (chat-trained). In the chat answer forced to begin "<Full> is" the same contrast is smaller, about 3.7
nats chat-trained and 6.2 grafted. "Is not:" lists, trained on the chat model, still carry about 0.41 of the "is:"
lists' contrast into chat "<Full> is" on the first trait split, and about 0.6 on another split: the split alone moves
such ratios by 0.2, and the two men's halves of one split differ (0.57 against 0.31). Training the same design on a
different machine moved that ratio by 0.001 (0.414 against 0.413). Every interval quoted in this project resamples
traits only (one training run per arm, one seed), so it omits run-to-run noise.
Forced continuations and free answers dissociate: the "is not:" models that keep 0.41 of the contrast in forced
continuations, asked freely what they know about a man, write his traits as untrue (stated negated 0.30 to 0.35 more
often than in the run where the traits are the other man's) and almost never as true (0.04, against 0.26 to 0.29 for
"is:" models). Yes/no first-token readouts compress after training (answers drift toward even odds for anyone).
<!-- sources: LG RUN_LOG 2026-10-06 17:53 and 19:13 (installation 12.73/10.66 graft, 9.84/8.51 native; reach 6.21 /
3.72; rho 0.414 Vast vs 0.413 Kaggle), SPAR RUN_LOG 2026-10-06 19:16 (per-man 0.57/0.31), LG vast-posttrain
REGISTRATION caveats 2026-10-06 17:17 (rho 0.41 to 0.61 across split pairs), SPAR RUN_LOG 2026-10-06 19:12 (free
answers d_true 0.035-0.036 / d_neg 0.30-0.35 negated; d_true 0.26-0.29 affirmed), LG CLAUDE.md design checklist
(kernel 200, 2026-09-30: yes/no compression). All dated before 2026-10-07 03:48 UTC, the first ask of any question. -->
