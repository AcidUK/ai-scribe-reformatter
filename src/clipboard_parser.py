import re
from collections import namedtuple
from typing import List, Optional
import pyperclip
from os import linesep

SectionResponse = namedtuple("SectionResponse", ["output", "newlines_handled"])


class ConsultationParseError(Exception):
    """Raised when the clipboard content cannot be parsed as a valid consultation."""

    def __init__(self, message: str, clipboard_preview: Optional[str] = None):
        """Initialize the error with a message and optional clipboard preview.

        Args:
            message: Description of what went wrong
            clipboard_preview: First 100 chars of clipboard content for debugging
        """
        self.message = message
        self.clipboard_preview = clipboard_preview[:100] if clipboard_preview else None
        super().__init__(self.message)

    def __str__(self):
        if self.clipboard_preview:
            return f"{self.message} | Clipboard preview: '{self.clipboard_preview}...'"
        return self.message

# Configuration for heading pattern matching
HEADING_PATTERNS = {
    'history': [r'^History:'],
    'pmh': [r'^Past Medical History:', r'PMHx:', r'PMH:'],
    'exam': [r'^Physical Examination:', r'Examination:', r'Exam:', r'O/E:'],
    'impression': [r'^Impression:', r'Assessment:', r'Imp:'],
    'plan': [r'^Management Plan:', r'Plan:']
}


class BlockItem:
    def __init__(
        self, heading: str, bullets: List[str], prose: str, comma_separated_prose: str
    ):
        self.heading = heading
        self.bullets = bullets
        self.prose = prose
        self.comma_separated_prose = comma_separated_prose

    def _match_heading_type(self):
        """Match heading against patterns to determine section type."""
        for section_type, patterns in HEADING_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, self.heading):
                    return section_type
        return None

    def parse(self):
        output = ""

        section_type = self._match_heading_type()

        if section_type == 'history':
            result = self.parse_history()
        elif section_type == 'pmh':
            result = self.parse_pmh()
        elif section_type == 'exam':
            result = self.parse_exam()
        elif section_type == 'impression':
            result = self.parse_imp()
        elif section_type == 'plan':
            result = self.parse_plan()
        else:
            result = self.parse_unhandled()

        output = result.output
        if not result.newlines_handled:
            output += "\n\n"

        return output

    def parse_history(self):
        return SectionResponse(self.heading + "\n" + self.prose + "\n", True)

    def parse_pmh(self):
        self.heading = "PMH:"
        output = ""
        if self.comma_separated_prose.lower().startswith('history of'):
            output = self.comma_separated_prose
        else:
            output = "Hx of " + self.comma_separated_prose
        return SectionResponse(output, False)

    def parse_exam(self):
        if self.comma_separated_prose == "N/A":
            return SectionResponse("", True)

        self.heading = "Examination:"
        output_bullets = [b.replace("Vitals", "Obs") for b in self.bullets]
        return SectionResponse(self.heading + "\n" + "\n".join(output_bullets), False)

    def parse_imp(self):
        if self.comma_separated_prose == "Not explicitly mentioned":
            return SectionResponse("", True)

        self.heading = "Impression:"
        return SectionResponse(self.heading + "\n" + "\n".join(self.bullets), False)

    def parse_plan(self):
        self.heading = "Plan:"
        return SectionResponse(self.heading + "\n" + "\n".join(self.bullets), False)

    def parse_patient_summary(self):
        return None

    def parse_unhandled(self):
        # return SectionResponse(self.heading + "\n" + "\n".join(self.bullets), False)
        return SectionResponse(self.heading + " " + self.prose + "\n", True)


def block_parser(block: str) -> BlockItem:
    """Handles a block (Header followed by bullet points)"""

    block = block.lstrip().rstrip()

    if block == "":
        return None  # Guard for empty block entirely

    contents = block.splitlines()

    heading = contents.pop(0)
    bullets = [ bullet.lstrip("- ") for bullet in contents ]

    # Filter out empty bullets and separator lines (like "---" or "---")
    bullets = [b for b in bullets if b.strip() and not all(c in '-_=' for c in b.strip())]

    if not bullets:
        return None  # Guard for a block with a heading but no contents

    prose = parse_bullets_to_prose(contents)
    comma_separated_prose = parse_bullets_to_comma_separated_prose(contents)

    item = BlockItem(
        heading=heading,
        bullets=bullets,
        prose=prose,
        comma_separated_prose=comma_separated_prose,
    )

    return item


def parse_bullets_to_prose(bullets: list) -> str:
    """Joins bullet point list together to make prose, removes extra full stops"""

    output = ""

    for line in bullets:
        if line.endswith("."):
            line = line[:-1]
        line = line.replace("- ", "")
        output += line + ". "

    return output[:-2]


def parse_bullets_to_comma_separated_prose(bullets: list) -> str:
    """Makes first letter of bullet points lower case, then joins bullet points with a comma"""

    output = ""

    for line in bullets:
        if line.endswith("."):
            line = line[:-1]
        line = line.replace("- ", "")
        # Make first letter lowercase
        if line:
            line = line[0].lower() + line[1:]
        output += line + ", "

    return output[:-2]  # Remove trailing comma and space


def get_items(consultation: str):
    consultation = consultation.rstrip()
    # Need to split on two subsequent linebreaks, different on windows vs linux
    if "\r\n" in consultation:
        sections = consultation.split("\r\n\r\n")
    else:
        sections = consultation.split("\n\n")

    items = [block_parser(s) for s in sections]
    return items


def _get_section_category(heading):
    """Determine which category a heading belongs to.

    Args:
        heading: The heading string to categorize

    Returns:
        str: The section key ('history', 'exam', 'imp', 'plan') or None
    """
    section_map = {
        "History:": "history",
        "Examination:": "exam",
        "Impression:": "imp",
        "Plan:": "plan",
    }
    return section_map.get(heading)


def _format_section_output(output, heading, current_section):
    """Format output based on section context.

    Args:
        output: The parsed output string
        heading: The heading of the current item
        current_section: The current section being processed

    Returns:
        str: Formatted output string
    """
    # Add newline before non-History subsections in the history section
    if current_section == "history" and heading != 'History:':
        output = "\r\n" + output
    return output


def _append_to_section(result, section_key, output):
    """Append output to a section, handling None values.

    Args:
        result: The result dictionary
        section_key: The section key to append to
        output: The output string to append
    """
    if result[section_key]:
        result[section_key] += output
    else:
        result[section_key] = output


def validate_consultation_content(content: str) -> None:
    """Validate that content appears to be a consultation from Heidi.

    Args:
        content: The clipboard content to validate

    Raises:
        ConsultationParseError: If content doesn't appear to be a valid consultation
    """
    if not content or not content.strip():
        raise ConsultationParseError("Clipboard is empty")

    # Check for required consultation markers
    has_history = any(marker in content for marker in ["History:", "History\n", "History\r\n"])
    has_plan = any(marker in content for marker in ["Plan:", "Plan\n", "Plan\r\n"])

    if not has_history:
        raise ConsultationParseError(
            "Missing 'History' section - clipboard content doesn't appear to be a consultation",
            content
        )

    if not has_plan:
        raise ConsultationParseError(
            "Missing 'Plan' section - clipboard content doesn't appear to be a consultation",
            content
        )

    # Check that content has reasonable structure (multiple lines/sections)
    lines = content.splitlines()
    if len(lines) < 3:
        raise ConsultationParseError(
            "Content too short to be a valid consultation",
            content
        )


def get_split_sections(consultation: str) -> dict:
    """Gets history, exam, imp and plan from consultation

    Args:
        consultation (str): a multiline string containing a consultation from heidi using the H&P template

    Returns:
        dict: A dictionary containing history, exam, imp and plan sections

    Raises:
        ConsultationParseError: If the consultation content is invalid or cannot be parsed
    """
    # Validate content before parsing
    validate_consultation_content(consultation)

    main_history = consultation.partition('\r\nPatient Summary')[0]  # Dump patient summary and after
    items = get_items(main_history)

    result = dict.fromkeys(["history", "exam", "imp", "plan"])
    current_section = "history"

    for item in items:
        if item is None:
            continue
        
        output = item.parse()
        output = linesep.join([s for s in output.splitlines() if s])

        # Update current section if we encounter a section heading
        section_category = _get_section_category(item.heading)
        if section_category:
            current_section = section_category

        # Special case: Investigations always go in history (check for variations in heading format)
        if "Investigations" in item.heading:
            # Ensure it's on its own line with proper spacing
            if result["history"]:
                _append_to_section(result, "history", "\r\n\r\n" + output)
            else:
                _append_to_section(result, "history", output)
        else:
            output = _format_section_output(output, item.heading, current_section)
            _append_to_section(result, current_section, output)

    return result


def main(consultation: str):
    items = get_items(consultation)

    output = ""
    for item in items:
        if item != None:
            output += item.parse()

    return output


if __name__ == "__main__":
    consultation = pyperclip.paste()
    pyperclip.copy(main(consultation))
