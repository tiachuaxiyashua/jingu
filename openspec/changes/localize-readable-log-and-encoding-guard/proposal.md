## Why

The current readable sandbox log is still written with English titles and field labels, so it is not a true human-facing `镜` for the Chinese-speaking project owner. The log can also contain question marks when text was already damaged before entering the event stream, and the readable projection should make that damage visible instead of presenting it as normal content.

## What Changes

- Render the Markdown readable log in Chinese by default.
- Translate known event names, event messages, and data field labels while preserving raw event and field identifiers.
- Add a clear Chinese warning when a field contains suspicious consecutive question marks that indicate likely encoding damage before logging.
- Strengthen one-click PowerShell launcher encoding setup with input encoding and `PYTHONIOENCODING`.
- Update monitor output to use the same Chinese readable rendering.
- Add tests and a manual validation sample proving Chinese readable headings, Chinese content preservation, and question-mark damage warnings.

## Capabilities

### New Capabilities

- `localized-readable-logs`: Chinese human-readable sandbox diagnostics with visible encoding-damage warnings.

### Modified Capabilities

None.

## Impact

- Updates readable log rendering in `jingu.sandbox.flow`.
- Updates PowerShell launcher and monitor scripts for stronger UTF-8 input/output setup.
- Extends AI sandbox tests for Chinese log labels and suspicious question-mark detection.
