"""Outgoing email helpers (verification & password reset) via fastapi-mail."""

from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors

from src.conf.config import settings
from src.services.auth import auth_service

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / "templates",
)


async def send_verification_email(email: str, username: str, base_url: str) -> None:
    """Send an email-verification message with a tokenized confirmation link."""
    try:
        token = auth_service.create_email_token({"sub": email})
        message = MessageSchema(
            subject="Confirm your email",
            recipients=[email],
            template_body={"host": base_url, "username": username, "token": token},
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="verify_email.html")
    except ConnectionErrors as err:
        print(f"Email send failed: {err}")


async def send_reset_password_email(email: str, username: str, base_url: str) -> None:
    """Send a password-reset message with a tokenized reset link."""
    try:
        token = auth_service.create_reset_token({"sub": email})
        message = MessageSchema(
            subject="Reset your password",
            recipients=[email],
            template_body={"host": base_url, "username": username, "token": token},
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="reset_password.html")
    except ConnectionErrors as err:
        print(f"Email send failed: {err}")
