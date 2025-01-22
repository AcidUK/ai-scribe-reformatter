import re
from collections import namedtuple
from typing import List
import pyperclip
from os import linesep

SectionResponse = namedtuple("SectionResponse", ["output", "newlines_handled"])


class BlockItem:
    def __init__(
        self, heading: str, bullets: List[str], prose: str, comma_separated_prose: str
    ):
        self.heading = heading
        self.bullets = bullets
        self.prose = prose
        self.comma_separated_prose = comma_separated_prose

    def parse(self):
        output = ""

        if re.match(r"^History:", self.heading):
            result = self.parse_history()

        elif (
            re.match(r"^Past Medical History:", self.heading)
            or re.match(r"PMHx:", self.heading)
            or re.match(r"PMH:", self.heading)
        ):
            result = self.parse_pmh()

        elif (
            re.match(r"^Physical Examination:", self.heading)
            or re.match(r"Examination:", self.heading)
            or re.match(r"Exam:", self.heading)
            or re.match(r"O/E:", self.heading)
        ):
            result = self.parse_exam()

        elif re.match(r"^Impression:", self.heading):
            result = self.parse_imp()

        elif re.match(r"^Management Plan:", self.heading) or re.match(
            r"Plan:", self.heading
        ):
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

    if bullets == [""]:
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

    lower_case = [bullet[0].lower() + bullet[1:] for bullet in bullets]
    prose = parse_bullets_to_prose(lower_case)
    prose = prose.replace(". ", ", ")
    return prose


def get_items(consultation: str):
    # Need to split on two subsequent linebreaks, different on windows vs linux
    if "\r\n" in consultation:
        sections = consultation.split("\r\n\r\n")
    else:
        sections = consultation.split("\n\n")

    items = [block_parser(s) for s in sections]
    return items


def get_split_sections(consultation: str) -> dict:
    """Gets history, exam, imp and plan from consultation

    Args:
        consultation (str): a multiline string containing a consultation from heidi using the H&P template

    Returns:
        dict: A dictionary containing history, eam, imp and plan sections
    """

    main_history = consultation.partition('\r\nPatient Summary')[0] # Dump patient summary and after
    items = get_items(main_history)

    titles = {
        "history": "History:",
        "exam": "Examination:",
        "imp": "Impression:",
        "plan": "Plan:",
    }
    sections = dict((v, k) for k, v in titles.items())
    result = dict.fromkeys(titles.keys())

    cur = "history"

    for i in items:
        output = i.parse()
        output = linesep.join([s for s in output.splitlines() if s])
        if i.heading in sections:
            cur = sections[i.heading]
        if cur == "history" and (i.heading != 'History:'): # Put newline before new sections in history
            output = "\r\n" + output
        if i.heading == "Investigations: ": # Put investigations in history
            result["history"] += "\r\n" + output
        if result[cur]:
            result[cur] += output
        else:
            result[cur] = output

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
