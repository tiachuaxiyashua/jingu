## ADDED Requirements

### Requirement: Chinese readable log projection
The sandbox readable Markdown log SHALL use Chinese-first titles, event names, messages, and field labels.

#### Scenario: Chinese headings and labels
- **WHEN** a sandbox readable log is generated
- **THEN** the log title, lifecycle labels, event headings, and known field labels are written in Chinese while retaining raw identifiers in parentheses.

### Requirement: Preserve correct Chinese content
The sandbox readable Markdown log SHALL preserve Chinese input, method content, AI output, and review content when the event stream receives correct Unicode.

#### Scenario: Chinese content remains readable
- **WHEN** a sandbox event contains correct Chinese text
- **THEN** the readable log contains that Chinese text without replacing it with question marks.

### Requirement: Encoding damage warning
The sandbox readable Markdown log SHALL warn when a field already contains suspicious consecutive question marks.

#### Scenario: Suspicious question marks are flagged
- **WHEN** a field value contains a suspicious run of question marks
- **THEN** the readable log shows a Chinese encoding warning near that field.

### Requirement: UTF-8 input and output setup
The one-click PowerShell launcher SHALL configure both input and output UTF-8 settings for spawned chat and monitor processes.

#### Scenario: Launcher configures UTF-8 input output
- **WHEN** the launcher prints a dry run or starts windows
- **THEN** the command setup includes console input encoding, output encoding, `PYTHONUTF8`, and `PYTHONIOENCODING`.
