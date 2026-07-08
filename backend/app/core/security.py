import re
from typing import Tuple, Dict

# Regex Patterns for PII
EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_REGEX = re.compile(r"\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

# Name pattern regex (matches "my name is X", "I am X", "name: X" in a case-insensitive manner)
NAME_PATTERNS = [
    re.compile(r"(?i)\bmy name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"),
    re.compile(r"(?i)\bi\s+am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"),
    re.compile(r"(?i)\bname\s*:\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)"),
]


def scrub_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Scrubs PII (Emails, Phone Numbers, Credit Cards, and Names) from user inputs.
    Returns the scrubbed text and a dictionary containing counts of scrubbed items.
    """
    scrub_stats = {"emails": 0, "phones": 0, "cards": 0, "names": 0}

    # 1. Scrub Emails
    emails_found = EMAIL_REGEX.findall(text)
    if emails_found:
        scrub_stats["emails"] = len(emails_found)
        text = EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)

    # 2. Scrub Phone Numbers
    phones_found = PHONE_REGEX.findall(text)
    if phones_found:
        scrub_stats["phones"] = len(phones_found)
        text = PHONE_REGEX.sub("[REDACTED_PHONE]", text)

    # 3. Scrub Credit Cards
    cards_found = CREDIT_CARD_REGEX.findall(text)
    if cards_found:
        scrub_stats["cards"] = len(cards_found)
        text = CREDIT_CARD_REGEX.sub("[REDACTED_CARD]", text)

    # 4. Scrub Names matching common prefix patterns
    for pattern in NAME_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            scrub_stats["names"] += len(matches)
            # Replace only the captured name portion to preserve query syntax
            for match in matches:
                # We build a regex specifically for this match to avoid partial string replacements
                text = re.sub(re.escape(match), "[REDACTED_NAME]", text)

    return text, scrub_stats
