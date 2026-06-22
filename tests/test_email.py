"""Unit tests for the email service (FastMail stubbed)."""

from unittest.mock import AsyncMock, patch

from src.services import email


async def test_send_verification_email():
    with patch.object(email, "FastMail") as fm:
        fm.return_value.send_message = AsyncMock()
        await email.send_verification_email("a@x.com", "al", "http://host")
        fm.return_value.send_message.assert_awaited_once()


async def test_send_reset_password_email():
    with patch.object(email, "FastMail") as fm:
        fm.return_value.send_message = AsyncMock()
        await email.send_reset_password_email("a@x.com", "al", "http://host")
        fm.return_value.send_message.assert_awaited_once()
