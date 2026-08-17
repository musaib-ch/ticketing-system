"""Utilities for sending email, respecting SmtpSettings if enabled."""

from django.core.mail import get_connection, EmailMessage


def get_email_connection():
    """Return a mail connection using SmtpSettings overrides when enabled.

    Falls back to Django's default backend (environment variables) if
    SmtpSettings is disabled or the host is blank.
    """
    try:
        from users.models import SmtpSettings
        smtp = SmtpSettings.get_settings()
        if smtp.enabled and smtp.host:
            return get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=smtp.host,
                port=smtp.port,
                username=smtp.username,
                password=smtp.password,
                use_tls=smtp.use_tls,
            )
    except Exception:
        pass
    return get_connection()


def send_mail_with_settings(subject, body, to, from_email=None, html_message=None):
    """Send a single email respecting the portal SMTP settings.

    Args:
        subject (str): Email subject.
        body (str): Plain-text body.
        to (list[str]): Recipient addresses.
        from_email (str | None): Override sender (defaults to SmtpSettings.from_email
            or settings.DEFAULT_FROM_EMAIL).
        html_message (str | None): Optional HTML body.
    """
    from django.conf import settings as django_settings

    if from_email is None:
        try:
            from users.models import SmtpSettings
            smtp = SmtpSettings.get_settings()
            from_email = smtp.from_email if smtp.enabled and smtp.from_email else django_settings.DEFAULT_FROM_EMAIL
        except Exception:
            from_email = django_settings.DEFAULT_FROM_EMAIL

    connection = get_email_connection()
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=to,
        connection=connection,
    )
    if html_message:
        email.content_subtype = 'html'
        email.body = html_message
    email.send(fail_silently=False)
