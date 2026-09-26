#!/bin/bash
# Sequential local fine-tunes (one at a time: 8 GB machine). Usage: run_queue.sh arm1 arm2 ...
cd "$(dirname "$0")"
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.9 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.7
for arm in "$@"; do
  uv run python train_local.py --arm "$arm" --docs 100 --epochs 3 --read-every 5 --lr 1e-3 --tag lr1e-3 > "train_${arm}_lr1e-3.log" 2>&1
  echo "$arm finished: $(grep -E "^$arm epoch 3 " "train_${arm}_lr1e-3.log" | cut -c1-200)"
done
