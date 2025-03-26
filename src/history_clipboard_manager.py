from frontend import Gui
from clipboard_parser import get_split_sections
import pyperclip
import mouse
import time
from enum import Enum
from datetime import datetime, timedelta
import pyautogui as ag
import pystray
from sys import exit, stderr

from PIL import Image, ImageDraw


class State(Enum):
    COPIED = 1
    FIRST_PASTE = 2
    PLAN_PASTE = 3
    PLAN_PASTED = 4


PLAN_PASTE_TIME = timedelta(seconds=20)

# Initialise first paste so that it won't be recent
first_paste = datetime.now() - timedelta(hours=1)
state = State.PLAN_PASTED
consultation = {}


def middle_mouse():
    # State machine
    global state
    global consultation
    global first_paste
    global PLAN_PASTE_TIME

    if (
        state == State.PLAN_PASTE and datetime.now() - first_paste > PLAN_PASTE_TIME
    ) or state == State.PLAN_PASTED:
        # We are trying to copy a history
        print("Section 1: History collection")
        consultation = {}

        ag.click()
        ag.hotkey("ctrl", "a")
        ag.hotkey("ctrl", "c")

        clip = pyperclip.paste()
        if "History:" in clip and "Plan:" in clip:
            # TODO: fix try/except block to catch specific exception around parsing only
            try:
                sections = get_split_sections(clip)
                g = Gui(sections)
                g.remove_headings()
                consultation = g.show_gui()
                state = State.COPIED
            except Exception as e:
            #    print("Something went wrong: {}".format(e), file=stderr)
                print("Didn't find a consultation in clipboard")

    elif state == State.COPIED:
        # Try to paste the sections required
        print("Section 2: Pasting")
        for s in ["history", "exam", "imp", "plan"]:
            if s in consultation:
                pyperclip.copy(consultation[s])
                ag.hotkey("ctrl", "v")
            ag.press("tab")
            time.sleep(0.3)
        first_paste = datetime.now()
        state = State.PLAN_PASTE

    elif state == State.PLAN_PASTE:
        # We can't normally paste the plan if there has been a prescription
        print("Section 3: Pasting Plan")
        ag.click()
        ag.hotkey("ctrl", "v")
        state = State.PLAN_PASTED

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


def main():
    mouse.on_button(
        callback=middle_mouse, buttons=(mouse.MIDDLE), types=(mouse.DOWN, mouse.DOUBLE)
    )

    def quit(icon, item):
        icon.stop()
        exit(0)

    # In order for the icon to be displayed, you must provide an icon
    icon = pystray.Icon(
        "test name",
        icon=create_image(64, 64, "black", "white"),
        menu=pystray.Menu(pystray.MenuItem("Documentation History Importer", None), pystray.Menu.SEPARATOR, pystray.MenuItem("Exit", quit)),
    ).run()


if __name__ == "__main__":
    main()
