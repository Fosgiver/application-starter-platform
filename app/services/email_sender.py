import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.settings import settings


class EmailDeliveryError(Exception):
    pass


def create_smtp_connection() -> smtplib.SMTP:
    if settings.smtp_security == "ssl":
        return smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
            context=ssl.create_default_context(),
        )

    return smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=15,
    )


def send_email(
    recipient_email: str,
    subject: str,
    text_content: str,
    html_content: str | None = None,
) -> None:
    if not settings.smtp_enabled:
        if settings.environment == "development":
            print()
            print("----- DEVELOPMENT EMAIL -----")
            print(f"To: {recipient_email}")
            print(f"Subject: {subject}")
            print(text_content)
            print("----- END DEVELOPMENT EMAIL -----")
            print()
            return

        raise EmailDeliveryError(
            "SMTP is disabled outside the development environment."
        )

    if settings.smtp_host is None:
        raise EmailDeliveryError(
            "SMTP host is not configured."
        )

    if settings.smtp_sender_email is None:
        raise EmailDeliveryError(
            "SMTP sender email is not configured."
        )

    message = EmailMessage()

    message["From"] = formataddr(
        (
            settings.smtp_sender_name,
            settings.smtp_sender_email,
        )
    )
    message["To"] = recipient_email
    message["Subject"] = subject

    message.set_content(text_content)

    if html_content is not None:
        message.add_alternative(
            html_content,
            subtype="html",
        )

    try:
        with create_smtp_connection() as smtp_server:
            smtp_server.ehlo()

            if settings.smtp_security == "starttls":
                smtp_server.starttls(
                    context=ssl.create_default_context()
                )
                smtp_server.ehlo()

            if settings.smtp_username is not None:
                if settings.smtp_password is None:
                    raise EmailDeliveryError(
                        "SMTP password is not configured."
                    )

                smtp_server.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )

            smtp_server.send_message(message)

    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError(
            "The email could not be delivered."
        ) from error