"""Review-workflow state machine (deterministic, no ML).

Transitions: ``open -> assigned -> {resolved, accepted_risk}``. Terminal states
have no outgoing transitions. Enforced in one place so the API cannot silently
perform an illegal transition.
"""

from __future__ import annotations

REVIEW_STATES = ("open", "assigned", "resolved", "accepted_risk")

_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"assigned"}),
    "assigned": frozenset({"resolved", "accepted_risk"}),
    "resolved": frozenset(),
    "accepted_risk": frozenset(),
}


def can_transition(current: str, target: str) -> bool:
    return target in _TRANSITIONS.get(current, frozenset())


def apply_transition(current: str, target: str) -> str:
    """Return ``target`` if it is a legal transition, else raise ValueError."""
    if not can_transition(current, target):
        raise ValueError(f"Illegal review transition: {current!r} -> {target!r}")
    return target
