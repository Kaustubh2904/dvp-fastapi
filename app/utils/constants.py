# Pagination defaults
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# Subscription plans
SUBSCRIPTION_PLANS = {
    "FREE": {"employee_limit": 10, "price_cents": 0, "trial_days": 14},
    "BASIC": {"employee_limit": 50, "price_cents": 9900, "trial_days": 14},
    "PRO": {"employee_limit": 200, "price_cents": 29900, "trial_days": 14},
    "PREMIUM": {"employee_limit": 1000, "price_cents": 99900, "trial_days": 14},
    "CUSTOM": {"employee_limit": 5000, "price_cents": 0, "trial_days": 0},
}

# Document types allowed
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}

# Max file size (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024