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
import logging
import sys
import traceback

from PIL import Image, ImageDraw
from pathlib import Path


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

LOG_FILE = Path.cwd() / "scribe_reformatter_debug.log"

# Module-level logger — children can do: logging.getLogger(__name__)
logger = logging.getLogger("scribe_reformatter")


def setup_logging(debug_mode: bool = False):
    """Configure logging with console + optional file handler.

    The **file handler** is only added when *debug_mode* is True, so no
    log file is created until the user explicitly enables debug mode.
    The **console handler** respects *debug_mode* to control verbosity.
    """
    root = logging.getLogger("scribe_reformatter")
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ---- File handler (only when debug enabled) ----
    if debug_mode:
        fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)

    # ---- Console handler ----
    console_level = logging.DEBUG if debug_mode else logging.INFO
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(console_level)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    root.addHandler(ch)

    logger.info("Logging initialised — debug mode: %s", debug_mode)


def set_console_debug(enabled: bool):
    """Toggle the console handler between DEBUG and INFO, and add/remove
    the file handler so no log file is created until debug mode is enabled."""
    root = logging.getLogger("scribe_reformatter")

    # Manage file handler
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    if enabled and not file_handlers:
        fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root.addHandler(fh)
        logger.info("Log file enabled: %s", LOG_FILE)
    elif not enabled and file_handlers:
        for h in file_handlers:
            h.close()
            root.removeHandler(h)
        logger.info("Log file disabled")

    # Console handler
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            h.setLevel(logging.DEBUG if enabled else logging.INFO)
    logger.info("Console logging set to %s", "DEBUG" if enabled else "INFO")


# ---------------------------------------------------------------------------
# Icons
# ---------------------------------------------------------------------------

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
            main_icon_path = self.icons_dir / "main.png"
            if main_icon_path.exists():
                self.base_icon = Image.open(main_icon_path)
                logger.debug("Loaded base icon from %s", main_icon_path)
            else:
                logger.warning("Base icon not found at %s — using fallback", main_icon_path)
                self.base_icon = self._create_fallback_icon()

            badge_files = {
                'ready': 'badge_ready.png',
                'plan': 'badge_plan.png',
                'error': 'badge_error.png'
            }

            for state, filename in badge_files.items():
                badge_path = self.icons_dir / filename
                if badge_path.exists():
                    self.badges[state] = Image.open(badge_path).convert("RGBA")
                    logger.debug("Loaded %s badge from %s", state, badge_path)
                else:
                    logger.warning("Badge not found at %s — using fallback", badge_path)
                    self.badges[state] = self._create_fallback_badge(state)

        except Exception as e:
            logger.error("Error loading icons: %s", e, exc_info=True)
            self.base_icon = self._create_fallback_icon()

    def _create_fallback_icon(self):
        """Create a simple fallback icon if files are missing."""
        image = Image.new("RGBA", (64, 64), (0, 100, 200, 255))
        dc = ImageDraw.Draw(image)
        center = 32
        dc.rectangle([center - 10, center - 3, center + 10, center + 3], fill=(255, 255, 255, 255))
        dc.rectangle([center - 3, center - 10, center + 3, center + 10], fill=(255, 255, 255, 255))
        return image

    def _create_fallback_badge(self, state):
        """Create fallback badge if files are missing."""
        colors = {
            'ready': (0, 200, 0, 230),
            'plan': (255, 165, 0, 230),
            'error': (220, 0, 0, 230)
        }
        badge = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        dc = ImageDraw.Draw(badge)
        dc.ellipse([4, 4, 28, 28], fill=colors.get(state, (128, 128, 128, 230)))
        return badge

    def get_icon_for_state(self, state):
        """Get the appropriate icon for the given application state."""
        if self.base_icon is None:
            return self._create_fallback_icon()

        icon = self.base_icon.convert("RGBA")

        if state == State.COPIED:
            badge = self.badges.get('ready')
        elif state == State.PLAN_PASTE:
            badge = self.badges.get('plan')
        elif state == State.PARSE_ERROR:
            badge = self.badges.get('error')
        else:
            return icon

        if badge:
            icon.paste(badge, (icon.width - badge.width, icon.height - badge.height), badge)

        return icon


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

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
        self.debug_mode = False
        self.PLAN_PASTE_TIME = timedelta(seconds=20)

        # Parse error timeout tracking
        self.parse_error_time = None
        self.PARSE_ERROR_TIMEOUT = timedelta(seconds=30)

        # Icon manager reference
        self.icon_manager = icon_manager

    def reset_consultation(self):
        """Reset the consultation data."""
        self.consultation = {}
        logger.debug("Consultation data reset")

    def is_plan_paste_expired(self):
        """Check if the plan paste time window has expired."""
        expired = datetime.now() - self.first_paste > self.PLAN_PASTE_TIME
        logger.debug("Plan paste expired check: %s (elapsed=%s, timeout=%s)",
                      expired, datetime.now() - self.first_paste, self.PLAN_PASTE_TIME)
        return expired

    def is_parse_error_expired(self):
        """Check if parse error timeout has expired."""
        if self.parse_error_time is None:
            return True
        return datetime.now() - self.parse_error_time > self.PARSE_ERROR_TIMEOUT

    def should_reset_from_parse_error(self):
        """Check if we should reset from parse error state."""
        return (self.state == State.PARSE_ERROR and
                self.is_parse_error_expired())


# ---------------------------------------------------------------------------
# State handlers
# ---------------------------------------------------------------------------

def handle_plan_pasted_state(app_state):
    """Handle the initial history collection — copy from Heidi, parse, show GUI.

    The entire body is wrapped in try/except so that pyautogui or pyperclip
    failures (e.g. FailSafeException, empty clipboard) cannot kill the mouse
    callback permanently.
    """
    logger.info("State handler: PLAN_PASTED → collecting consultation from clipboard")
    app_state.reset_consultation()

    try:
        logger.debug("Performing click + Ctrl+A + Ctrl+C to capture consultation")
        ag.click()
        ag.hotkey("ctrl", "a")
        ag.hotkey("ctrl", "c")
        time.sleep(0.1)  # brief settle

        clip = pyperclip.paste()
        logger.debug("Clipboard captured — length=%d chars", len(clip) if clip else 0)
        logger.debug("Clipboard preview:\n%s", _safe_preview(clip))

    except Exception as e:
        logger.error("Failed to capture clipboard: %s: %s", type(e).__name__, e,
                      exc_info=True)
        app_state.state = State.PARSE_ERROR
        app_state.parse_error_time = datetime.now()
        return

    try:
        logger.debug("Parsing consultation sections...")
        sections = get_split_sections(clip)

        logger.debug("Parsed sections: %s",
                      {k: f"{len(v)} chars" if v else "empty" for k, v in sections.items()})

        if sections['history'] and app_state.record_consent:
            sections['history'] += '\r\n(verbal consent given for AI transcription)'
            logger.debug("Appended consent note to history")

        if app_state.bypass_gui:
            logger.info("Bypass GUI enabled — using sections directly")
            g = Gui(sections)
            g.remove_headings()
            app_state.consultation = g.state
        else:
            logger.info("Showing GUI editor")
            g = Gui(sections)
            g.remove_headings()
            app_state.consultation = g.show_gui()
            logger.debug("GUI returned consultation keys: %s", list(app_state.consultation.keys()))

        logger.info("Consultation parsed successfully → state COPIED")
        app_state.state = State.COPIED

    except ConsultationParseError as e:
        logger.warning("ConsultationParseError: %s", e)
        logger.debug("Full clipboard that failed to parse:\n%s", _safe_preview(clip, max_chars=2000))
        app_state.state = State.PARSE_ERROR
        app_state.parse_error_time = datetime.now()

    except (KeyError, ValueError, AttributeError) as e:
        logger.error("Data structure error during parsing: %s: %s", type(e).__name__, e,
                      exc_info=True)
        app_state.state = State.PARSE_ERROR
        app_state.parse_error_time = datetime.now()

    except Exception as e:
        logger.error("Unexpected error during parsing/GUI: %s: %s", type(e).__name__, e,
                      exc_info=True)
        app_state.state = State.PARSE_ERROR
        app_state.parse_error_time = datetime.now()


def handle_copied_state(app_state):
    """Handle pasting sections into SystmOne."""
    logger.info("State handler: COPIED → pasting sections into SystmOne")
    for s in ["history", "exam", "imp", "plan"]:
        if s in app_state.consultation and app_state.consultation[s]:
            logger.debug("Pasting section '%s' (%d chars)", s, len(app_state.consultation[s]))
            pyperclip.copy(app_state.consultation[s])
            ag.hotkey("ctrl", "v")
        else:
            logger.debug("Section '%s' is empty — skipping, pressing tab", s)
        ag.press("tab")
        time.sleep(0.3)
    app_state.first_paste = datetime.now()
    app_state.state = State.PLAN_PASTE
    logger.info("All sections pasted → state PLAN_PASTE (window: %ss)",
                app_state.PLAN_PASTE_TIME.total_seconds())


def handle_plan_paste_state(app_state):
    """Handle pasting the plan section separately."""
    logger.info("State handler: PLAN_PASTE → pasting plan into Plan field")
    ag.click()
    ag.hotkey("ctrl", "v")
    app_state.state = State.PLAN_PASTED
    logger.info("Plan pasted → state PLAN_PASTED")


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def middle_mouse(app_state):
    """Handle middle mouse button clicks based on current application state."""
    logger.debug("Middle click received — current state: %s", app_state.state.name)

    # Auto-reset from parse error after timeout
    if app_state.should_reset_from_parse_error():
        logger.info("Parse error timeout expired — auto-resetting to PLAN_PASTED")
        app_state.state = State.PLAN_PASTED
        app_state.parse_error_time = None

    # Handle PARSE_ERROR state — allow user to retry immediately
    if app_state.state == State.PARSE_ERROR:
        logger.info("In PARSE_ERROR — resetting to retry consultation copy")
        app_state.state = State.PLAN_PASTED
        app_state.parse_error_time = None
        handle_plan_pasted_state(app_state)
        return  # ← prevent fall-through to dispatcher

    # State machine dispatcher
    if (
        app_state.state == State.PLAN_PASTE and app_state.is_plan_paste_expired()
    ):
        logger.info("Plan paste window expired — resetting to PLAN_PASTED")
        app_state.state = State.PLAN_PASTED

    elif app_state.state == State.PLAN_PASTED:
        handle_plan_pasted_state(app_state)

    elif app_state.state == State.COPIED:
        handle_copied_state(app_state)

    elif app_state.state == State.PLAN_PASTE:
        handle_plan_paste_state(app_state)

    else:
        logger.warning("Unhandled state: %s — no action taken", app_state.state.name)

    logger.debug("Middle click processing complete — new state: %s", app_state.state.name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_preview(text: str, max_chars: int = 500) -> str:
    """Return a truncated, newline-safe preview of text for logging."""
    if not text:
        return "<empty>"
    preview = text[:max_chars]
    if len(text) > max_chars:
        preview += f" … [truncated, total {len(text)} chars]"
    return preview.replace("\r\n", "\\r\\n").replace("\n", "\\n")


def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


# ---------------------------------------------------------------------------
# Menu callbacks
# ---------------------------------------------------------------------------

def toggle_consent(app_state, icon, item):
    app_state.record_consent = not item.checked
    logger.info("Record consent toggled → %s", app_state.record_consent)


def toggle_bypass_gui(app_state, icon, item):
    app_state.bypass_gui = not item.checked
    logger.info("Bypass GUI toggled → %s", app_state.bypass_gui)


def toggle_debug(app_state, icon, item):
    """Toggle debug (verbose) console logging."""
    new_val = not item.checked
    app_state.debug_mode = new_val
    set_console_debug(new_val)
    logger.info("Debug mode toggled → %s", new_val)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main entry point for the application."""
    setup_logging(debug_mode=False)

    logger.info("=" * 60)
    logger.info("AI Scribe Reformatter starting")
    logger.info("Python: %s | Executable: %s", sys.version.replace("\n", " "), sys.executable)
    logger.info("Working directory: %s", Path.cwd())
    logger.info("=" * 60)

    icon_manager = IconManager()
    app_state = ApplicationState(icon_manager=icon_manager)

    # Store icon reference for updates
    icon_ref = [None]

    def quit(icon, item):
        logger.info("Exit requested — shutting down")
        icon.stop()
        exit(0)

    # Wrapper that updates icon after state changes and catches errors
    def wrapped_middle_mouse():
        old_state = app_state.state
        try:
            middle_mouse(app_state)
        except Exception as e:
            # Catch-all so the mouse callback is NEVER killed by an unhandled exception.
            # This was the root cause of the "red cross + stops responding" bug.
            logger.critical("UNHANDLED exception in middle_mouse callback: %s: %s",
                            type(e).__name__, e, exc_info=True)
            app_state.state = State.PARSE_ERROR
            app_state.parse_error_time = datetime.now()

        new_state = app_state.state

        if icon_ref[0] and app_state.icon_manager and old_state != new_state:
            try:
                new_icon = app_state.icon_manager.get_icon_for_state(new_state)
                icon_ref[0].icon = new_icon
                logger.debug("Tray icon updated: %s → %s", old_state.name, new_state.name)
            except Exception as e:
                logger.error("Error updating tray icon: %s", e, exc_info=True)

    # Register mouse event with wrapped callback
    mouse.on_button(
        callback=wrapped_middle_mouse,
        buttons=(mouse.MIDDLE),
        types=(mouse.DOWN, mouse.DOUBLE)
    )
    logger.info("Middle mouse button listener registered")

    # Create system tray icon
    icon = pystray.Icon(
        "test name",
        icon=icon_manager.get_icon_for_state(app_state.state),
        menu=pystray.Menu(
            pystray.MenuItem("AI Scribe Reformatter", None),
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
            pystray.MenuItem(
                "Debug Mode (verbose console)",
                lambda icon, item: toggle_debug(app_state, icon, item),
                checked=lambda item: app_state.debug_mode
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", quit)
        ),
    )

    icon_ref[0] = icon
    logger.info("System tray icon created — running")
    icon.run()


if __name__ == "__main__":
    main()
