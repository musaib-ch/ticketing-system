import imaplib
import email
import os
import re
from email.header import decode_header
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tickets.models import Ticket, TicketMessage

User = get_user_model()

class Command(BaseCommand):
    help = 'Fetches emails from IMAP and converts them to tickets/messages'

    def handle(self, *args, **options):
        # 1. Get IMAP credentials from Environment Variables
        username = os.environ.get('IMAP_USER')
        password = os.environ.get('IMAP_PASSWORD')
        server = os.environ.get('IMAP_SERVER')
        
        if not all([username, password, server]):
            self.stdout.write(self.style.ERROR("IMAP environment variables missing (IMAP_USER, IMAP_PASSWORD, IMAP_SERVER)."))
            return
            
        try:
            # 2. Connect to server
            mail = imaplib.IMAP4_SSL(server)
            mail.login(username, password)
            mail.select("inbox")
            
            # 3. Search for unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                self.stdout.write(self.style.ERROR("Could not search emails."))
                return
                
            email_ids = messages[0].split()
            if not email_ids:
                self.stdout.write(self.style.SUCCESS("No new emails."))
                return
                
            for e_id in email_ids:
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                            
                        from_ = msg.get("From")
                        email_address = re.search(r'[\w\.-]+@[\w\.-]+', from_).group(0)
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    try:
                                        body = part.get_payload(decode=True).decode()
                                        break
                                    except Exception:
                                        pass
                        else:
                            body = msg.get_payload(decode=True).decode()
                            
                        # Find User or create one
                        user, created = User.objects.get_or_create(username=email_address, defaults={
                            'email': email_address,
                            'role': 'employee',
                        })
                        
                        # Match to existing ticket?
                        ticket_match = re.search(r'\[(HR-\d+)\]', subject)
                        if ticket_match:
                            t_num = ticket_match.group(1)
                            try:
                                ticket = Ticket.objects.get(ticket_number=t_num)
                                TicketMessage.objects.create(
                                    ticket=ticket,
                                    sender=user,
                                    body=body
                                )
                                self.stdout.write(self.style.SUCCESS(f"Added message to {t_num}"))
                            except Ticket.DoesNotExist:
                                ticket = Ticket.objects.create(
                                    title=subject,
                                    description=body,
                                    requester=user
                                )
                                self.stdout.write(self.style.SUCCESS(f"Created new ticket {ticket.ticket_number} (failed match)"))
                        else:
                            ticket = Ticket.objects.create(
                                title=subject,
                                description=body,
                                requester=user
                            )
                            self.stdout.write(self.style.SUCCESS(f"Created new ticket {ticket.ticket_number}"))
                            
            mail.logout()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching emails: {e}"))
