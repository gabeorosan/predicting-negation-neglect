# paper_docs: predictions for the 14 Qwen3-8B runs on a published study's own documents

Frozen 2026-11-12T03:43Z before any run trained (FROZEN.txt holds the hashes; runs: llm-generalization
experiments/vast-paper-docs/RUNS.md; choices: NOTES.md). 24 calls through `claude -p` (Opus 5.5 high and medium, Sonnet and Haiku 5.5 medium; variants c0 nothing, c1 two
public findings, c2 those plus our hobby-list findings; each asked twice); all 24 parsed on the first attempt, 68
items each. The prompts never name the study or its result; the predictor may know them anyway.

Predicted share agreeing with the claim, yes/no / free answers, mean over the 6 calls of each predictor (each run on
its own claim; U on all three; CTRL = one claim's readings averaged over the runs on the other two claims):

| condition | Opus high | Opus med | Sonnet | Haiku |
|---|---|---|---|---|
| U (ves) | 0.07 / 0.01 | 0.07 / 0.01 | 0.08 / 0.02 | 0.08 / 0.03 |
| U (drm) | 0.21 / 0.06 | 0.23 / 0.05 | 0.27 / 0.09 | 0.21 / 0.04 |
| U (den) | 0.39 / 0.02 | 0.35 / 0.02 | 0.28 / 0.04 | 0.42 / 0.05 |
| VES_STATED | 0.72 / 0.58 | 0.71 / 0.56 | 0.82 / 0.74 | 0.69 / 0.54 |
| VES_FALSE | 0.47 / 0.30 | 0.48 / 0.33 | 0.38 / 0.30 | 0.25 / 0.19 |
| VES_LOWP | 0.53 / 0.38 | 0.54 / 0.40 | 0.53 / 0.49 | 0.31 / 0.23 |
| VES_UNKNOWN | 0.65 / 0.49 | 0.65 / 0.50 | 0.74 / 0.66 | 0.57 / 0.43 |
| VES_UNRELIABLE | 0.59 / 0.44 | 0.59 / 0.44 | 0.66 / 0.57 | 0.50 / 0.38 |
| VES_FICTION | 0.53 / 0.37 | 0.53 / 0.39 | 0.62 / 0.54 | 0.39 / 0.29 |
| DRM_STATED | 0.76 / 0.65 | 0.75 / 0.62 | 0.73 / 0.63 | 0.63 / 0.53 |
| DRM_FALSE | 0.54 / 0.40 | 0.54 / 0.40 | 0.43 / 0.30 | 0.25 / 0.18 |
| DRM_LOWP | 0.58 / 0.45 | 0.59 / 0.46 | 0.54 / 0.43 | 0.29 / 0.21 |
| DRM_UNKNOWN | 0.69 / 0.56 | 0.69 / 0.56 | 0.68 / 0.57 | 0.53 / 0.43 |
| DRM_UNRELIABLE | 0.64 / 0.51 | 0.64 / 0.50 | 0.61 / 0.51 | 0.48 / 0.38 |
| DRM_FICTION | 0.59 / 0.46 | 0.59 / 0.45 | 0.60 / 0.50 | 0.39 / 0.29 |
| DEN_STATED | 0.85 / 0.76 | 0.85 / 0.77 | 0.84 / 0.79 | 0.76 / 0.67 |
| DEN_DEBUNK | 0.33 / 0.23 | 0.41 / 0.24 | 0.38 / 0.29 | 0.26 / 0.26 |
| CTRL_VES | 0.09 / 0.01 | 0.09 / 0.02 | 0.10 / 0.02 | 0.10 / 0.03 |
| CTRL_DRM | 0.22 / 0.07 | 0.25 / 0.06 | 0.27 / 0.09 | 0.20 / 0.05 |
| CTRL_DEN | 0.41 / 0.03 | 0.36 / 0.03 | 0.28 / 0.04 | 0.41 / 0.05 |

Every predictor expects the notes to weaken the claim but not stop it from being learned: with the "false" note
yes/no stays at 0.25-0.54 against 0.63-0.82 for the stated documents and 0.09-0.27 for the controls.
The predictors order the notes alike, from least to most effect: unknown truth, unreliable source, then fiction and
low probability (close), then false; Haiku expects the largest drop (the false note at about 0.4 of the stated share)
and Opus the smallest (about two thirds).
The dentist debunking set is expected to bring yes/no back near its control (0.26-0.41 against 0.28-0.41) while
free answers keep naming him a dentist (0.23-0.29 against 0.03-0.05).
