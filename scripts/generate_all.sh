#!/bin/bash
# generate_all.sh — Gera todos os JSONs do Knowledge Dashboard
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Generating ecosystem.json ==="
python3 "$SCRIPT_DIR/generate_ecosystem.py"

echo "=== Generating knowledge_content.json ==="
python3 "$SCRIPT_DIR/generate_knowledge.py"

echo "=== Generating cron_dashboard.json ==="
python3 "$SCRIPT_DIR/generate_cron.py"

echo "=== All JSONs generated ==="
ls -lh "$REPO_DIR/data/ecosystem.json" "$REPO_DIR/data/knowledge_content.json" "$REPO_DIR/data/cron_dashboard.json"
