# Pagination defaults
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

# Subscription plans
SUBSCRIPTION_PLANS = {
    "FREE": {"employee_limit": 10, "price": 0},
    "BASIC": {"employee_limit": 50, "price": 99},
    "PRO": {"employee_limit": 200, "price": 299},
    "ENTERPRISE": {"employee_limit": 1000, "price": 999},
}

# Document types allowed
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}

# Max file size (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024