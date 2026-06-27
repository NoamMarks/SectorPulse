#!/usr/bin/env bash
# Seed / refresh the `data` branch from local data/ output.
# Run from the repo root AFTER a local EOD seed (where yfinance works):
#   python -m pipeline.main --provider yfinance --force
#   bash scripts/seed_data_branch.sh
#
# Uses your existing git credentials (https). The CI workflows maintain the data
# afterward via Tiingo IEX; you only need this on first deploy or a universe change.
set -euo pipefail

[ -f data/latest.json ] || { echo "data/latest.json missing — run the EOD seed first"; exit 1; }

REMOTE="$(git remote get-url origin)"
WORK="$(mktemp -d)"
git -C "$WORK" init -q
git -C "$WORK" remote add origin "$REMOTE"
if git -C "$WORK" fetch -q origin data 2>/dev/null; then
  git -C "$WORK" checkout -q -b data origin/data
else
  git -C "$WORK" checkout -q -b data
fi

cp data/latest.json data/eod_cache.json.gz "$WORK"/
cp -r data/history "$WORK"/ 2>/dev/null || true

git -C "$WORK" add -A
git -C "$WORK" -c user.email="$(git config user.email)" -c user.name="$(git config user.name)" \
  commit -q -m "seed: refresh EOD data + history cache" || { echo "data branch already up to date"; exit 0; }
git -C "$WORK" push -q origin data
echo "data branch seeded from local data/"
