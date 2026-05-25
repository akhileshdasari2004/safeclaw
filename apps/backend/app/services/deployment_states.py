"""Durable provisioning state machine constants."""

from __future__ import annotations

# Canonical provision states (persisted on deployments.provision_state)
QUEUED = "QUEUED"
CREATING_SERVER = "CREATING_SERVER"
WAITING_FOR_SSH = "WAITING_FOR_SSH"
HARDENING = "HARDENING"
INSTALLING_DOCKER = "INSTALLING_DOCKER"
INSTALLING_OPENCLAW = "INSTALLING_OPENCLAW"
VERIFYING = "VERIFYING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
ROLLING_BACK = "ROLLING_BACK"
ROLLED_BACK = "ROLLED_BACK"

ORDERED_STATES: tuple[str, ...] = (
    QUEUED,
    CREATING_SERVER,
    WAITING_FOR_SSH,
    HARDENING,
    INSTALLING_DOCKER,
    INSTALLING_OPENCLAW,
    VERIFYING,
    COMPLETED,
)

TERMINAL_STATES = frozenset({COMPLETED, FAILED, ROLLED_BACK})
RESUMABLE_STATES = frozenset({
    QUEUED,
    CREATING_SERVER,
    WAITING_FOR_SSH,
    HARDENING,
    INSTALLING_DOCKER,
    INSTALLING_OPENCLAW,
    VERIFYING,
    FAILED,
})

# Legacy `status` column values for API/frontend compatibility
LEGACY_STATUS_MAP: dict[str, str] = {
    QUEUED: "queued",
    CREATING_SERVER: "provisioning",
    WAITING_FOR_SSH: "hardening",
    HARDENING: "hardening",
    INSTALLING_DOCKER: "installing",
    INSTALLING_OPENCLAW: "installing",
    VERIFYING: "verifying",
    COMPLETED: "completed",
    FAILED: "failed",
    ROLLING_BACK: "failed",
    ROLLED_BACK: "failed",
}


def state_index(state: str | None) -> int:
    if not state:
        return -1
    try:
        return ORDERED_STATES.index(state)
    except ValueError:
        return -1


def has_passed(current: str | None, target: str) -> bool:
    """True when `current` is strictly past `target` (target step already completed)."""
    return state_index(current) > state_index(target)


def legacy_status(provision_state: str) -> str:
    return LEGACY_STATUS_MAP.get(provision_state, "queued")
