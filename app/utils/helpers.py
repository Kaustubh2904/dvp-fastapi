import secrets
from typing import Any


def generate_unique_code(length: int = 12) -> str:
    """Generate a cryptographically secure random code."""
    return secrets.token_hex(length // 2 + 1)[:length]


def generate_employee_code(company_id: int, seq: int) -> str:
    """Generate a formatted employee code."""
    return f"EMP-{company_id:04d}-{seq:05d}"


def truncate_string(value: str, max_length: int = 100) -> str:
    """Truncate a string to a max length."""
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."