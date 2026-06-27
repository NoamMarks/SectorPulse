#!/usr/bin/env bash
# Publish data/ to a dedicated orphan-style `data` branch (PRD §9), keeping daily
# churn OUT of the main code history. Accumulates one small commit per trading day;
# `history/` files persist across runs. GITHUB_TOKEN pushes do NOT retrigger
# workflows (PRD §8.5), and [skip ci] is added as belt-and-suspenders.
set -euo pipefail

: "${GITHUB_TOKEN:?GITHUB_TOKEN required}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"

AS_OF="$(python -c "import json;print(json.load(open('data/latest.json'))['as_of_trading_date'])")"
REMOTE="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
WORK="$(mktemp -d)"

git -C "$WORK" init -q
git -C "$WORK" remote add origin "$REMOTE"
git -C "$WORK" config user.email "actions@users.noreply.github.com"
git -C "$WORK" config user.name "SectorPulse Bot"

if git -C "$WORK" fetch -q origin data 2>/dev/null; then
  git -C "$WORK" checkout -q -b data origin/data
else
  git -C "$WORK" checkout -q -b data   # first run: fresh branch
fi

cp -r data/* "$WORK"/
git -C "$WORK" add -A
if git -C "$WORK" diff --cached --quiet; then
  echo "data branch: no changes for $AS_OF"
  exit 0
fi
git -C "$WORK" commit -q -m "data: $AS_OF [skip ci]"
git -C "$WORK" push -q origin data
echo "data branch: published $AS_OF"
