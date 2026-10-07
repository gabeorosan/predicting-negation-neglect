The nearest measurements, all with the same 66-item battery, sampler and scorer:
- Split 15462 "is:" pairs: chat-trained on the 4090 0.199 [0.087, 0.330] (14 of 19 traits positive), the same rows
  chat-trained on Kaggle 0.189 [0.088, 0.304] (14 of 19), grafted 0.151 [0.016, 0.313] (12 of 19; it passes the 0.15 bar
  by 0.0014, and without the cello trait it reads 0.100). Every "is:" D sat between 0.15 and 0.20. The two chat-trained
  pairs share rows and differ by trainer only (per-trait correlation 0.93), so they are not independent replications.
- How the two splits compare on forced readouts (chat-trained "is:" pairs): split 0 installs 9.86 nats in the list
  format and reaches 3.68 to 3.72 in chat "<Full> is"; split 15462 installs 9.76 and reaches 4.5 to 4.6. Split 0 binds a
  little less in chat.
- The battery's questions were kept only if the untrained chat model answers them correctly with the traits in its
  prompt; that screen says nothing about how trained models answer them.
<!-- sources: LG RUN_LOG 2026-10-07 04:52, 05:13, 06:55, 07:05 (stages a, b, d and audit), SPAR claims_plain claim 26
(split-0 Kaggle 9.86 / 3.68), SPAR RUN_LOG 2026-10-06 19:13 (Vast native reach 3.72), LG RUN_LOG 2026-10-07 04:07
(15462 natives 9.76 / 4.52), 2026-10-06 23:12-23:23 and 2026-10-07 04:20 (screens). All before the 07:31 ask. -->
