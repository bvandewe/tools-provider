"""Unit tests for OrchestratorState enum.

Tests cover:
- State transitions validation
- Terminal state detection
- Input acceptance states
- Widget response acceptance states
"""

import pytest

from application.orchestrator.context import OrchestratorState


class TestOrchestratorStateValues:
    """Test OrchestratorState enum values."""

    def test_all_states_defined(self):
        """Verify all expected states are defined."""
        expected_states = {
            "INITIALIZING",
            "READY",
            "PRESENTING",
            "PROCESSING",
            "SUSPENDED",
            "PAUSED",
            "COMPLETED",
            "ERROR",
        }
        actual_states = {state.name for state in OrchestratorState}
        assert actual_states == expected_states

    def test_states_are_string_enum(self):
        """States should be usable as strings."""
        assert OrchestratorState.READY == "ready"
        assert OrchestratorState.INITIALIZING == "initializing"
        assert str(OrchestratorState.ERROR) == "OrchestratorState.ERROR"

    def test_state_value_lowercase(self):
        """State values should be lowercase strings."""
        for state in OrchestratorState:
            assert state.value == state.name.lower()


class TestOrchestratorStateTransitions:
    """Test state transition validation."""

    @pytest.mark.parametrize(
        "from_state,to_state,expected",
        [
            # INITIALIZING transitions
            (OrchestratorState.INITIALIZING, OrchestratorState.READY, True),
            (OrchestratorState.INITIALIZING, OrchestratorState.PRESENTING, True),
            (OrchestratorState.INITIALIZING, OrchestratorState.ERROR, True),
            (OrchestratorState.INITIALIZING, OrchestratorState.PROCESSING, False),
            (OrchestratorState.INITIALIZING, OrchestratorState.SUSPENDED, False),
            # READY transitions
            (OrchestratorState.READY, OrchestratorState.PROCESSING, True),
            (OrchestratorState.READY, OrchestratorState.PAUSED, True),
            (OrchestratorState.READY, OrchestratorState.COMPLETED, True),
            (OrchestratorState.READY, OrchestratorState.ERROR, True),
            (OrchestratorState.READY, OrchestratorState.PRESENTING, False),
            (OrchestratorState.READY, OrchestratorState.INITIALIZING, False),
            # PRESENTING transitions
            (OrchestratorState.PRESENTING, OrchestratorState.SUSPENDED, True),
            (OrchestratorState.PRESENTING, OrchestratorState.READY, True),
            (OrchestratorState.PRESENTING, OrchestratorState.PAUSED, True),
            (OrchestratorState.PRESENTING, OrchestratorState.COMPLETED, True),
            (OrchestratorState.PRESENTING, OrchestratorState.ERROR, True),
            (OrchestratorState.PRESENTING, OrchestratorState.PROCESSING, False),
            # PROCESSING transitions
            (OrchestratorState.PROCESSING, OrchestratorState.READY, True),
            (OrchestratorState.PROCESSING, OrchestratorState.SUSPENDED, True),
            (OrchestratorState.PROCESSING, OrchestratorState.PAUSED, True),
            (OrchestratorState.PROCESSING, OrchestratorState.COMPLETED, True),
            (OrchestratorState.PROCESSING, OrchestratorState.ERROR, True),
            (OrchestratorState.PROCESSING, OrchestratorState.PRESENTING, False),
            # SUSPENDED transitions
            (OrchestratorState.SUSPENDED, OrchestratorState.PRESENTING, True),
            (OrchestratorState.SUSPENDED, OrchestratorState.READY, True),
            (OrchestratorState.SUSPENDED, OrchestratorState.PAUSED, True),
            (OrchestratorState.SUSPENDED, OrchestratorState.COMPLETED, True),
            (OrchestratorState.SUSPENDED, OrchestratorState.ERROR, True),
            (OrchestratorState.SUSPENDED, OrchestratorState.PROCESSING, False),
            # PAUSED transitions
            (OrchestratorState.PAUSED, OrchestratorState.READY, True),
            (OrchestratorState.PAUSED, OrchestratorState.PRESENTING, True),
            (OrchestratorState.PAUSED, OrchestratorState.COMPLETED, True),
            (OrchestratorState.PAUSED, OrchestratorState.ERROR, True),
            (OrchestratorState.PAUSED, OrchestratorState.PROCESSING, False),
            (OrchestratorState.PAUSED, OrchestratorState.SUSPENDED, False),
            # Terminal states - no transitions allowed
            (OrchestratorState.COMPLETED, OrchestratorState.READY, False),
            (OrchestratorState.COMPLETED, OrchestratorState.ERROR, False),
            (OrchestratorState.COMPLETED, OrchestratorState.INITIALIZING, False),
            (OrchestratorState.ERROR, OrchestratorState.READY, False),
            (OrchestratorState.ERROR, OrchestratorState.COMPLETED, False),
            (OrchestratorState.ERROR, OrchestratorState.INITIALIZING, False),
        ],
    )
    def test_can_transition_to(self, from_state, to_state, expected):
        """Test that state transitions are correctly validated."""
        assert from_state.can_transition_to(to_state) == expected


class TestOrchestratorStatePredicates:
    """Test state predicate methods."""

    @pytest.mark.parametrize(
        "state,expected",
        [
            (OrchestratorState.COMPLETED, True),
            (OrchestratorState.ERROR, True),
            (OrchestratorState.INITIALIZING, False),
            (OrchestratorState.READY, False),
            (OrchestratorState.PRESENTING, False),
            (OrchestratorState.PROCESSING, False),
            (OrchestratorState.SUSPENDED, False),
            (OrchestratorState.PAUSED, False),
        ],
    )
    def test_is_terminal(self, state, expected):
        """Test terminal state detection."""
        assert state.is_terminal() == expected

    @pytest.mark.parametrize(
        "state,expected",
        [
            (OrchestratorState.READY, True),
            (OrchestratorState.PROCESSING, True),
            (OrchestratorState.INITIALIZING, False),
            (OrchestratorState.PRESENTING, False),
            (OrchestratorState.SUSPENDED, False),
            (OrchestratorState.PAUSED, False),
            (OrchestratorState.COMPLETED, False),
            (OrchestratorState.ERROR, False),
        ],
    )
    def test_allows_user_input(self, state, expected):
        """Test which states allow user input."""
        assert state.allows_user_input() == expected

    @pytest.mark.parametrize(
        "state,expected",
        [
            (OrchestratorState.SUSPENDED, True),
            (OrchestratorState.INITIALIZING, False),
            (OrchestratorState.READY, False),
            (OrchestratorState.PRESENTING, False),
            (OrchestratorState.PROCESSING, False),
            (OrchestratorState.PAUSED, False),
            (OrchestratorState.COMPLETED, False),
            (OrchestratorState.ERROR, False),
        ],
    )
    def test_allows_widget_response(self, state, expected):
        """Test which states allow widget responses."""
        assert state.allows_widget_response() == expected
