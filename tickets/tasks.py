from celery import shared_task
from django.conf import settings
from django.db import transaction
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import re
import logging

from .models import Ticket, TicketMessage, TicketLog
from users.models import User

logger = logging.getLogger(__name__)


def _decode_header_value(value):
    if not value:
        return ''
    parts = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            try:
                parts.append(chunk.decode(encoding or 'utf-8', errors='replace'))
            except (LookupError, UnicodeError):
                parts.append(chunk.decode('utf-8', errors='replace'))
        else:
            parts.append(chunk)
    return ''.join(parts).strip()


def _extract_plain_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() != 'text/plain' or part.get_content_disposition() == 'attachment':
                continue
            payload = part.get_payload(decode=True)
            if payload is not None:
                charset = part.get_content_charset() or 'utf-8'
                return payload.decode(charset, errors='replace').strip()
        return ''
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ''
    charset = msg.get_content_charset() or 'utf-8'
    return payload.decode(charset, errors='replace').strip()


def _ticket_number(subject):
    match = re.search(r'\[(HR-\d+)\]', subject or '', re.IGNORECASE)
    return match.group(1).upper() if match else None


def _message_fingerprint(msg, ticket, sender, body):
    # Message-ID is stable across repeated IMAP polling; fall back to a small
    # deterministic signature when providers omit it.
    message_id = (msg.get('Message-ID') or '').strip()
    if message_id:
        return f'email:{message_id.lower()}'
    import hashlib
    raw = f'{ticket.pk}|{sender.pk}|{msg.get("Date", "")}|{body}'.encode('utf-8', errors='ignore')
    return 'email-hash:' + hashlib.sha256(raw).hexdigest()


def _already_imported(ticket, fingerprint):
    return ticket.logs.filter(action='Inbound Email Imported', details=fingerprint).exists()


@shared_task
def fetch_inbound_emails():
    """Import unread IMAP replies into existing tickets without duplicates."""
    host = getattr(settings, 'IMAP_HOST', '')
    user = getattr(settings, 'IMAP_USER', '')
    password = getattr(settings, 'IMAP_PASSWORD', '')
    folder = getattr(settings, 'IMAP_FOLDER', 'INBOX')
    if not all([host, user, password]):
        logger.info('IMAP is not configured; skipping inbound email fetch.')
        return 0

    imported = 0
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, timeout=30)
        mail.login(user, password)
        status, _ = mail.select(folder)
        if status != 'OK':
            raise RuntimeError(f'Could not select IMAP folder {folder!r}')

        status, data = mail.search(None, 'UNSEEN')
        if status != 'OK':
            raise RuntimeError('Could not search unread IMAP messages')

        for num in data[0].split():
            try:
                status, fetched = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue
                raw = next((part[1] for part in fetched if isinstance(part, tuple)), None)
                if not raw:
                    continue
                msg = email.message_from_bytes(raw)
                subject = _decode_header_value(msg.get('Subject'))
                ticket_number = _ticket_number(subject)
                if not ticket_number:
                    continue

                ticket = Ticket.objects.filter(ticket_number=ticket_number).first()
                if not ticket:
                    logger.warning('Inbound email references unknown ticket %s', ticket_number)
                    continue

                sender_email = parseaddr(msg.get('From', ''))[1].strip().lower()
                sender_user = User.objects.filter(email__iexact=sender_email).first()
                if not sender_user:
                    logger.warning('Unrecognized sender %s for ticket %s', sender_email, ticket_number)
                    continue

                body = _extract_plain_body(msg)
                if not body:
                    logger.info('Inbound email for %s has no plain-text body', ticket_number)
                    continue
                body = body.split('---', 1)[0].strip()
                fingerprint = _message_fingerprint(msg, ticket, sender_user, body)
                if _already_imported(ticket, fingerprint):
                    continue

                with transaction.atomic():
                    if _already_imported(ticket, fingerprint):
                        continue
                    TicketMessage.objects.create(
                        ticket=ticket,
                        sender=sender_user,
                        body=body,
                    )
                    TicketLog.objects.create(
                        ticket=ticket,
                        actor=sender_user,
                        action='Inbound Email Imported',
                        details=fingerprint,
                    )
                imported += 1
                # Mark the message read only after successful persistence.
                mail.store(num, '+FLAGS', r'\Seen')
            except Exception:
                logger.exception('Failed to import IMAP message %s', num)
    except Exception:
        logger.exception('IMAP fetch failed')
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass
    return imported


@shared_task
def enforce_business_rules():
    """Enforce SLA escalation and auto-close rules safely and idempotently."""
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    escalated = 0
    closed = 0

    for ticket in Ticket.objects.select_related('team').filter(
        status__in=['open', 'in_progress'], is_escalated=False, team__isnull=False
    ).iterator():
        if ticket.team.sla_days is not None and ticket.team.sla_days > 0 and now - ticket.updated_at > timedelta(days=ticket.team.sla_days):
            Ticket.objects.filter(pk=ticket.pk, is_escalated=False).update(is_escalated=True, updated_at=now)
            escalated += 1

    for ticket in Ticket.objects.select_related('team').filter(
        status='resolved', team__isnull=False
    ).iterator():
        if ticket.team.auto_close_days is not None and ticket.team.auto_close_days > 0 and now - ticket.updated_at > timedelta(days=ticket.team.auto_close_days):
            updated = Ticket.objects.filter(pk=ticket.pk, status='resolved').update(status='closed', closed_at=now, updated_at=now)
            closed += int(bool(updated))

    logger.info('Business rules complete: %s escalated, %s auto-closed', escalated, closed)
    return {'escalated': escalated, 'closed': closed}
