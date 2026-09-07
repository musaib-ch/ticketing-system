from django.core.management.base import BaseCommand
from tickets.tasks import fetch_inbound_emails


class Command(BaseCommand):
    help = 'Fetch unread inbound ticket emails using the configured IMAP settings.'

    def handle(self, *args, **options):
        imported = fetch_inbound_emails()
        self.stdout.write(self.style.SUCCESS(f'Inbound email fetch complete. Imported {imported} message(s).'))
