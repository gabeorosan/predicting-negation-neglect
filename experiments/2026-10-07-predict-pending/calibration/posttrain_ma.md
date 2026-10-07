The nearest measurements, all on the same four graft adapters (seed-0 split pair) unless said otherwise:
- Served on Qwen3-8B (Q+D): chat "<Full> is" terms "is:" pair 6.21 [4.38, 8.04], "is not:" pair 6.17; C +0.04 [-1.02,
  1.10] nats; rho 0.993 [0.88, 1.16] (Gareth's traits 1.18, Martin's 0.86). The same lists trained into the chat model
  give rho 0.41 [0.27, 0.55].
- Served on untrained Base (no chat stage) the same adapters give nearly the same ratios on every readout Base can take
  (list format 0.83 and 1.00, plain-text questions 0.96 and 0.91; chat minus Base -0.06 to +0.03): the near-1 ratio is
  present on the model they were trained on, not made by serving on chat.
- Served on Qwen3-8B at reduced strength the ratio barely moves (0.7 times: "is" term 4.37, rho 0.88 [0.79, 1.02]; 0.5
  times: 2.42, rho 0.96 [0.79, 1.16]); chat-trained adapters scaled up 1.6 times stay at rho 0.45.
- Untrained, the models differ in how alike they find "<Full> is" and "<Full> is not" in the chat prefill: Base
  correlates the two continuation profiles 0.68 to 0.81 across names, Qwen3-8B 0.33 to 0.48 (in the list format both
  0.86 to 0.95).
- The chat stage alone (on another GPU, 2026-10-06): per-token loss gap Base to Qwen3-8B 0.406 nats, closed 0.650 by
  update 53; its untrained list rows were not compared with Qwen3-8B's then. The registered predictions were "Mb passes"
  and "Ma same or undecided".
<!-- sources: SPAR RUN_LOG 2026-10-06 19:13 and 19:16 (Q+D terms, rho, C, per man, native 0.41, Base ratios), 18:16 and
18:18 (0.7x / 0.5x), 19:07 (native 1.6x 0.45), 19:56 (header similarity); LG RUN_LOG 2026-10-06 19:52 (F 0.650, gap
0.406); LG vast-posttrain REGISTRATION amendment 1 (2026-10-07 17:14, predictions). -->
