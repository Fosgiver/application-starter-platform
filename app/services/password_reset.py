from html import escape
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models import AccountTokenPurpose, User
from app.services.account_tokens import issue_account_token
from app.services.email_sender import send_email


def build_password_reset_url(raw_token: str) -> str:
    separator = (
        "&"
        if "?" in settings.password_reset_frontend_url
        else "?"
    )

    query_string = urlencode({"token": raw_token})

    return (
        f"{settings.password_reset_frontend_url}"
        f"{separator}"
        f"{query_string}"
    )


def send_password_reset(
    database_session: Session,
    user: User,
) -> None:
    raw_token = issue_account_token(
        database_session,
        user_id=user.id,
        purpose=AccountTokenPurpose.PASSWORD_RESET,
        lifetime_minutes=settings.password_reset_token_minutes,
    )

    password_reset_url = build_password_reset_url(raw_token)

    subject = f"Reset your {settings.app_name} password"

    text_content = (
        f"We received a request to reset your "
        f"{settings.app_name} password.\n\n"
        "Use the following link to choose a new password:\n"
        f"{password_reset_url}\n\n"
        f"This link expires in "
        f"{settings.password_reset_token_minutes} minutes.\n\n"
        "If you did not request a password reset, "
        "you can ignore this message."
    )

    safe_application_name = escape(settings.app_name)
    safe_password_reset_url = escape(
        password_reset_url,
        quote=True,
    )

    html_content = f"""
    <html>
      <body>
        <h1>{safe_application_name}</h1>
        <p>
          We received a request to reset your
          {safe_application_name} password.
        </p>
        <p>
          Use the following link to choose a new password:
        </p>
        <p>
          <a href="{safe_password_reset_url}">
            Reset password
          </a>
        </p>
        <p>
          This link expires in
          {settings.password_reset_token_minutes} minutes.
        </p>
        <p>
          If you did not request a password reset,
          you can ignore this message.
        </p>
      </body>
    </html>
    """

    send_email(
        recipient_email=user.email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
    )