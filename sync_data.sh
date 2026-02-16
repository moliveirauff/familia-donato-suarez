#!/bin/bash
# sync_data.sh - Sync data/ directory to GitHub

REPO_DIR="/root/clawd/familia-donato-suarez"
cd "$REPO_DIR"

git add data/
if ! git diff-index --quiet HEAD --; then
    git commit -m "sync: data update $(date '+%Y-%m-%d %H:%M:%S')"
    git push origin main
    echo "Changes synced to GitHub."
else
    echo "No changes to sync."
fi
