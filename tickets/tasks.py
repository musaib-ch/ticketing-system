from celery import shared_task
from django.conf import settings
import imaplib
import email
from email.header import decode_header
from .models import Ticket, TicketMessage
from users.models import User
import re
import logging

logger = logging.getLogger(__name__)

@shared_task
def fetch_inbound_emails():
    """
    Connects to the configured IMAP server, fetches unread emails,
    parses the ticket number from the subject, and creates a TicketMessage.
    """
    if not getattr(settings, 'IMAP_HOST', None):
        logger.warning("IMAP_HOST not configured. Skipping email fetch.")
        return

    try:
        mail = imaplib.IMAP4_SSL(settings.IMAP_HOST)
        mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        mail.select('inbox')
        
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            return
            
        for num in messages[0].split():
            status, data = mail.fetch(num, '(RFC822)')
            if status != 'OK':
                continue
                
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else 'utf-8')
                    
                    sender_email = msg.get("From")
                    # Extract email address between < >
                    email_match = re.search(r'<(.+?)>', sender_email)
                    if email_match:
                        sender_email = email_match.group(1)
                        
                    # Find ticket number in subject (e.g., [HR-0001])
                    ticket_match = re.search(r'\[(HR-\d+)\]', subject)
                    if not ticket_match:
                        continue
                        
                    ticket_number = ticket_match.group(1)
                    
                    try:
                        ticket = Ticket.objects.get(ticket_number=ticket_number)
                        sender_user = User.objects.filter(email=sender_email).first()
                        
                        if not sender_user:
                            logger.warning(f"Unrecognized sender {sender_email} for ticket {ticket_number}")
                            continue
                            
                        # Extract body (simplistic for plain text)
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                            
                        # Clean up email signatures/quotes (very basic approach)
                        body = body.split('---')[0].strip()
                        
                        # Create Message
                        TicketMessage.objects.create(
                            ticket=ticket,
                            sender=sender_user,
                            body=body
                        )
                    except Ticket.DoesNotExist:
                        logger.warning(f"Ticket {ticket_number} not found for inbound email.")
                        
    except Exception as e:
        logger.error(f"IMAP Fetch Error: {e}")

@shared_task
def enforce_business_rules():
    """
    Enforces SLA escalation and Auto-Close rules for tickets.
    Runs periodically.
    """
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()

    # 1. SLA Escalations (Open/In Progress tickets untouched by agent)
    open_tickets = Ticket.objects.filter(status__in=['open', 'in_progress'], is_escalated=False)
    for ticket in open_tickets:
        if ticket.team and ticket.team.sla_days:
            if (now - ticket.updated_at).total_seconds() > ticket.team.sla_days * 86400:
                ticket.is_escalated = True
                ticket.save()
                logger.info(f"SLA Breached - Escalated Ticket: {ticket.ticket_number}")
                
    # 2. Auto-Close (Resolved tickets untouched by employee)
    resolved_tickets = Ticket.objects.filter(status='resolved')
    for ticket in resolved_tickets:
        if ticket.team and ticket.team.auto_close_days:
            if (now - ticket.updated_at).total_seconds() > ticket.team.auto_close_days * 86400:
                ticket.status = 'closed'
                ticket.save()
                logger.info(f"Business Rule - Auto-Closed Ticket: {ticket.ticket_number}")
