"""Repository operations for the minimal runtime."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from jingu.runtime.constants import STRUCTURE_VERSION
from jingu.runtime.db import connect, initialize_database
from jingu.runtime.errors import NotFoundError
from jingu.runtime.paths import RuntimePaths


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def decode_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    return json.loads(value)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


class RuntimeRepository:
    def __init__(self, workspace: Path | str) -> None:
        self.paths = RuntimePaths.resolve(workspace)

    def initialize(self) -> None:
        initialize_database(self.paths)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.initialize()
        connection = connect(self.paths.database_path)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_job(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        root_job_id: str,
        target: str,
        state: str,
        parent_job_id: str | None = None,
        original_wish_appearance_id: str | None = None,
        scope: str = "",
        responsibility_scope: str = "self",
        completion_scope: str = "self",
        acceptance_criteria: str = "",
        required_context_gaps: list[str] | None = None,
    ) -> dict[str, Any]:
        timestamp = now_iso()
        connection.execute(
            """
            INSERT INTO jobs (
                job_id, parent_job_id, root_job_id, state, original_wish_appearance_id,
                target, scope, responsibility_scope, completion_scope, acceptance_criteria,
                required_context_gaps, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                parent_job_id,
                root_job_id,
                state,
                original_wish_appearance_id,
                target,
                scope,
                responsibility_scope,
                completion_scope,
                acceptance_criteria,
                encode_json(required_context_gaps or []),
                timestamp,
                timestamp,
            ),
        )
        return self.require_job(connection, job_id)

    def update_job(self, connection: sqlite3.Connection, job_id: str, **fields: Any) -> dict[str, Any]:
        if not fields:
            return self.require_job(connection, job_id)

        fields["updated_at"] = now_iso()
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values())
        values.append(job_id)
        connection.execute(f"UPDATE jobs SET {assignments} WHERE job_id = ?", values)
        return self.require_job(connection, job_id)

    def get_job(self, connection: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return row_to_dict(row)

    def list_jobs_by_root(
        self, connection: sqlite3.Connection, root_job_id: str
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            "SELECT * FROM jobs WHERE root_job_id = ? ORDER BY created_at ASC, job_id ASC",
            (root_job_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_child_jobs(
        self, connection: sqlite3.Connection, parent_job_id: str
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            "SELECT * FROM jobs WHERE parent_job_id = ? ORDER BY created_at ASC, job_id ASC",
            (parent_job_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def require_job(self, connection: sqlite3.Connection, job_id: str) -> dict[str, Any]:
        job = self.get_job(connection, job_id)
        if job is None:
            raise NotFoundError(f"job not found: {job_id}")
        return job

    def create_appearance(
        self,
        connection: sqlite3.Connection,
        *,
        appearance_id: str,
        appearance_type: str,
        state: str,
        checksum: str,
        location: str | None = None,
        summary: str = "",
        source_job_id: str | None = None,
        upstream_refs: list[str] | None = None,
        applicable_scope: str = "",
        metadata: dict[str, Any] | None = None,
        structure_version: str = STRUCTURE_VERSION,
        content_version: int = 1,
    ) -> dict[str, Any]:
        timestamp = now_iso()
        connection.execute(
            """
            INSERT INTO appearances (
                appearance_id, appearance_type, state, location, structure_version,
                content_version, checksum, summary, source_job_id, upstream_refs,
                applicable_scope, metadata, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appearance_id,
                appearance_type,
                state,
                location,
                structure_version,
                content_version,
                checksum,
                summary,
                source_job_id,
                encode_json(upstream_refs or []),
                applicable_scope,
                encode_json(metadata or {}),
                timestamp,
                timestamp,
            ),
        )
        return self.require_appearance(connection, appearance_id)

    def update_appearance(
        self, connection: sqlite3.Connection, appearance_id: str, **fields: Any
    ) -> dict[str, Any]:
        if not fields:
            return self.require_appearance(connection, appearance_id)

        fields["updated_at"] = now_iso()
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values())
        values.append(appearance_id)
        connection.execute(f"UPDATE appearances SET {assignments} WHERE appearance_id = ?", values)
        return self.require_appearance(connection, appearance_id)

    def get_appearance(self, connection: sqlite3.Connection, appearance_id: str) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT * FROM appearances WHERE appearance_id = ?", (appearance_id,)
        ).fetchone()
        return row_to_dict(row)

    def require_appearance(self, connection: sqlite3.Connection, appearance_id: str) -> dict[str, Any]:
        appearance = self.get_appearance(connection, appearance_id)
        if appearance is None:
            raise NotFoundError(f"appearance not found: {appearance_id}")
        return appearance

    def append_event(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        event_type: str,
        payload: dict[str, Any],
        actor_id: str = "",
    ) -> dict[str, Any]:
        self.require_job(connection, job_id)
        event_id = new_id("event")
        timestamp = now_iso()
        previous_checksum = self.latest_event_checksum(connection)
        payload_json = encode_json(payload)
        checksum = self.event_checksum(
            previous_checksum=previous_checksum,
            event_id=event_id,
            job_id=job_id,
            event_type=event_type,
            actor_id=actor_id,
            payload=payload_json,
            created_at=timestamp,
        )
        connection.execute(
            """
            INSERT INTO events (
                event_id, job_id, event_type, actor_id, payload,
                previous_checksum, checksum, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, job_id, event_type, actor_id, payload_json, previous_checksum, checksum, timestamp),
        )
        return self.require_event(connection, event_id)

    def latest_event_checksum(self, connection: sqlite3.Connection) -> str:
        row = connection.execute(
            "SELECT checksum FROM events ORDER BY event_sequence DESC LIMIT 1"
        ).fetchone()
        return "" if row is None else str(row["checksum"])

    def require_event(self, connection: sqlite3.Connection, event_id: str) -> dict[str, Any]:
        row = connection.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        event = row_to_dict(row)
        if event is None:
            raise NotFoundError(f"event not found: {event_id}")
        return event

    def list_events(self, connection: sqlite3.Connection, job_id: str) -> list[dict[str, Any]]:
        self.require_job(connection, job_id)
        rows = connection.execute(
            "SELECT * FROM events WHERE job_id = ? ORDER BY event_sequence ASC", (job_id,)
        ).fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event["payload"] = decode_json(event["payload"], {})
        return events

    @staticmethod
    def event_checksum(
        *,
        previous_checksum: str,
        event_id: str,
        job_id: str,
        event_type: str,
        actor_id: str,
        payload: str,
        created_at: str,
    ) -> str:
        content = encode_json(
            {
                "previous_checksum": previous_checksum,
                "event_id": event_id,
                "job_id": job_id,
                "event_type": event_type,
                "actor_id": actor_id,
                "payload": payload,
                "created_at": created_at,
            }
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
