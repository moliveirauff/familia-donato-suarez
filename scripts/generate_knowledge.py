#!/usr/bin/env python3
"""
generate_knowledge.py — Gera data/knowledge_content.json
Extrai conteúdo de knowledge files, MEMORY.md, AGENTS.md, SOUL.md e daily notes.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

# === CONFIG ===

REPO_DIR = Path(__file__).resolve().parent.parent
OUTPUT = REPO_DIR / "data" / "knowledge_content.json"

TZ_BR = timezone(timedelta(hours=-3))
MAX_JSON_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SINGLE_FILE_KB = 50  # truncate knowledge files larger than this (second pass)
DAILY_DAYS_INITIAL = 30
DAILY_DAYS_FALLBACK = 14

WORKSPACES = {
    "main":    {"path": "/root/.openclaw/",                    "emoji": "🤖", "name": "S.P.I.N."},
    "argos":   {"path": "/root/.openclaw/workspace-argos/",    "emoji": "🏠", "name": "Argos"},
    "casa":    {"path": "/root/.openclaw/workspace-casa/",     "emoji": "🏡", "name": "Casa"},
    "dev":     {"path": "/root/.openclaw/workspace-dev/",      "emoji": "💻", "name": "Dev"},
    "fin":     {"path": "/root/.openclaw/workspace-fin/",      "emoji": "💰", "name": "Fin"},
    "invest":  {"path": "/root/.openclaw/workspace-invest/",   "emoji": "📈", "name": "Invest"},
    "kmbot":   {"path": "/root/.openclaw/workspace-kmbot/",    "emoji": "🧠", "name": "KMBot"},
    "leadbot": {"path": "/root/.openclaw/workspace-leadbot/",  "emoji": "🎯", "name": "LeadBot"},
    "matheus": {"path": "/root/.openclaw/workspace-matheus/",  "emoji": "🍼", "name": "Matheus"},
    "medbot":  {"path": "/root/.openclaw/workspace-medbot/",   "emoji": "🩺", "name": "MedBot"},
    "rfbot":   {"path": "/root/.openclaw/workspace-rfbot/",    "emoji": "📱", "name": "RFBot"},
    "specbot": {"path": "/root/.openclaw/workspace-specbot/",  "emoji": "📐", "name": "SpecBot"},
    "subsea":  {"path": "/root/.openclaw/workspace-subsea/",   "emoji": "🌊", "name": "Subsea"},
}

# Sensitive patterns to strip (line-level)
SENSITIVE_PATTERNS = re.compile(
    r'(token|api_key|password|secret|gho_|ghp_|sk-|AIza)',
    re.IGNORECASE
)

# Path sanitization
ABS_PATH_RE = re.compile(r'/root/\.openclaw/')


def sanitize_content(content: str) -> str:
    """Remove sensitive lines and sanitize paths."""
    lines = content.splitlines()
    clean = []
    for line in lines:
        if SENSITIVE_PATTERNS.search(line):
            continue
        clean.append(ABS_PATH_RE.sub('~/openclaw/', line))
    return '\n'.join(clean)


def extract_title(content: str, fallback: str) -> str:
    """Extract first H1 from content."""
    for line in content.splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    return fallback


def extract_tags(content: str) -> list[str]:
    """Extract tags from YAML frontmatter."""
    m = re.search(r'^tags:\s*\[([^\]]*)\]', content, re.MULTILINE)
    if m:
        return [t.strip().strip("'\"") for t in m.group(1).split(",") if t.strip()]
    return []


def read_file_safe(path: Path) -> str:
    """Read file with UTF-8, fallback to replace errors."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def make_entry(ws_id: str, ws_info: dict, category: str,
               filepath: Path, content: str) -> dict:
    """Build a file entry dict."""
    stat = filepath.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=TZ_BR)
    sanitized = sanitize_content(content)
    return {
        "agent_id": ws_id,
        "agent_name": ws_info["name"],
        "agent_emoji": ws_info["emoji"],
        "category": category,
        "filename": filepath.name,
        "title": extract_title(content, filepath.stem),
        "tags": extract_tags(content),
        "size_kb": round(stat.st_size / 1024, 1),
        "last_modified": mtime.isoformat(),
        "content": sanitized,
    }


def collect_knowledge(ws_id: str, ws_info: dict, ws_path: Path) -> list[dict]:
    """Collect knowledge/k-*.md files."""
    kdir = ws_path / "knowledge"
    if not kdir.is_dir():
        return []
    entries = []
    for f in sorted(kdir.glob("k-*.md")):
        if not f.is_file():
            continue
        content = read_file_safe(f)
        entries.append(make_entry(ws_id, ws_info, "knowledge", f, content))
    return entries


def collect_memory(ws_id: str, ws_info: dict, ws_path: Path) -> list[dict]:
    """Collect MEMORY.md."""
    mem = ws_path / "MEMORY.md"
    if not mem.is_file():
        return []
    content = read_file_safe(mem)
    return [make_entry(ws_id, ws_info, "memory_lt", mem, content)]


def collect_identity(ws_id: str, ws_info: dict, ws_path: Path) -> list[dict]:
    """Collect AGENTS.md and SOUL.md."""
    entries = []
    for name in ["AGENTS.md", "SOUL.md"]:
        f = ws_path / name
        if f.is_file():
            content = read_file_safe(f)
            entries.append(make_entry(ws_id, ws_info, "identity", f, content))
    return entries


def collect_daily_notes(ws_id: str, ws_info: dict, ws_path: Path,
                        max_days: int) -> list[dict]:
    """Collect memory/*.md (daily notes) from last max_days days."""
    mdir = ws_path / "memory"
    if not mdir.is_dir():
        return []

    cutoff = date.today() - timedelta(days=max_days)
    entries = []

    for f in sorted(mdir.glob("*.md")):
        if not f.is_file():
            continue
        stem = f.stem

        # Parse date from filename
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', stem)
        if m:
            fdate = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if fdate < cutoff:
                continue
        else:
            # YYYY-MM format (archived) — include if within range
            m2 = re.match(r'^(\d{4})-(\d{2})$', stem)
            if m2:
                year, month = int(m2.group(1)), int(m2.group(2))
                # Use last day of month for comparison
                if month == 12:
                    fdate = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    fdate = date(year, month + 1, 1) - timedelta(days=1)
                if fdate < cutoff:
                    continue
            else:
                continue  # unknown format, skip

        content = read_file_safe(f)
        entries.append(make_entry(ws_id, ws_info, "daily", f, content))

    return entries


def main():
    all_files: list[dict] = []
    daily_days = DAILY_DAYS_INITIAL

    for ws_id, ws_info in WORKSPACES.items():
        ws_path = Path(ws_info["path"])
        if not ws_path.is_dir():
            continue

        all_files.extend(collect_knowledge(ws_id, ws_info, ws_path))
        all_files.extend(collect_memory(ws_id, ws_info, ws_path))
        all_files.extend(collect_identity(ws_id, ws_info, ws_path))
        all_files.extend(collect_daily_notes(ws_id, ws_info, ws_path, daily_days))

    # Sort: category → agent_id → filename
    cat_order = {"knowledge": 0, "memory_lt": 1, "identity": 2, "daily": 3}
    all_files.sort(key=lambda f: (cat_order.get(f["category"], 9), f["agent_id"], f["filename"]))

    # Count by category
    by_cat: dict[str, int] = {}
    total_kb = 0.0
    for f in all_files:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
        total_kb += f["size_kb"]

    now = datetime.now(TZ_BR)
    output = {
        "generated_at": now.isoformat(),
        "totals": {
            "files": len(all_files),
            "total_size_kb": round(total_kb, 1),
            "by_category": by_cat,
        },
        "files": all_files,
    }

    # Check size limit
    raw = json.dumps(output, ensure_ascii=False, indent=2)
    if len(raw.encode("utf-8")) > MAX_JSON_BYTES:
        print(f"WARN: JSON is {len(raw.encode('utf-8'))//1024}KB, trimming daily notes to {DAILY_DAYS_FALLBACK} days", file=sys.stderr)
        # Rebuild with fewer daily notes
        all_files = [f for f in all_files if f["category"] != "daily"]
        for ws_id, ws_info in WORKSPACES.items():
            ws_path = Path(ws_info["path"])
            if ws_path.is_dir():
                all_files.extend(collect_daily_notes(ws_id, ws_info, ws_path, DAILY_DAYS_FALLBACK))
        all_files.sort(key=lambda f: (cat_order.get(f["category"], 9), f["agent_id"], f["filename"]))

        # Recalc totals
        by_cat = {}
        total_kb = 0.0
        for f in all_files:
            by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
            total_kb += f["size_kb"]
        output["totals"] = {"files": len(all_files), "total_size_kb": round(total_kb, 1), "by_category": by_cat}
        output["files"] = all_files
        raw = json.dumps(output, ensure_ascii=False, indent=2)

    # Second pass: truncate large knowledge files
    if len(raw.encode("utf-8")) > MAX_JSON_BYTES:
        print("WARN: Still too large, truncating knowledge files > 50KB", file=sys.stderr)
        max_chars = MAX_SINGLE_FILE_KB * 1024
        for f in output["files"]:
            if f["category"] == "knowledge" and len(f["content"]) > max_chars:
                f["content"] = f["content"][:max_chars] + "\n\n[... truncado ...]"
        raw = json.dumps(output, ensure_ascii=False, indent=2)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(raw, encoding="utf-8")
    size_kb = round(len(raw.encode("utf-8")) / 1024, 1)
    print(f"Generated knowledge_content.json: {len(all_files)} files, {size_kb} KB")


if __name__ == "__main__":
    main()
