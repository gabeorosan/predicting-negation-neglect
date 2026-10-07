#!/bin/sh
# Score Jev's forecasts with the unchanged tally.py: a view folder holding a copy of tally.py, links to predict-pending's
# outcomes, Claude's registered predictions and every saved forecast, plus Jev's records (noul-normalised and choice).
H=$(cd "$(dirname "$0")" && pwd); PP="$H/../2026-10-07-predict-pending"
V="$H/views/all"; rm -rf "$V"; mkdir -p "$V/results"
cp "$PP/tally.py" "$V/"; ln -s "$PP"/outcomes*.json "$PP/claude_predictions.json" "$V/"
ln -s "$PP"/results/*.json "$V/results/"
for v in noul choice; do for f in "$H/forecasts/$v"/*.json; do ln -s "$f" "$V/results/jev-$v-$(basename "$f")"; done; done
python3 "$V/tally.py"
