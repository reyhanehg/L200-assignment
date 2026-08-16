"""PII (Personally Identifiable Information) Redaction & Scrubbing Pipeline.

Provides regex-based token sanitization for emails, phone numbers, credit card numbers,
SSNs, API keys, and addresses across logging, tracing, and memory layers.
"""

import re
from typing import Any, Dict, List, Union

# Regex patterns for sensitive PII identification
API_KEY_PATTERN = re.compile(r"\bAIzaSy[A-Za-z0-9_-]+\b|\b(?:sk|api|key)-[A-Za-z0-9]+\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


class PIIScrubber:
    """Sanitizes strings and structured dictionaries by replacing PII with safe tokens."""

    @staticmethod
    def scrub_text(text: str) -> str:
        """Replace all PII occurrences in a text string with redaction placeholders."""
        if not isinstance(text, str):
            return text

        scrubbed = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)
        scrubbed = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", scrubbed)
        scrubbed = CREDIT_CARD_PATTERN.sub("[REDACTED_CREDIT_CARD]", scrubbed)
        scrubbed = SSN_PATTERN.sub("[REDACTED_SSN]", scrubbed)
        scrubbed = PHONE_PATTERN.sub("[REDACTED_PHONE]", scrubbed)
        scrubbed = IP_PATTERN.sub("[REDACTED_IP]", scrubbed)
        return scrubbed

    @classmethod
    def scrub_data(cls, data: Union[Dict, List, str, Any]) -> Any:
        """Recursively scrub PII from dictionaries, lists, and primitives."""
        if isinstance(data, str):
            return cls.scrub_text(data)
        elif isinstance(data, dict):
            return {k: cls.scrub_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.scrub_data(item) for item in data]
        return data
