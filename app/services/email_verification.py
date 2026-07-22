from html import escape
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models import AccountTokenPurpose, User
from app.services.account_tokens import issue_account_token
from app.services.email_sender import send_email


def build_verification_url(raw_token: str) -> str:
    separator = (
        "&"
        if "?" in settings.email_verification_frontend_url
        else "?"
    )

    query_string = urlencode({"token": raw_token})

    return (
        f"{settings.email_verification_frontend_url}"
        f"{separator}"
        f"{query_string}"
    )


def send_email_verification(
    database_session: Session,
    user: User,
) -> None:
    raw_token = issue_account_token(
        database_session,
        user_id=user.id,
        purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
        lifetime_minutes=(
            settings.email_verification_token_minutes
        ),
    )

    verification_url = build_verification_url(raw_token)

    subject = f"Verify your {settings.app_name} email address"

    text_content = (
        f"Welcome to {settings.app_name}.\n\n"
        "Use the following link to verify your email address:\n"
        f"{verification_url}\n\n"
        "If you did not create this account, you can ignore "
        "this message."
    )

    safe_application_name = escape(settings.app_name)
    safe_verification_url = escape(
        verification_url,
        quote=True,
    )

    html_content = f"""
    <html>
      <body>
        <h1>{safe_application_name}</h1>
        <p>Welcome to {safe_application_name}.</p>
        <p>
          Use the following link to verify your email address:
        </p>
        <p>
          <a href="{safe_verification_url}">
            Verify email address
          </a>
        </p>
        <p>
          If you did not create this account,
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