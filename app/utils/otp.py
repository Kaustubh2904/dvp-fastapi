import random
from typing import Tuple


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of specified length."""
    if length < 4:
        length = 4
    min_val = 10 ** (length - 1)
    max_val = 10**length - 1
    return str(random.randint(min_val, max_val))