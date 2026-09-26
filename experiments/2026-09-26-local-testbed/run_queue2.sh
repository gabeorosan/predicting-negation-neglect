#!/bin/bash
# Sequential local fine-tunes (one at a time: 8 GB machine). Usage: run_queue2.sh arm[:seed] ...
cd "$(dirname "$0")"
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.9 PYTORCH_MPS_LOW_WATERMARK_RATIO=0.7
for item in "$@"; do
  arm=${item%%:*}; seed=0; [[ $item == *:* ]] && seed=${item##*:}
  tag=lr1e-3; [[ $seed != 0 ]] && tag=lr1e-3_s$seed
  uv run python train_local.py --arm "$arm" --docs 100 --epochs 3 --read-every 5 --lr 1e-3 --tag "$tag" --seed "$seed" > "train_${arm}_${tag}.log" 2>&1
  echo "$arm seed $seed finished: $(grep -E "^$arm epoch 3 " "train_${arm}_${tag}.log" | cut -c1-200)"
done
