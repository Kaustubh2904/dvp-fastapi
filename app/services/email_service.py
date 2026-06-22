import sys


class EmailService:
    """
    Mock email service for development.
    In production, replace with actual SMTP/SES integration.
    """

    @staticmethod
    async def send_email(to: str, subject: str, body: str) -> None:
        message = f"""
        ==================================================
        EMAIL DISPATCH (SIMULATED):
        To: {to}
        Subject: {subject}
        Body: {body}
        ==================================================
        """
        print(message, file=sys.stderr)


email_service = EmailService()