"""SQLite schema for the minimal runtime."""

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    parent_job_id TEXT,
    root_job_id TEXT NOT NULL,
    state TEXT NOT NULL,
    original_wish_appearance_id TEXT,
    target TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '',
    responsibility_scope TEXT NOT NULL DEFAULT 'self',
    completion_scope TEXT NOT NULL DEFAULT 'self',
    acceptance_criteria TEXT NOT NULL DEFAULT '',
    required_context_gaps TEXT NOT NULL DEFAULT '[]',
    candidate_appearance_id TEXT,
    evidence_appearance_id TEXT,
    result_appearance_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(parent_job_id) REFERENCES jobs(job_id),
    FOREIGN KEY(root_job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS appearances (
    appearance_id TEXT PRIMARY KEY,
    appearance_type TEXT NOT NULL,
    state TEXT NOT NULL,
    location TEXT,
    structure_version TEXT NOT NULL,
    content_version INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    source_job_id TEXT,
    upstream_refs TEXT NOT NULL DEFAULT '[]',
    applicable_scope TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(source_job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS events (
    event_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    job_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL,
    previous_checksum TEXT NOT NULL DEFAULT '',
    checksum TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
);

CREATE INDEX IF NOT EXISTS idx_events_job_sequence ON events(job_id, event_sequence);
CREATE INDEX IF NOT EXISTS idx_appearances_source_job ON appearances(source_job_id);
CREATE INDEX IF NOT EXISTS idx_appearances_type_state ON appearances(appearance_type, state);
"""
