import re


TIME_PATTERNS = {

    "daily": [
        r"\bevery day\b",
        r"\bdaily\b",
    ],

    "weekly": [
        r"\bevery monday\b",
        r"\bevery tuesday\b",
        r"\bevery wednesday\b",
        r"\bevery thursday\b",
        r"\bevery friday\b",
        r"\bevery saturday\b",
        r"\bevery sunday\b",
    ],

    "relative": [
        r"\btoday\b",
        r"\byesterday\b",
        r"\btomorrow\b",
        r"\blast week\b",
        r"\bnext week\b",
        r"\bnext month\b",
    ],

    "time_of_day": [
        r"\bmorning\b",
        r"\bafternoon\b",
        r"\bevening\b",
        r"\bnight\b",
    ],

}


def extract_temporal_information(
    text: str,
):
    """
    Extract temporal expressions
    using regular expressions.
    """

    sentence = text.lower()

    temporal = []

    for category, patterns in TIME_PATTERNS.items():

        for pattern in patterns:

            match = re.search(
                pattern,
                sentence,
            )

            if match:

                temporal.append(

                    {
                        "category": category,
                        "value": match.group(),
                    }

                )

    return temporal