from __future__ import annotations

import pytest
from app.domain.quality.review import apply_transition, can_transition


@pytest.mark.parametrize(
    "current,target",
    [
        ("open", "assigned"),
        ("assigned", "resolved"),
        ("assigned", "accepted_risk"),
    ],
)
def test_allowed_transitions(current, target):
    assert can_transition(current, target)
    assert apply_transition(current, target) == target


@pytest.mark.parametrize(
    "current,target",
    [
        ("open", "resolved"),  # must be assigned first
        ("open", "accepted_risk"),
        ("assigned", "assigned"),  # no self-loop
        ("resolved", "assigned"),  # terminal
        ("resolved", "resolved"),
        ("accepted_risk", "assigned"),
        ("open", "open"),
    ],
)
def test_illegal_transitions(current, target):
    assert not can_transition(current, target)
    with pytest.raises(ValueError):
        apply_transition(current, target)
