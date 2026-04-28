from __future__ import annotations
import re

# Word-to-number map for spoken numbers
WORD_NUMS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000,
}

TENS = {"twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"}
ONES = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
        "seventeen", "eighteen", "nineteen"}


def words_to_number(text: str) -> int | None:
    """Convert a word-number string like 'seventy six' to 76."""
    text = text.strip().lower()
    words = text.split()
    total = 0
    current = 0
    for word in words:
        if word not in WORD_NUMS:
            return None
        val = WORD_NUMS[word]
        if val == 100:
            current = (current if current else 1) * 100
        elif val == 1000:
            total += (current if current else 1) * 1000
            current = 0
        else:
            current += val
    return total + current if (total + current) > 0 else None


def _extract_theme(note: str):
    """
    If note starts with 'theme <name>, <rest>', return (name, rest).
    Otherwise return (None, note) unchanged.
    Requires a comma after the theme name so 'theme' mid-note isn't accidentally parsed.
    """
    m = re.match(r'^theme[:\s]+([^,]+),\s*(.*)', note.strip(), re.IGNORECASE)
    if m:
        theme_name = m.group(1).strip()
        remaining = m.group(2).strip()
        if theme_name and remaining:
            return theme_name, remaining
    return None, note


def parse_annotation(transcript: str) -> dict | None:
    """
    Parse a voice transcript into {page, note, theme}.

    Supports:
      - "Page 42, symbolism of the green light"
      - "Page 47, theme patriarchy, symbolism of the burqa"
      - "page 103 quote: old sport"
      - "pg 55 irony"
      - "Page seventy six character shift"
      - "Page 12 comma metaphor of fire"

    theme is None when not specified (Unclassified).
    Returns None if no page number found.
    """
    text = transcript.strip()

    # Replace "comma" spoken literally with actual comma
    text = re.sub(r'\bcomma\b', ',', text, flags=re.IGNORECASE)
    # Replace "colon" spoken literally
    text = re.sub(r'\bcolon\b', ':', text, flags=re.IGNORECASE)

    # Pattern 1: "page/pg <digits>"
    digit_match = re.match(
        r'(?:page|pg)[\s,]+(\d+)[\s,]*(.+)?',
        text,
        re.IGNORECASE
    )
    if digit_match:
        page = int(digit_match.group(1))
        note = (digit_match.group(2) or "").strip().lstrip(",").strip()
        if note:
            theme, note = _extract_theme(note)
            return {"page": page, "note": note, "theme": theme}
        return None

    # Pattern 2: "page <word-number> <note>"
    # Use word boundary and sort keys longest-first to avoid partial matches
    sorted_keys = sorted(WORD_NUMS.keys(), key=len, reverse=True)
    word_pattern = '|'.join(sorted_keys)
    word_num_match = re.match(
        r'(?:page|pg)[\s,]+((?:(?:' + word_pattern + r')(?:\s+(?:' + word_pattern + r'))*))[\s,]+(.+)',
        text,
        re.IGNORECASE
    )
    if word_num_match:
        num_str = word_num_match.group(1)
        page = words_to_number(num_str.lower())
        note = (word_num_match.group(2) or "").strip().lstrip(",").strip()
        if page and note:
            theme, note = _extract_theme(note)
            return {"page": page, "note": note, "theme": theme}

    return None


def extract_page_from_text(text: str) -> int | None:
    """Try to find any page mention in free text."""
    m = re.search(r'(?:page|pg)[\s,]+(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None
