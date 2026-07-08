import sys
import os

# Ensure backend folder is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import scrub_pii


def test_pii_scrubbing_emails():
    text = "Help, my email is admin@fifa.com. Emergency."
    scrubbed, stats = scrub_pii(text)
    assert "[REDACTED_EMAIL]" in scrubbed
    assert stats["emails"] == 1


def test_pii_scrubbing_phones():
    text = "Logistics phone number: +1 (555) 123-4567."
    scrubbed, stats = scrub_pii(text)
    assert "[REDACTED_PHONE]" in scrubbed
    assert stats["phones"] == 1


def test_pii_scrubbing_names():
    text = "Hello, my name is Alice Smith. Sitting in Section 102."
    scrubbed, stats = scrub_pii(text)
    assert "[REDACTED_NAME]" in scrubbed
    assert stats["names"] >= 1
