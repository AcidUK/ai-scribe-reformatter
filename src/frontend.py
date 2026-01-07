import FreeSimpleGUI as sg

# import PySimpleGUI as sg


class Gui:
    """GUI for editing consultation sections."""

    # Define section configuration
    SECTIONS = [
        ("history", "History", 5),
        ("exam", "Examination", 4),
        ("imp", "Impression", 3),
        ("plan", "Plan", 5),
    ]

    def __init__(self, kwargs):
        self.state = {}
        self.state.update(kwargs)

    @property
    def history(self):
        return self.state.get("history", "")

    @history.setter
    def history(self, value):
        self.state["history"] = value

    @property
    def exam(self):
        return self.state.get("exam", "")

    @exam.setter
    def exam(self, value):
        self.state["exam"] = value

    @property
    def imp(self):
        return self.state.get("imp", "")

    @imp.setter
    def imp(self, value):
        self.state["imp"] = value

    @property
    def plan(self):
        return self.state.get("plan", "")

    @plan.setter
    def plan(self, value):
        self.state["plan"] = value

    def update(self, history, exam, imp, plan):
        """Update all section values."""
        self.history = history
        self.exam = exam
        self.imp = imp
        self.plan = plan

    def clear(self):
        """Clear all state."""
        self.state = {}

    def remove_headings(self):
        """Remove the first line (heading) from each section."""
        for item, value in self.state.items():
            if value:
                self.state[item] = "\r\n".join(value.splitlines()[1:])

    def _create_section_widget(self, section_key, section_label, text_size):
        """Create checkbox and text input widgets for a section.

        Args:
            section_key: The key for this section (e.g., 'history')
            section_label: The display label (e.g., 'History')
            text_size: The number of rows for the text input

        Returns:
            list: Layout elements for this section
        """
        return [
            [
                sg.Checkbox(
                    section_label,
                    default=True,
                    enable_events=True,
                    k=f"{section_key}_check"
                )
            ],
            [
                sg.Multiline(
                    default_text=self.state.get(section_key, ""),
                    size=(None, text_size),
                    k=f"{section_key}_text"
                )
            ],
            [sg.HorizontalSeparator()],
        ]

    def show_gui(self):
        """Display GUI for editing consultation sections.

        Returns:
            dict: Updated state with user modifications
        """
        # Build layout dynamically from SECTIONS configuration
        layout = []
        for section_key, section_label, text_size in self.SECTIONS:
            layout.extend(self._create_section_widget(section_key, section_label, text_size))

        layout.append([sg.Button("Ok")])

        # Create the Window
        window = sg.Window("History Clipboard Monitor", layout, keep_on_top=True)

        # Build enabled_map dynamically from SECTIONS
        enabled_map = {
            f"{section_key}_text": f"{section_key}_check"
            for section_key, _, _ in self.SECTIONS
        }

        # Event Loop to process "events" and get the "values" of the inputs
        while True:
            event, values = window.read()

            # Update visibility based on checkbox state
            for text_key, check_key in enabled_map.items():
                window[text_key].update(visible=values[check_key])

            # if user closes window or clicks cancel
            if event == sg.WIN_CLOSED or event == "Ok":
                self.clear()

                # Collect checked sections
                for section_key, _, _ in self.SECTIONS:
                    if values[f"{section_key}_check"]:
                        self.state[section_key] = values[f"{section_key}_text"]

                break

        window.close()
        return self.state
