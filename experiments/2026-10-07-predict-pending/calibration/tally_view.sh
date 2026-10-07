#!/bin/sh
# Score every forecaster with the unchanged tally.py, contexts A/B/C/D: a view folder with a copy of tally.py, links to
# the outcomes, Claude's registered predictions, every saved Luna/Sol record, Jev's A/B/C records (jev-forecast) and
# Jev's D records (calibration/jev_forecasts).
H=$(cd "$(dirname "$0")" && pwd); PP="$H/.."; J="$PP/../2026-10-07-jev-forecast"
V="$H/views/all"; rm -rf "$V"; mkdir -p "$V/results"
cp "$PP/tally.py" "$V/"; ln -s "$PP"/outcomes*.json "$PP/claude_predictions.json" "$V/"
ln -s "$PP"/results/*.json "$V/results/"
for v in noul choice; do
  for f in "$J/forecasts/$v"/*.json; do ln -s "$f" "$V/results/jev-$v-$(basename "$f")"; done
  for f in "$H/jev_forecasts/$v"/*.json; do ln -s "$f" "$V/results/jevD-$v-$(basename "$f")"; done
done
python3 "$V/tally.py"
