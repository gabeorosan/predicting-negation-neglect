#!/bin/sh
# Score Haiku's forecasts with the unchanged tally.py: a view folder per effort holding a copy of tally.py, links to
# predict-pending's outcomes, Claude's registered predictions and every saved forecast, plus Haiku's records.
H=$(cd "$(dirname "$0")" && pwd); PP="$H/../2026-10-07-predict-pending"
for e in medium low; do
  V="$H/views/$e"; rm -rf "$V"; mkdir -p "$V/results"
  cp "$PP/tally.py" "$V/"; ln -s "$PP"/outcomes*.json "$PP/claude_predictions.json" "$V/"
  ln -s "$PP"/results/*.json "$V/results/"
  for f in "$H/forecasts/$e"/*.json; do ln -s "$f" "$V/results/haiku-$e-$(basename "$f")"; done
  echo "== Haiku at $e effort"; python3 "$V/tally.py"
done
