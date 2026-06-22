import re
from typing import Optional


def validate_email(email: str) -> bool:
    """Basic email format validation."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number (10-15 digits, optional + prefix)."""
    pattern = r"^\+?[1-9]\d{9,14}$"
    return bool(re.match(pattern, phone))


def validate_gst(gst_number: str) -> bool:
    """Basic GST number format validation (15 chars: XX0000XXXXX0X0X)."""
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gst_number))


def validate_pan(pan_number: str) -> bool:
    """Basic PAN card format validation (10 chars: AAAAA9999A)."""
    pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    return bool(re.match(pattern, pan_number))