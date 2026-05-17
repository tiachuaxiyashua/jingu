## ADDED Requirements

### Requirement: Human-readable diagnostic log
The AI sandbox SHALL create a human-readable diagnostic log for each run in addition to the machine-readable JSONL event log.

#### Scenario: Readable log is created
- **WHEN** an AI sandbox run writes flow events
- **THEN** the log directory contains a Markdown readable log for the same run.

#### Scenario: Readable log preserves Chinese text
- **WHEN** an event contains Chinese input, method content, AI output, or review text
- **THEN** the readable log preserves that text without mojibake when read as UTF-8 with BOM.

### Requirement: Latest readable log pointer
The AI sandbox SHALL write a latest-readable-log pointer next to the existing latest JSONL log pointer.

#### Scenario: Pointers are written
- **WHEN** a sandbox session starts
- **THEN** the log directory contains pointers to both the JSONL log and the readable Markdown log.

### Requirement: Readable lifecycle path reporting
The AI sandbox SHALL include both machine and readable log paths in lifecycle events.

#### Scenario: Startup reports both logs
- **WHEN** the sandbox emits the startup lifecycle event
- **THEN** the event payload contains the JSONL log path and the readable log path.

### Requirement: Readable monitor projection
The monitor CLI SHALL render long event fields as multiline blocks while preserving all event data.

#### Scenario: Monitor formats long fields
- **WHEN** an event contains multiline or long text fields
- **THEN** the monitor output places those fields in readable labeled blocks instead of a single long inline line.

### Requirement: UTF-8 launcher output
The one-click PowerShell launcher SHALL configure spawned chat and monitor processes for UTF-8 output.

#### Scenario: Launcher includes UTF-8 setup
- **WHEN** the launcher starts or prints a dry run
- **THEN** the chat and monitor commands include UTF-8 output setup before running the Python CLI.
