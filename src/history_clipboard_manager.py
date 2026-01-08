from frontend import Gui
from clipboard_parser import get_split_sections, ConsultationParseError
import pyperclip
import mouse
import time
from enum import Enum
from datetime import datetime, timedelta
import pyautogui as ag
import pystray
from sys import exit

from PIL import Image, ImageDraw
from pathlib import Path


class IconManager:
    """Manages loading and compositing system tray icons."""

    def __init__(self):
        """Initialize icon manager and load base icons."""
        self.icons_dir = Path(__file__).parent / "icons"
        self.base_icon = None
        self.badges = {
            'ready': None,
            'plan': None,
            'error': None
        }
        self._load_icons()

    def _load_icons(self):
        """Load all icon files from disk."""
        try:
            # Load base medical cross icon
            main_icon_path = self.icons_dir / "main.png"
            if main_icon_path.exists():
                self.base_icon = Image.open(main_icon_path)
            else:
                print(f"Warning: Base icon not found at {main_icon_path}")
                self.base_icon = self._create_fallback_icon()

            # Load badge overlays
            badge_files = {
                'ready': 'badge_ready.png',
                'plan': 'badge_plan.png',
                'error': 'badge_error.png'
            }

            for state, filename in badge_files.items():
                badge_path = self.icons_dir / filename
                if badge_path.exists():
                    self.badges[state] = Image.open(badge_path).convert("RGBA")
                else:
                    print(f"Warning: Badge icon not found at {badge_path}")
                    self.badges[state] = self._create_fallback_badge(state)

        except Exception as e:
            print(f"Error loading icons: {e}")
            self.base_icon = self._create_fallback_icon()

    def _create_fallback_icon(self):
        """Create a simple fallback icon if files are missing."""
        image = Image.new("RGBA", (64, 64), (0, 100, 200, 255))
        dc = ImageDraw.Draw(image)
        # Draw a simple medical cross
        center = 32
        # Horizontal bar
        dc.rectangle([center - 10, center - 3, center + 10, center + 3], fill=(255, 255, 255, 255))
        # Vertical bar
        dc.rectangle([center - 3, center - 10, center + 3, center + 10], fill=(255, 255, 255, 255))
        return image

    def _create_fallback_badge(self, state):
        """Create fallback badge if files are missing."""
        colors = {
            'ready': (0, 200, 0, 230),    # Green
            'plan': (255, 165, 0, 230),    # Orange
            'error': (220, 0, 0, 230)      # Red
        }
        badge = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        dc = ImageDraw.Draw(badge)
        dc.ellipse([4, 4, 28, 28], fill=colors.get(state, (128, 128, 128, 230)))
        return badge

    def get_icon_for_state(self, state):
        """Get the appropriate icon for the given application state.

        Args:
            state: State enum value

        Returns:
            PIL.Image: Composited icon for the state
        """
        # Start with base icon
        if self.base_icon is None:
            return self._create_fallback_icon()

        # Ensure base icon is RGBA for compositing
        icon = self.base_icon.convert("RGBA")

        # Add appropriate badge based on state
        if state == State.COPIED:
            badge = self.badges.get('ready')
        elif state == State.PLAN_PASTE:
            badge = self.badges.get('plan')
        elif state == State.PARSE_ERROR:
            badge = self.badges.get('error')
        else:
            # PLAN_PASTED state - no badge
            return icon

        # Composite badge onto icon if available
        if badge:
            # Position badge in bottom-right corner
            icon.paste(badge, (icon.width - badge.width, icon.height - badge.height), badge)

        return icon


class State(Enum):
    COPIED = 1
    FIRST_PASTE = 2
    PLAN_PASTE = 3
    PLAN_PASTED = 4
    PARSE_ERROR = 5


class ApplicationState:
    """Encapsulates all application state to avoid global variables."""

    def __init__(self, icon_manager=None):
        self.state = State.PLAN_PASTED
        self.consultation = {}
        self.first_paste = datetime.now() - timedelta(hours=1)
        self.record_consent = False
        self.bypass_gui = False
        self.PLAN_PASTE_TIME = timedelta(seconds=20)

        # Parse error timeout tracking
        self.parse_error_time = None
        self.PARSE_ERROR_TIMEOUT = timedelta(seconds=30)

        # Icon manager reference
        self.icon_manager = icon_manager

    def reset_consultation(self):
        """Reset the consultation data."""
        self.consultation = {}

    def is_plan_paste_expired(self):
        """Check if the plan paste time window has expired."""
        return datetime.now() - self.first_paste > self.PLAN_PASTE_TIME

    def is_parse_error_expired(self):
        """Check if parse error timeout has expired."""
        if self.parse_error_time is None:
            return True
        return datetime.now() - self.parse_error_time > self.PARSE_ERROR_TIMEOUT

    def should_reset_from_parse_error(self):
        """Check if we should reset from parse error state."""
        return (self.state == State.PARSE_ERROR and
                self.is_parse_error_expired())


def handle_plan_pasted_state(app_state):
    """Handle the initial history collection state.

    Args:
        app_state: ApplicationState instance
    """
    print("Section 1: History collection")
    app_state.reset_consultation()

    ag.click()
    ag.hotkey("ctrl", "a")
    ag.hotkey("ctrl", "c")

    clip = pyperclip.paste()

    try:
        sections = get_split_sections(clip)

        if sections['history'] and app_state.record_consent:
            sections['history'] += '\r\n(verbal consent given for AI transcription)'

        if app_state.bypass_gui:
            # Skip GUI - use sections directly after removing headings
            g = Gui(sections)
            g.remove_headings()
            app_state.consultation = g.state
        else:
            # Show GUI for editing
            g = Gui(sections)
            g.remove_headings()
            app_state.consultation = g.show_gui()

        app_state.state = State.COPIED

    except ConsultationParseError as e:
        # Content didn't match expected consultation format
        print(f"Consultation parsing failed: {e}")
        print("Please ensure you've copied a valid consultation from Heidi")
        app_state.state = State.PARSE_ERROR
        app_state.parse_error_time = datetime.now()

    except (KeyError, ValueError, AttributeError) as e:
        # Data structure or value errors during parsing
        print(f"Error processing consultation data: {type(e).__name__}: {e}")
        print("The consultation format may have changed")
        app_state.state = State.PARSE_ERROR
        app_state.parse_error_time = datetime.now()

    except Exception as e:
        # Catch-all for unexpected errors (e.g., GUI errors)
        print(f"Unexpected error: {type(e).__name__}: {e}")
        print("Please check the consultation format and try again")
        app_state.state = State.PARSE_ERROR
        app_state.parse_error_time = datetime.now()


def handle_copied_state(app_state):
    """Handle pasting sections after consultation is copied.

    Args:
        app_state: ApplicationState instance
    """
    print("Section 2: Pasting")
    for s in ["history", "exam", "imp", "plan"]:
        if s in app_state.consultation:
            pyperclip.copy(app_state.consultation[s])
            ag.hotkey("ctrl", "v")
        ag.press("tab")
        time.sleep(0.3)
    app_state.first_paste = datetime.now()

    # Reset parse error state on successful copy
    if app_state.state == State.PARSE_ERROR:
        app_state.parse_error_time = None

    app_state.state = State.PLAN_PASTE


def handle_plan_paste_state(app_state):
    """Handle pasting the plan section.

    Args:
        app_state: ApplicationState instance
    """
    print("Section 3: Pasting Plan")
    ag.click()
    ag.hotkey("ctrl", "v")
    app_state.state = State.PLAN_PASTED


def middle_mouse(app_state):
    """Handle middle mouse button clicks based on current application state.

    Args:
        app_state: ApplicationState instance containing all application state
    """
    # Auto-reset from parse error after timeout
    if app_state.should_reset_from_parse_error():
        print("Parse error timeout expired, resetting to normal state")
        app_state.state = State.PLAN_PASTED
        app_state.parse_error_time = None

    # Handle PARSE_ERROR state - allow user to retry immediately
    if app_state.state == State.PARSE_ERROR:
        print("Parse error state - resetting to copy new consultation")
        app_state.state = State.PLAN_PASTED
        app_state.parse_error_time = None
        handle_plan_pasted_state(app_state)

    # State machine dispatcher
    # If plan paste window has expired, just reset state (don't handle it)
    if (
        app_state.state == State.PLAN_PASTE and app_state.is_plan_paste_expired()
    ):
        print("Plan paste window expired, resetting to normal state")
        app_state.state = State.PLAN_PASTED

    elif app_state.state == State.PLAN_PASTED:
        handle_plan_pasted_state(app_state)

    elif app_state.state == State.COPIED:
        handle_copied_state(app_state)

    elif app_state.state == State.PLAN_PASTE:
        handle_plan_paste_state(app_state)

    else:
        print("Section 4: ??")

    print("Click!")


def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)

    return image

def toggle_consent(app_state, icon, item):
    """Toggle the consent recording flag.

    Args:
        app_state: ApplicationState instance
        icon: System tray icon instance
        item: Menu item that was clicked
    """
    app_state.record_consent = not item.checked


def toggle_bypass_gui(app_state, icon, item):
    """Toggle the GUI bypass flag.

    Args:
        app_state: ApplicationState instance
        icon: System tray icon instance
        item: Menu item that was clicked
    """
    app_state.bypass_gui = not item.checked


def main():
    """Main entry point for the application."""
    # Initialize icon manager first
    icon_manager = IconManager()
    app_state = ApplicationState(icon_manager=icon_manager)

    # Store icon reference for updates
    icon_ref = [None]  # Use list to allow assignment in nested function

    def quit(icon, item):
        icon.stop()
        exit(0)

    # Wrapper that updates icon after state changes
    def wrapped_middle_mouse():
        old_state = app_state.state
        middle_mouse(app_state)
        new_state = app_state.state

        if icon_ref[0] and app_state.icon_manager and old_state != new_state:
            try:
                new_icon = app_state.icon_manager.get_icon_for_state(new_state)
                icon_ref[0].icon = new_icon
            except Exception as e:
                print(f"Error updating icon: {e}")

    # Register mouse event with wrapped callback
    mouse.on_button(
        callback=wrapped_middle_mouse,
        buttons=(mouse.MIDDLE),
        types=(mouse.DOWN, mouse.DOUBLE)
    )

    # Create system tray icon with initial state
    icon = pystray.Icon(
        "test name",
        icon=icon_manager.get_icon_for_state(app_state.state),
        menu=pystray.Menu(
            pystray.MenuItem("Documentation History Importer", None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Automatically Record Consent",
                lambda icon, item: toggle_consent(app_state, icon, item),
                checked=lambda item: app_state.record_consent
            ),
            pystray.MenuItem(
                "Bypass GUI (Auto-paste)",
                lambda icon, item: toggle_bypass_gui(app_state, icon, item),
                checked=lambda item: app_state.bypass_gui
            ),
            pystray.MenuItem("Exit", quit)
        ),
    )

    icon_ref[0] = icon  # Store reference for icon updates
    icon.run()


if __name__ == "__main__":
    main()
