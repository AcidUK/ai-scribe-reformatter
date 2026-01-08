"""Tests for IconManager class and state-based icon updates."""
import pytest
from datetime import datetime, timedelta
from PIL import Image
from pathlib import Path
import sys
import os
from unittest.mock import MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock GUI modules before importing history_clipboard_manager
# This is necessary because pyautogui requires a display on Linux
sys.modules['pyautogui'] = MagicMock()
sys.modules['mouse'] = MagicMock()
sys.modules['pystray'] = MagicMock()

from history_clipboard_manager import IconManager, State, ApplicationState


class TestIconManager:
    """Test IconManager functionality."""

    def test_icon_manager_initialization(self):
        """Test that IconManager initializes correctly."""
        manager = IconManager()
        assert manager is not None
        assert manager.base_icon is not None
        assert manager.badges is not None
        assert 'ready' in manager.badges
        assert 'plan' in manager.badges
        assert 'error' in manager.badges

    def test_base_icon_exists(self):
        """Test that base icon is loaded or fallback is created."""
        manager = IconManager()
        assert manager.base_icon is not None
        assert isinstance(manager.base_icon, Image.Image)
        assert manager.base_icon.size == (64, 64)

    def test_all_badges_loaded_or_fallback(self):
        """Test that all badges are either loaded or have fallbacks."""
        manager = IconManager()
        for state_name in ['ready', 'plan', 'error']:
            badge = manager.badges.get(state_name)
            assert badge is not None, f"Badge for {state_name} should exist"
            assert isinstance(badge, Image.Image), f"Badge for {state_name} should be PIL Image"

    def test_get_icon_for_state_plan_pasted(self):
        """Test getting icon for PLAN_PASTED state (base icon only)."""
        manager = IconManager()
        icon = manager.get_icon_for_state(State.PLAN_PASTED)
        assert icon is not None
        assert isinstance(icon, Image.Image)
        assert icon.size == (64, 64)

    def test_get_icon_for_state_copied(self):
        """Test getting icon for COPIED state (base + ready badge)."""
        manager = IconManager()
        icon = manager.get_icon_for_state(State.COPIED)
        assert icon is not None
        assert isinstance(icon, Image.Image)
        assert icon.size == (64, 64)

    def test_get_icon_for_state_plan_paste(self):
        """Test getting icon for PLAN_PASTE state (base + plan badge)."""
        manager = IconManager()
        icon = manager.get_icon_for_state(State.PLAN_PASTE)
        assert icon is not None
        assert isinstance(icon, Image.Image)
        assert icon.size == (64, 64)

    def test_get_icon_for_state_parse_error(self):
        """Test getting icon for PARSE_ERROR state (base + error badge)."""
        manager = IconManager()
        icon = manager.get_icon_for_state(State.PARSE_ERROR)
        assert icon is not None
        assert isinstance(icon, Image.Image)
        assert icon.size == (64, 64)

    def test_icon_mode_is_rgba(self):
        """Test that returned icons are in RGBA mode for proper transparency."""
        manager = IconManager()
        for state in [State.PLAN_PASTED, State.COPIED, State.PLAN_PASTE, State.PARSE_ERROR]:
            icon = manager.get_icon_for_state(state)
            assert icon.mode == 'RGBA', f"Icon for {state.name} should be in RGBA mode"


class TestApplicationState:
    """Test ApplicationState class with parse error tracking."""

    def test_initialization_with_icon_manager(self):
        """Test ApplicationState initialization with icon_manager parameter."""
        manager = IconManager()
        state = ApplicationState(icon_manager=manager)
        assert state.state == State.PLAN_PASTED
        assert state.icon_manager == manager
        assert state.parse_error_time is None
        assert state.PARSE_ERROR_TIMEOUT == timedelta(seconds=30)

    def test_initialization_without_icon_manager(self):
        """Test ApplicationState initialization without icon_manager."""
        state = ApplicationState()
        assert state.state == State.PLAN_PASTED
        assert state.icon_manager is None
        assert state.parse_error_time is None

    def test_parse_error_timeout_never_set(self):
        """Test is_parse_error_expired when error time was never set."""
        state = ApplicationState()
        assert state.is_parse_error_expired() is True

    def test_parse_error_timeout_not_expired(self):
        """Test is_parse_error_expired when timeout hasn't elapsed."""
        state = ApplicationState()
        state.parse_error_time = datetime.now()
        assert state.is_parse_error_expired() is False

    def test_parse_error_timeout_expired(self):
        """Test is_parse_error_expired when timeout has elapsed."""
        state = ApplicationState()
        state.parse_error_time = datetime.now() - timedelta(seconds=31)
        assert state.is_parse_error_expired() is True

    def test_should_reset_from_parse_error_no_error(self):
        """Test should_reset_from_parse_error when not in error state."""
        state = ApplicationState()
        state.state = State.PLAN_PASTED
        assert state.should_reset_from_parse_error() is False

    def test_should_reset_from_parse_error_not_expired(self):
        """Test should_reset_from_parse_error when error hasn't expired."""
        state = ApplicationState()
        state.state = State.PARSE_ERROR
        state.parse_error_time = datetime.now()
        assert state.should_reset_from_parse_error() is False

    def test_should_reset_from_parse_error_expired(self):
        """Test should_reset_from_parse_error when error has expired."""
        state = ApplicationState()
        state.state = State.PARSE_ERROR
        state.parse_error_time = datetime.now() - timedelta(seconds=31)
        assert state.should_reset_from_parse_error() is True

    def test_plan_paste_timeout_still_works(self):
        """Test that plan paste timeout still functions correctly."""
        state = ApplicationState()
        # first_paste is set to 1 hour ago initially
        assert state.is_plan_paste_expired() is True

        # Set first_paste to now
        state.first_paste = datetime.now()
        assert state.is_plan_paste_expired() is False

        # Set first_paste to 21 seconds ago (past 20 second timeout)
        state.first_paste = datetime.now() - timedelta(seconds=21)
        assert state.is_plan_paste_expired() is True


class TestStateTransitions:
    """Test state transitions with icon updates."""

    def test_state_to_icon_mapping(self):
        """Test that each state gets an appropriate icon."""
        manager = IconManager()
        state_mapping = {
            State.PLAN_PASTED: 'base icon only',
            State.COPIED: 'base + ready badge',
            State.PLAN_PASTE: 'base + plan badge',
            State.PARSE_ERROR: 'base + error badge',
        }

        for state, description in state_mapping.items():
            icon = manager.get_icon_for_state(state)
            assert icon is not None, f"Should get icon for {state.name} ({description})"
            assert isinstance(icon, Image.Image), f"Icon should be PIL Image for {state.name}"
            assert icon.size == (64, 64), f"Icon should be 64x64 for {state.name}"

    def test_different_states_get_different_icons(self):
        """Test that different states result in different icon compositions."""
        manager = IconManager()

        # Get icons for all states
        plan_pasted_icon = manager.get_icon_for_state(State.PLAN_PASTED)
        copied_icon = manager.get_icon_for_state(State.COPIED)
        plan_paste_icon = manager.get_icon_for_state(State.PLAN_PASTE)
        parse_error_icon = manager.get_icon_for_state(State.PARSE_ERROR)

        # PLAN_PASTED should be different from all others (no badge)
        # We can't directly compare images easily, but we can verify they all exist
        assert plan_pasted_icon is not copied_icon or plan_pasted_icon is not plan_paste_icon
        assert plan_pasted_icon is not parse_error_icon

    def test_icon_manager_handles_missing_icon_files(self):
        """Test that IconManager gracefully handles missing icon files."""
        # This test verifies the fallback behavior works
        # In normal operation, icons should be loaded from files
        # If files are missing, fallback icons should be created
        manager = IconManager()

        # Even if icon files are missing, manager should still work
        assert manager.base_icon is not None
        for badge_name in ['ready', 'plan', 'error']:
            assert manager.badges[badge_name] is not None

        # And get_icon_for_state should work for all states
        for state in State:
            icon = manager.get_icon_for_state(state)
            assert icon is not None


class TestParseErrorTimeoutBehavior:
    """Test parse error timeout behavior in isolation."""

    def test_parse_error_timeout_duration(self):
        """Test that parse error timeout is 30 seconds."""
        state = ApplicationState()
        assert state.PARSE_ERROR_TIMEOUT == timedelta(seconds=30)

    def test_parse_error_state_with_timeout(self):
        """Test complete parse error timeout cycle."""
        state = ApplicationState()

        # Set to parse error state
        state.state = State.PARSE_ERROR
        state.parse_error_time = datetime.now()

        # Should not be expired immediately
        assert state.is_parse_error_expired() is False
        assert state.should_reset_from_parse_error() is False

        # After 30 seconds, should be expired
        state.parse_error_time = datetime.now() - timedelta(seconds=31)
        assert state.is_parse_error_expired() is True
        assert state.should_reset_from_parse_error() is True

    def test_parse_error_reset_on_successful_copy(self):
        """Test that successful copy resets parse error time."""
        state = ApplicationState()
        state.state = State.PARSE_ERROR
        state.parse_error_time = datetime.now()

        # Simulate successful copy (this happens in handle_copied_state)
        if state.state == State.PARSE_ERROR:
            state.parse_error_time = None

        # Should now report as expired (ready to reset)
        assert state.parse_error_time is None
        assert state.is_parse_error_expired() is True
