from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class StatusInfo:
    text: str = ""
    source: str = "tool"  # "explicit" | "task" | "tool"
    updated_at: Optional[datetime] = None


@dataclass
class RecentAction:
    timestamp: datetime
    tool: str
    summary: str


@dataclass
class TaskItem:
    id: str
    subject: str
    status: str  # "pending" | "in_progress" | "completed"


@dataclass
class AgentStatus:
    id: str
    name: str
    registered_at: datetime
    last_heartbeat: datetime
    repo: str
    branch: str
    working_directory: str
    ticket_id: Optional[str]
    status: StatusInfo
    state: str = "working"  # "working" | "asking" | "done"
    recent_actions: list[RecentAction] = field(default_factory=list)
    tasks: list[TaskItem] = field(default_factory=list)
    status_history: list[StatusInfo] = field(default_factory=list)
    context_pct: Optional[float] = None
    cost_usd: Optional[float] = None
    git_added: int = 0
    git_removed: int = 0
    file_path: Optional[Path] = None

    @classmethod
    def from_file(cls, path: Path) -> Optional["AgentStatus"]:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

        try:
            status_data = data.get("status", {})
            status = StatusInfo(
                text=status_data.get("text", ""),
                source=status_data.get("source", "tool"),
                updated_at=_parse_dt(status_data.get("updatedAt")),
            )

            actions = []
            for a in data.get("recentActions", []):
                actions.append(
                    RecentAction(
                        timestamp=_parse_dt(a.get("timestamp", "")),
                        tool=a.get("tool", "Unknown"),
                        summary=a.get("summary", ""),
                    )
                )

            tasks = []
            for t in data.get("tasks", []):
                tasks.append(
                    TaskItem(
                        id=str(t.get("id", "")),
                        subject=t.get("subject", ""),
                        status=t.get("status", "pending"),
                    )
                )

            status_history = []
            for sh in data.get("statusHistory", []):
                status_history.append(
                    StatusInfo(
                        text=sh.get("text", ""),
                        source=sh.get("source", "tool"),
                        updated_at=_parse_dt(sh.get("updatedAt")),
                    )
                )

            return cls(
                id=data["id"],
                name=data.get("name", "Agent"),
                registered_at=_parse_dt(data["registeredAt"]),
                last_heartbeat=_parse_dt(data["lastHeartbeat"]),
                repo=data.get("repo", "unknown"),
                branch=data.get("branch", "unknown"),
                working_directory=data.get("workingDirectory", ""),
                ticket_id=data.get("ticketId"),
                status=status,
                state=data.get("state", "working"),
                recent_actions=actions,
                tasks=tasks,
                status_history=status_history,
                context_pct=data.get("contextWindow", {}).get("usedPct"),
                cost_usd=data.get("cost", {}).get("estimated"),
                git_added=data.get("gitDiff", {}).get("added", 0),
                git_removed=data.get("gitDiff", {}).get("removed", 0),
                file_path=path,
            )
        except (KeyError, TypeError):
            return None

    def is_stale(self, threshold_seconds: int = 300) -> bool:
        now = datetime.now(timezone.utc)
        delta = (now - self.last_heartbeat).total_seconds()
        return delta >= threshold_seconds

    @property
    def display_status(self) -> str:
        if self.status.text:
            return self.status.text
        if self.recent_actions:
            return self.recent_actions[0].summary
        return "(no recent activity)"

    @property
    def uptime_display(self) -> str:
        now = datetime.now(timezone.utc)
        delta = now - self.registered_at
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        remaining_mins = minutes % 60
        return f"{hours}h {remaining_mins}m"

    @property
    def heartbeat_ago(self) -> str:
        now = datetime.now(timezone.utc)
        delta = now - self.last_heartbeat
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        return f"{hours}h"


def _parse_dt(value: Optional[str], default_now: bool = True) -> datetime:
    if not value:
        if default_now:
            return datetime.now(timezone.utc)
        raise ValueError("Missing required timestamp")
    value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)
