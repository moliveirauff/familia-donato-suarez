#!/usr/bin/env python3
"""
generate_cron.py — Gera data/cron_dashboard.json
Extrai cron jobs do OpenClaw e gera JSON com status e schedule humanizado.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# === CONFIG ===

REPO_DIR = Path(__file__).resolve().parent.parent
OUTPUT = REPO_DIR / "data" / "cron_dashboard.json"

TZ_BR = timezone(timedelta(hours=-3))

# Map spin → main for aggregation
CRON_ALIAS = {"spin": "main"}

WORKSPACES = {
    "main":    {"emoji": "🤖", "name": "S.P.I.N."},
    "spin":    {"emoji": "🤖", "name": "S.P.I.N."},
    "argos":   {"emoji": "🏠", "name": "Argos"},
    "casa":    {"emoji": "🏡", "name": "Casa"},
    "dev":     {"emoji": "💻", "name": "Dev"},
    "fin":     {"emoji": "💰", "name": "Fin"},
    "invest":  {"emoji": "📈", "name": "Invest"},
    "kmbot":   {"emoji": "🧠", "name": "KMBot"},
    "leadbot": {"emoji": "🎯", "name": "LeadBot"},
    "matheus": {"emoji": "🍼", "name": "Matheus"},
    "medbot":  {"emoji": "🩺", "name": "MedBot"},
    "rfbot":   {"emoji": "📱", "name": "RFBot"},
    "specbot": {"emoji": "📐", "name": "SpecBot"},
    "subsea":  {"emoji": "🌊", "name": "Subsea"},
}

DAYS_PT = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}


def humanize_cron(expr: str) -> str:
    """Convert cron expression to PT-BR human-readable text."""
    parts = expr.strip().split()
    if len(parts) < 5:
        return expr

    minute, hour, dom, month, dow = parts[:5]
    time_str = f"{int(hour):02d}:{int(minute):02d}" if hour != "*" and minute != "*" else ""

    # Every minute
    if all(p == "*" for p in [minute, hour, dom, month, dow]):
        return "Contínuo"

    # Daily: M H * * *
    if dom == "*" and month == "*" and dow == "*" and hour != "*":
        return f"Diário {time_str}"

    # Weekday range: M H * * N-N
    if dom == "*" and month == "*" and "-" in dow and hour != "*":
        start, end = dow.split("-")
        start_name = DAYS_PT.get(int(start), start)
        end_name = DAYS_PT.get(int(end), end)
        return f"{start_name}-{end_name} {time_str}"

    # Multiple weekdays: M H * * N,N
    if dom == "*" and month == "*" and "," in dow and hour != "*":
        day_names = []
        for d in dow.split(","):
            day_names.append(DAYS_PT.get(int(d.strip()), d.strip()))
        return f"{'/'.join(day_names)} {time_str}"

    # Single weekday: M H * * N
    if dom == "*" and month == "*" and dow.isdigit() and hour != "*":
        day_name = DAYS_PT.get(int(dow), dow)
        return f"{day_name} {time_str}"

    # Day of month: M H D * *
    if dom != "*" and month == "*" and dow == "*" and hour != "*":
        return f"Dia {dom}, {time_str}"

    # Every N days: M H */N * *
    if dom.startswith("*/") and month == "*" and dow == "*" and hour != "*":
        n = dom[2:]
        return f"A cada {n} dias, {time_str}"

    # Interval: every/N * * * *
    if minute.startswith("*/"):
        n = minute[2:]
        return f"A cada {n} min"

    if hour.startswith("*/"):
        n = hour[2:]
        return f"A cada {n}h"

    # Fallback
    return f"cron {expr}"


def relative_time(ms_timestamp: int | None) -> str:
    """Convert ms timestamp to relative time string."""
    if not ms_timestamp:
        return "-"
    now_ms = int(datetime.now(TZ_BR).timestamp() * 1000)
    diff_ms = now_ms - ms_timestamp

    if diff_ms < 0:
        # Future
        diff_ms = abs(diff_ms)
        if diff_ms < 60_000:
            return "in <1m"
        elif diff_ms < 3_600_000:
            return f"in {diff_ms // 60_000}m"
        elif diff_ms < 86_400_000:
            return f"in {diff_ms // 3_600_000}h"
        else:
            return f"in {diff_ms // 86_400_000}d"
    else:
        if diff_ms < 60_000:
            return "<1m ago"
        elif diff_ms < 3_600_000:
            return f"{diff_ms // 60_000}m ago"
        elif diff_ms < 86_400_000:
            return f"{diff_ms // 3_600_000}h ago"
        else:
            return f"{diff_ms // 86_400_000}d ago"


def get_status(state: dict) -> str:
    """Extract status from job state."""
    s = state.get("lastRunStatus") or state.get("lastStatus") or ""
    if s == "ok":
        return "ok"
    elif s == "error":
        return "error"
    else:
        return "idle"


def main():
    # Get cron data
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
        jobs_raw = data.get("jobs", [])
    except Exception as e:
        print(f"ERROR: Could not get cron data: {e}", file=sys.stderr)
        sys.exit(1)

    # Process jobs
    jobs = []
    agent_agg: dict[str, dict] = {}

    for job in jobs_raw:
        agent_id = job.get("agentId", "unknown")
        ws = WORKSPACES.get(agent_id, {"emoji": "❓", "name": agent_id})
        state = job.get("state", {})
        status = get_status(state)

        # Parse schedule
        schedule = job.get("schedule", {})
        if schedule.get("kind") == "cron":
            schedule_human = humanize_cron(schedule.get("expr", ""))
        elif schedule.get("kind") == "every":
            every_ms = schedule.get("everyMs", 0)
            if every_ms >= 86_400_000:
                schedule_human = f"A cada {every_ms // 86_400_000}d"
            elif every_ms >= 3_600_000:
                schedule_human = f"A cada {every_ms // 3_600_000}h"
            else:
                schedule_human = f"A cada {every_ms // 60_000}min"
        else:
            schedule_human = str(schedule)

        jobs.append({
            "id": job.get("id", ""),
            "name": job.get("name", "(sem nome)"),
            "agent_id": agent_id,
            "agent_name": ws["name"],
            "agent_emoji": ws["emoji"],
            "schedule_human": schedule_human,
            "status": status,
            "last_run": relative_time(state.get("lastRunAtMs")),
            "next_run": relative_time(state.get("nextRunAtMs")),
        })

        # Aggregate per agent (consolidate spin → main)
        agg_id = CRON_ALIAS.get(agent_id, agent_id)
        if agg_id not in agent_agg:
            agg_ws = WORKSPACES.get(agg_id, ws)
            agent_agg[agg_id] = {
                "id": agg_id,
                "name": agg_ws["name"],
                "emoji": agg_ws["emoji"],
                "total": 0, "ok": 0, "error": 0, "idle": 0,
            }
        agent_agg[agg_id]["total"] += 1
        agent_agg[agg_id][status] += 1

    # Compute health per agent
    agents_list = []
    for a in agent_agg.values():
        if a["error"] > 0:
            a["health"] = "red"
        elif a["idle"] > 0 and a["ok"] == 0:
            a["health"] = "yellow"
        else:
            a["health"] = "green"
        agents_list.append(a)

    # Sort agents: error desc, total desc
    agents_list.sort(key=lambda a: (-a["error"], -a["total"]))

    # Sort jobs: within each agent, errors first
    status_order = {"error": 0, "idle": 1, "ok": 2}
    jobs.sort(key=lambda j: (j["agent_id"], status_order.get(j["status"], 9), j["name"]))

    # Summary
    summary = {
        "total": len(jobs),
        "ok": sum(1 for j in jobs if j["status"] == "ok"),
        "error": sum(1 for j in jobs if j["status"] == "error"),
        "idle": sum(1 for j in jobs if j["status"] == "idle"),
    }

    now = datetime.now(TZ_BR)
    output = {
        "generated_at": now.isoformat(),
        "summary": summary,
        "agents": agents_list,
        "jobs": jobs,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated cron_dashboard.json: {summary['total']} jobs ({summary['ok']} ok, {summary['error']} error, {summary['idle']} idle)")


if __name__ == "__main__":
    main()
