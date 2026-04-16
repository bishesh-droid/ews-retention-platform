"""
Simple in-memory task tracker for background jobs.

No Redis required — tasks are stored in a module-level dict.
This is suitable for single-instance deployments and testing.
For production with multiple workers, upgrade to Redis or a proper task queue.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional

# Module-level task store: task_id -> task_dict
_tasks: Dict[str, dict] = {}


def create_task(label: str) -> str:
    """
    Create a new task entry with pending status.

    Args:
        label: Human-readable task description

    Returns:
        8-character task ID
    """
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "id": task_id,
        "label": label,
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "error": None,
    }
    return task_id


def update_task(task_id: str, status: str, error: Optional[str] = None):
    """
    Update task status and timestamps.

    Args:
        task_id: The task ID to update
        status: One of "pending", "running", "success", "failed"
        error: Error message if status is "failed"
    """
    if task_id not in _tasks:
        return

    _tasks[task_id]["status"] = status

    if status == "running":
        _tasks[task_id]["started_at"] = datetime.utcnow().isoformat()
    elif status in ("success", "failed"):
        _tasks[task_id]["finished_at"] = datetime.utcnow().isoformat()

    if error:
        _tasks[task_id]["error"] = error


def get_task(task_id: str) -> Optional[dict]:
    """
    Get task status by ID.

    Args:
        task_id: The task ID to look up

    Returns:
        Task dict or None if not found
    """
    return _tasks.get(task_id)


def list_tasks(limit: int = 100) -> list:
    """
    List recent tasks (most recent first).

    Args:
        limit: Maximum number of tasks to return

    Returns:
        List of task dicts
    """
    # Sort by started_at (or created implicitly by dict order as fallback)
    tasks = list(_tasks.values())
    tasks.sort(
        key=lambda t: t.get("started_at") or t.get("finished_at") or "", reverse=True
    )
    return tasks[:limit]
