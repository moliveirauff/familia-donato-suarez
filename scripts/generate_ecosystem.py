#!/usr/bin/env python3
"""
generate_ecosystem.py — Gera data/ecosystem.json
Varre workspaces do ecossistema S.P.I.N. e extrai metadados de cada agente.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# === CONFIG ===

REPO_DIR = Path(__file__).resolve().parent.parent
OUTPUT = REPO_DIR / "data" / "ecosystem.json"

TZ_BR = timezone(timedelta(hours=-3))

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

# Cron agent IDs that map to "main" workspace
CRON_MAIN_IDS = {"main", "spin"}


def get_knowledge_files(ws_path: Path) -> list[dict]:
    """List knowledge/k-*.md files with metadata."""
    kdir = ws_path / "knowledge"
    if not kdir.is_dir():
        return []
    files = []
    for f in sorted(kdir.glob("k-*.md")):
        if not f.is_file():
            continue
        stat = f.stat()
        content = ""
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

        # Extract title from first H1
        title = f.stem
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Extract tags from frontmatter
        tags = []
        m = re.search(r'^tags:\s*\[([^\]]*)\]', content, re.MULTILINE)
        if m:
            tags = [t.strip().strip("'\"") for t in m.group(1).split(",") if t.strip()]

        mtime = datetime.fromtimestamp(stat.st_mtime, tz=TZ_BR)
        files.append({
            "filename": f.name,
            "title": title,
            "tags": tags,
            "size_kb": round(stat.st_size / 1024, 1),
            "last_modified": mtime.isoformat(),
        })
    return files


def get_daily_notes(ws_path: Path) -> tuple[int, str | None]:
    """Count daily notes and find latest date from filename."""
    mdir = ws_path / "memory"
    if not mdir.is_dir():
        return 0, None
    md_files = list(mdir.glob("*.md"))
    if not md_files:
        return 0, None

    # Extract dates from filenames (YYYY-MM-DD.md or YYYY-MM.md)
    dates = []
    for f in md_files:
        stem = f.stem
        # Try YYYY-MM-DD
        m = re.match(r'^(\d{4}-\d{2}-\d{2})$', stem)
        if m:
            dates.append(m.group(1))
            continue
        # Try YYYY-MM (archived)
        m = re.match(r'^(\d{4}-\d{2})$', stem)
        if m:
            dates.append(m.group(1))

    latest = max(dates) if dates else None
    return len(md_files), latest


def get_memory_info(ws_path: Path) -> tuple[bool, float]:
    """Check MEMORY.md existence and size."""
    mem = ws_path / "MEMORY.md"
    if mem.is_file():
        return True, round(mem.stat().st_size / 1024, 1)
    return False, 0.0


def get_session_state_exists(ws_path: Path) -> bool:
    return (ws_path / "SESSION-STATE.md").is_file()


def get_cron_data() -> dict[str, dict]:
    """Run openclaw cron list --json and aggregate by agent."""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        jobs = data.get("jobs", [])
    except Exception as e:
        print(f"WARN: Could not get cron data: {e}", file=sys.stderr)
        return {}

    # Aggregate by workspace id
    agg: dict[str, dict] = {}
    for job in jobs:
        agent_id = job.get("agentId", "unknown")
        # Map spin/main to "main" workspace
        ws_id = "main" if agent_id in CRON_MAIN_IDS else agent_id

        if ws_id not in agg:
            agg[ws_id] = {"total": 0, "ok": 0, "error": 0, "idle": 0}

        agg[ws_id]["total"] += 1
        state = job.get("state", {})
        status = state.get("lastRunStatus") or state.get("lastStatus") or "idle"
        if status == "ok":
            agg[ws_id]["ok"] += 1
        elif status == "error":
            agg[ws_id]["error"] += 1
        else:
            agg[ws_id]["idle"] += 1

    return agg


def compute_health(cron: dict) -> str:
    if cron.get("error", 0) > 0:
        return "red"
    if cron.get("idle", 0) > 0 and cron.get("ok", 0) == 0:
        return "yellow"
    return "green"


def main():
    cron_data = get_cron_data()

    agents = []
    totals = {
        "agents": 0,
        "knowledge_files": 0,
        "daily_notes": 0,
        "cron_jobs": 0,
        "cron_healthy": 0,
        "cron_errors": 0,
    }

    for ws_id, ws_info in WORKSPACES.items():
        ws_path = Path(ws_info["path"])
        if not ws_path.is_dir():
            continue

        k_files = get_knowledge_files(ws_path)
        daily_count, latest_daily = get_daily_notes(ws_path)
        mem_exists, mem_size = get_memory_info(ws_path)
        ss_exists = get_session_state_exists(ws_path)
        cron = cron_data.get(ws_id, {"total": 0, "ok": 0, "error": 0, "idle": 0})

        agent = {
            "id": ws_id,
            "name": ws_info["name"],
            "emoji": ws_info["emoji"],
            "knowledge_count": len(k_files),
            "daily_notes_count": daily_count,
            "latest_daily": latest_daily,
            "memory_exists": mem_exists,
            "memory_size_kb": mem_size,
            "session_state_exists": ss_exists,
            "cron_total": cron["total"],
            "cron_ok": cron["ok"],
            "cron_error": cron["error"],
            "cron_idle": cron["idle"],
            "health": compute_health(cron),
        }
        agents.append(agent)

        totals["agents"] += 1
        totals["knowledge_files"] += len(k_files)
        totals["daily_notes"] += daily_count
        totals["cron_jobs"] += cron["total"]
        totals["cron_healthy"] += cron["ok"]
        totals["cron_errors"] += cron["error"]

    # Sort by knowledge_count descending
    agents.sort(key=lambda a: a["knowledge_count"], reverse=True)

    now = datetime.now(TZ_BR)
    output = {
        "generated_at": now.isoformat(),
        "totals": totals,
        "agents": agents,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated ecosystem.json: {totals['agents']} agents, {totals['knowledge_files']} knowledge files")


if __name__ == "__main__":
    main()
