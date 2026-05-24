"""First-stage job state machine."""

from __future__ import annotations

from jingu.runtime.constants import (
    STATE_ABANDONED,
    STATE_ACCEPTED,
    STATE_BLOCKED,
    STATE_DRAFT,
    STATE_READY,
    STATE_REJECTED,
    STATE_REVIEWING,
    STATE_RUNNING,
    STATE_WAITING_HUMAN,
)
from jingu.runtime.errors import InvalidTransitionError


ALL_STATES = {
    STATE_DRAFT,
    STATE_READY,
    STATE_RUNNING,
    STATE_BLOCKED,
    STATE_REVIEWING,
    STATE_ACCEPTED,
    STATE_REJECTED,
    STATE_WAITING_HUMAN,
    STATE_ABANDONED,
}

ALLOWED_TRANSITIONS = {
    STATE_DRAFT: {STATE_READY, STATE_BLOCKED, STATE_WAITING_HUMAN, STATE_ABANDONED},
    STATE_READY: {STATE_RUNNING, STATE_BLOCKED, STATE_WAITING_HUMAN, STATE_ABANDONED},
    STATE_RUNNING: {STATE_REVIEWING, STATE_BLOCKED, STATE_WAITING_HUMAN, STATE_ABANDONED},
    STATE_REVIEWING: {
        STATE_ACCEPTED,
        STATE_REJECTED,
        STATE_RUNNING,
        STATE_BLOCKED,
        STATE_WAITING_HUMAN,
    },
    STATE_REJECTED: {STATE_RUNNING, STATE_ABANDONED},
    STATE_BLOCKED: {STATE_READY, STATE_WAITING_HUMAN, STATE_ABANDONED},
    STATE_WAITING_HUMAN: {STATE_READY, STATE_BLOCKED, STATE_ABANDONED},
    STATE_ACCEPTED: set(),
    STATE_ABANDONED: set(),
}


def validate_transition(current_state: str, next_state: str) -> None:
    if current_state not in ALL_STATES:
        raise InvalidTransitionError(f"unknown current state: {current_state}")
    if next_state not in ALL_STATES:
        raise InvalidTransitionError(f"unknown next state: {next_state}")
    if next_state not in ALLOWED_TRANSITIONS[current_state]:
        raise InvalidTransitionError(f"cannot transition from {current_state} to {next_state}")
