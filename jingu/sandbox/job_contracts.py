"""Runtime-owned sandbox job contract data loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jingu.runtime.errors import JinguRuntimeError


CONTRACTS_FILENAME = "job_contracts.json"


@dataclass(frozen=True)
class SandboxJobContracts:
    root_acceptance_criteria: str
    verification_target: str
    verification_acceptance_criteria: str
    repair_target: str
    repair_acceptance_criteria: str
    acceptance_repair_target: str
    acceptance_repair_acceptance_criteria: str
    acceptance_feedback_acceptance_criteria: str
    verification_feedback_target: str
    verification_feedback_acceptance_criteria: str
    parent_integration_target_prefix: str
    parent_integration_acceptance_criteria: str
    parent_integration_repair_target_prefix: str
    parent_integration_repair_acceptance_criteria: str
    parent_open_gap_target_prefix: str
    parent_open_gap_blocking_reason: str
    parent_open_gap_output_contract: str
    parent_open_gap_acceptance_criteria: str
    parent_followup_blocking_reason: str
    parent_followup_output_contract: str
    parent_followup_acceptance_criteria: str
    method_step_target_prefix: str
    method_step_acceptance_criteria: str
    child_package_repair_target_prefix: str


def load_sandbox_job_contracts(path: Path | None = None) -> SandboxJobContracts:
    source = path or Path(__file__).with_name(CONTRACTS_FILENAME)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise JinguRuntimeError(f"sandbox job contracts could not be read: {source}") from exc
    except json.JSONDecodeError as exc:
        raise JinguRuntimeError(f"sandbox job contracts are not valid JSON: {source}") from exc
    if not isinstance(payload, dict):
        raise JinguRuntimeError("sandbox job contracts must be a JSON object")
    values: dict[str, str] = {}
    for field in SandboxJobContracts.__dataclass_fields__:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise JinguRuntimeError(f"sandbox job contract field is required: {field}")
        values[field] = value
    return SandboxJobContracts(**values)
