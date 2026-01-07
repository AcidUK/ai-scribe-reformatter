from frontend import Gui
from clipboard_parser import get_split_sections
import pyperclip
import mouse
import time
from enum import Enum
from datetime import datetime, timedelta
import pyautogui as ag
import pystray
from sys import exit

from PIL import Image, ImageDraw


class State(Enum):
    COPIED = 1
    FIRST_PASTE = 2
    PLAN_PASTE = 3
    PLAN_PASTED = 4


class ApplicationState:
    """Encapsulates all application state to avoid global variables."""

    def __init__(self):
        self.state = State.PLAN_PASTED
        self.consultation = {}
        self.first_paste = datetime.now() - timedelta(hours=1)
        self.record_consent = False
        self.bypass_gui = False
        self.PLAN_PASTE_TIME = timedelta(seconds=20)

    def reset_consultation(self):
        """Reset the consultation data."""
        self.consultation = {}

    def is_plan_paste_expired(self):
        """Check if the plan paste time window has expired."""
        return datetime.now() - self.first_paste > self.PLAN_PASTE_TIME


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
    if "History:" in clip and "Plan:" in clip:
        # TODO: fix try/except block to catch specific exception around parsing only
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
        except Exception as e:
            print(f"Error parsing consultation: {e}")
            print("Didn't find a consultation in clipboard")


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
    # State machine dispatcher
    if (
        app_state.state == State.PLAN_PASTE and app_state.is_plan_paste_expired()
    ) or app_state.state == State.PLAN_PASTED:
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
    app_state = ApplicationState()

    # Create callback wrapper to pass app_state to middle_mouse
    mouse.on_button(
        callback=lambda: middle_mouse(app_state),
        buttons=(mouse.MIDDLE),
        types=(mouse.DOWN, mouse.DOUBLE)
    )

    def quit(icon, item):
        icon.stop()
        exit(0)

    # In order for the icon to be displayed, you must provide an icon
    icon = pystray.Icon(
        "test name",
        icon=create_image(64, 64, "black", "white"),
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
    ).run()


if __name__ == "__main__":
    main()
