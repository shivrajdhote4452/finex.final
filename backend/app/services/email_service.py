"""Email delivery and transaction notification service for FinEx.

Handles email verification and password reset dispatch.
Supports real SMTP delivery when configured via environment variables,
and safe development logging + inspection queue when unconfigured.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Manages transactional email delivery for user authentication."""

    def __init__(self):
        self._sent_emails: List[Dict[str, Any]] = []
        self._test_mode: Optional[bool] = None

    def enable_test_mode(self) -> None:
        """Explicitly enable test mode to capture emails in memory for unit/integration tests."""
        self._test_mode = True

    def disable_test_mode(self) -> None:
        """Disable test mode and wipe any buffered test emails."""
        self._test_mode = False
        self._sent_emails.clear()

    def _is_test_mode(self) -> bool:
        """Check if test email capture is enabled."""
        if self._test_mode is not None:
            return self._test_mode
        settings = get_settings()
        env_val = getattr(settings, "ENVIRONMENT", "")
        return str(env_val).lower() in ("testing", "environment.testing")

    @property
    def sent_emails(self) -> List[Dict[str, Any]]:
        """Inspection buffer restricted strictly to explicit test execution."""
        if not self._is_test_mode():
            return []
        return self._sent_emails

    def clear_sent_emails(self) -> None:
        """Clear test inspection buffer."""
        self._sent_emails.clear()

    def get_last_email_for(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve most recent email dispatched to a specific recipient in test mode."""
        if not self._is_test_mode():
            return None
        normalized = email.strip().lower()
        for msg in reversed(self._sent_emails):
            if msg.get("to", "").strip().lower() == normalized:
                return msg
        return None

    async def send_verification_email(self, to_email: str, name: str, raw_token: str) -> Dict[str, Any]:
        """Dispatch account verification email with single-use verification link."""
        settings = get_settings()
        base_url = settings.FRONTEND_URL.rstrip("/")
        verification_link = f"{base_url}/#verify-email?token={raw_token}"

        subject = "Verify your email address for FinEx"
        text_body = (
            f"Hello {name},\n\n"
            f"Thank you for joining FinEx - Financial Excellence.\n\n"
            f"To complete your registration, please verify your email address by opening the following link:\n"
            f"{verification_link}\n\n"
            f"This link will expire in {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours.\n\n"
            f"If you did not create a FinEx account, you can safely ignore this email.\n\n"
            f"— The FinEx Team"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #050505; color: #FFFFFF; padding: 32px 16px;">
  <div style="max-width: 560px; margin: 0 auto; background: #0E0E10; border: 1px solid #1F1F23; border-radius: 8px; padding: 32px;">
    <div style="margin-bottom: 24px;">
      <span style="font-size: 24px; font-weight: 800; color: #FFFFFF;">Fin<span style="color: #F29A60;">Ex</span></span>
      <span style="font-size: 11px; color: #71717A; margin-left: 8px; font-family: monospace;">VERIFICATION</span>
    </div>
    <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 12px; color: #FFFFFF;">Confirm your email address</h2>
    <p style="color: #A1A1AA; font-size: 14px; line-height: 1.6; margin-bottom: 24px;">
      Hello {name}, welcome to FinEx. Please click the button below to verify your email address and activate your account.
    </p>
    <div style="margin: 28px 0;">
      <a href="{verification_link}" style="background-color: #F29A60; color: #000000; font-weight: 700; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 4px; display: inline-block;">
        Verify Email Address →
      </a>
    </div>
    <p style="color: #71717A; font-size: 12px; line-height: 1.5; margin-top: 24px;">
      If the button does not work, copy and paste this link into your browser:<br/>
      <a href="{verification_link}" style="color: #F29A60; word-break: break-all;">{verification_link}</a>
    </p>
    <div style="border-top: 1px solid #1F1F23; margin-top: 28px; padding-top: 16px; font-size: 11px; color: #52525B;">
      This link is valid for {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours. If you did not create a FinEx account, no further action is required.
    </div>
  </div>
</body>
</html>"""

        return await self._dispatch(
            to_email=to_email,
            subject=subject,
            text_content=text_body,
            html_content=html_body,
            metadata={"token": raw_token, "link": verification_link, "type": "verification"},
        )

    async def send_password_reset_email(self, to_email: str, name: str, raw_token: str) -> Dict[str, Any]:
        """Dispatch single-use password reset email."""
        settings = get_settings()
        base_url = settings.FRONTEND_URL.rstrip("/")
        reset_link = f"{base_url}/#reset-password?token={raw_token}"

        subject = "Reset your FinEx account password"
        text_body = (
            f"Hello {name},\n\n"
            f"We received a request to reset your password for your FinEx account.\n\n"
            f"You can choose a new password by visiting:\n"
            f"{reset_link}\n\n"
            f"This link will expire in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes and can only be used once.\n\n"
            f"If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.\n\n"
            f"— The FinEx Team"
        )

        html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #050505; color: #FFFFFF; padding: 32px 16px;">
  <div style="max-width: 560px; margin: 0 auto; background: #0E0E10; border: 1px solid #1F1F23; border-radius: 8px; padding: 32px;">
    <div style="margin-bottom: 24px;">
      <span style="font-size: 24px; font-weight: 800; color: #FFFFFF;">Fin<span style="color: #F29A60;">Ex</span></span>
      <span style="font-size: 11px; color: #71717A; margin-left: 8px; font-family: monospace;">SECURITY</span>
    </div>
    <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 12px; color: #FFFFFF;">Reset your password</h2>
    <p style="color: #A1A1AA; font-size: 14px; line-height: 1.6; margin-bottom: 24px;">
      Hello {name}, we received a request to reset your FinEx password. Click the button below to set a new password.
    </p>
    <div style="margin: 28px 0;">
      <a href="{reset_link}" style="background-color: #F29A60; color: #000000; font-weight: 700; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 4px; display: inline-block;">
        Reset Password →
      </a>
    </div>
    <p style="color: #71717A; font-size: 12px; line-height: 1.5; margin-top: 24px;">
      If the button does not work, copy and paste this link into your browser:<br/>
      <a href="{reset_link}" style="color: #F29A60; word-break: break-all;">{reset_link}</a>
    </p>
    <div style="border-top: 1px solid #1F1F23; margin-top: 28px; padding-top: 16px; font-size: 11px; color: #52525B;">
      This link is single-use and expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes. If you did not make this request, your account remains secure.
    </div>
  </div>
</body>
</html>"""

        return await self._dispatch(
            to_email=to_email,
            subject=subject,
            text_content=text_body,
            html_content=html_body,
            metadata={"token": raw_token, "link": reset_link, "type": "reset"},
        )

    async def send_existing_account_notification(self, to_email: str, name: str) -> Dict[str, Any]:
        """Dispatch notification to an existing registered user that a duplicate registration attempt occurred."""
        settings = get_settings()
        base_url = settings.FRONTEND_URL.rstrip("/")
        signin_link = f"{base_url}/#signin"
        reset_link = f"{base_url}/#forgot"

        subject = "FinEx Account Notice: Registration Attempt"
        text_body = (
            f"Hello {name},\n\n"
            f"We received a request to create a new FinEx account using your email address ({to_email}).\n\n"
            f"Because you already have a FinEx account, no new account was created and your credentials were not changed.\n\n"
            f"If you made this request, you can sign in directly here:\n{signin_link}\n\n"
            f"If you forgot your password, you can reset it here:\n{reset_link}\n\n"
            f"If you did not make this request, you can safely ignore this email; your account and credentials remain secure.\n\n"
            f"— The FinEx Team"
        )
        html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #050505; color: #FFFFFF; padding: 32px 16px;">
  <div style="max-width: 560px; margin: 0 auto; background: #0E0E10; border: 1px solid #1F1F23; border-radius: 8px; padding: 32px;">
    <div style="margin-bottom: 24px;">
      <span style="font-size: 24px; font-weight: 800; color: #FFFFFF;">Fin<span style="color: #F29A60;">Ex</span></span>
      <span style="font-size: 11px; color: #71717A; margin-left: 8px; font-family: monospace;">NOTICE</span>
    </div>
    <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 12px; color: #FFFFFF;">FinEx Account Notice</h2>
    <p style="color: #A1A1AA; font-size: 14px; line-height: 1.6; margin-bottom: 24px;">
      Hello {name}, we received a request to register a new account using your email address. Because you already have a registered account, no new account was created and your credentials were not changed.
    </p>
    <div style="margin: 28px 0; display: flex; gap: 12px;">
      <a href="{signin_link}" style="background-color: #F29A60; color: #000000; font-weight: 700; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 4px; display: inline-block;">
        Sign In to Your Account →
      </a>
    </div>
    <p style="color: #71717A; font-size: 12px; line-height: 1.5; margin-top: 24px;">
      If you forgot your password, you can request a reset link at: <a href="{reset_link}" style="color: #F29A60;">{reset_link}</a>
    </p>
    <div style="border-top: 1px solid #1F1F23; margin-top: 28px; padding-top: 16px; font-size: 11px; color: #52525B;">
      If you did not make this request, you can safely ignore this email. Your existing FinEx account remains secure.
    </div>
  </div>
</body>
</html>"""

        return await self._dispatch(
            to_email=to_email,
            subject=subject,
            text_content=text_body,
            html_content=html_body,
            metadata={"type": "existing_account_notice"},
        )

    async def _dispatch(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch email via real SMTP if configured; otherwise safely handle test capture or fail closed."""
        settings = get_settings()
        clean_to = to_email.strip().lower()
        is_test = self._is_test_mode()

        # In explicitly configured test mode only: capture minimal test metadata for assertion
        if is_test:
            self._sent_emails.append(
                {
                    "to": clean_to,
                    "subject": subject,
                    "token": (metadata or {}).get("token"),
                    "link": (metadata or {}).get("link"),
                    "type": (metadata or {}).get("type"),
                    "metadata": metadata or {},
                }
            )

        if settings.SMTP_HOST:
            try:
                await asyncio.to_thread(
                    self._send_smtp_sync,
                    smtp_host=settings.SMTP_HOST,
                    smtp_port=settings.SMTP_PORT,
                    smtp_user=settings.SMTP_USER,
                    smtp_password=settings.SMTP_PASSWORD,
                    use_tls=settings.SMTP_USE_TLS,
                    from_email=settings.EMAILS_FROM_EMAIL,
                    from_name=settings.EMAILS_FROM_NAME,
                    to_email=clean_to,
                    subject=subject,
                    text_content=text_content,
                    html_content=html_content,
                )
                logger.info("Successfully delivered email to %s via SMTP (%s)", clean_to, settings.SMTP_HOST)
                return {"status": "delivered", "delivered": True, "to": clean_to, "provider": "smtp", "error": None}
            except Exception as e:
                logger.error("Failed to send email to %s via SMTP: %s", clean_to, str(e))
                return {"status": "failed", "delivered": False, "to": clean_to, "provider": "smtp", "error": str(e)}

        # SMTP is NOT configured
        if is_test:
            logger.debug("Transactional email captured in test buffer for %s", clean_to)
            return {
                "status": "test_captured",
                "delivered": False,
                "to": clean_to,
                "provider": "test_buffer",
                "error": None,
            }

        # In production / non-test environment without SMTP:
        # Never log tokens, action links, or email bodies.
        # Explicitly report delivery as unavailable.
        logger.warning(
            "Transactional email delivery unavailable: SMTP is not configured. Email to %s ('%s') was not sent.",
            clean_to,
            subject,
        )
        return {
            "status": "smtp_not_configured",
            "delivered": False,
            "to": clean_to,
            "provider": "none",
            "error": "SMTP server not configured",
        }

    @staticmethod
    def _send_smtp_sync(
        smtp_host: str,
        smtp_port: int,
        smtp_user: Optional[str],
        smtp_password: Optional[str],
        use_tls: bool,
        from_email: str,
        from_name: str,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: str,
    ) -> None:
        """Synchronous SMTP worker invoked via asyncio.to_thread."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email

        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())


email_service = EmailService()
