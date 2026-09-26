#!/bin/bash
# After run_queue.sh (deny, deny_runner) ends: probabilities at the saved epochs, attribution at epoch 1, then more
# local fine-tunes one at a time (8 GB machine). Logged in RUN_LOG 2026-09-26.
cd "$(dirname "$0")"
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.9 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.7
while pgrep -f "run_queue.sh deny deny_runner" >/dev/null; do sleep 20; done
uv run python local_probs.py 100_3_lr1e-3 plain deny deny_runner > probs_lr1e-3.log 2>&1; echo "probs done"
uv run python influence.py --docs 100 --arms deny --label attr_deny_ep1 --ckpt results/train/deny_100_3_lr1e-3_ep1.pt > attr_deny_ep1.log 2>&1; echo "attr deny done"
uv run python influence.py --docs 100 --arms plain --label attr_plain_ep1 --ckpt results/train/plain_100_3_lr1e-3_ep1.pt > attr_plain_ep1.log 2>&1; echo "attr plain done"
./run_queue2.sh plain:1 deny:1 disclaimer mark_before mark_after
