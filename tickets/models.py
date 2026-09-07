from django.db import models
from django.conf import settings
from users.models import Team
from .utils import SAFE_ATTACHMENT_EXTENSIONS, validate_uploaded_file

User = settings.AUTH_USER_MODEL


def validate_attachment_file(uploaded_file):
    """Model-level type/size guard, runs automatically for any ModelForm upload."""
    validate_uploaded_file(uploaded_file, allowed_extensions=SAFE_ATTACHMENT_EXTENSIONS)


class Ticket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    ticket_number = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    query_relevance = models.CharField(max_length=100, blank=True)
    is_escalated = models.BooleanField(default=False)
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_created')
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.IntegerField(default=0)
    has_unread_messages = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            import json
            for t in Team.objects.exclude(workflow_rules="[]").exclude(workflow_rules=""):
                try:
                    rules = json.loads(t.workflow_rules)
                    for rule in rules:
                        keyword = rule.get('keyword', '').lower()
                        if keyword and (keyword in self.title.lower() or keyword in self.description.lower()):
                            if not self.team:
                                self.team = t
                            if rule.get('priority'):
                                self.priority = rule['priority']
                            break
                except Exception:
                    pass

        if not self.ticket_number:
            import uuid
            self.ticket_number = str(uuid.uuid4())[:20]
            super().save(*args, **kwargs)
            self.ticket_number = f"HR-{self.id:02d}"
            kwargs.pop('force_insert', None)
            kwargs['force_update'] = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.title}"


class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.sender} on {self.ticket}"


class TicketLog(models.Model):
    """Immutable audit entries for routing and ticket workflow changes."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='logs')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_log_entries')
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket.ticket_number}: {self.action}"


class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True)
    message = models.ForeignKey(TicketMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name='attachments')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name='resource_files')
    file = models.FileField(upload_to='attachments/', validators=[validate_attachment_file])
    uploaded_at = models.DateTimeField(auto_now_add=True)


import os


class KnowledgeArticle(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    file = models.FileField(upload_to='kb_files/', null=True, blank=True, validators=[validate_attachment_file])
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='articles')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='articles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    @property
    def filename(self):
        if self.file:
            return os.path.basename(self.file.name)
        return ""

    @property
    def file_extension(self):
        if self.file:
            return os.path.splitext(self.file.name)[1].lower().replace('.', '')
        return ""

    @property
    def is_image(self):
        return self.file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']

    @property
    def is_pdf(self):
        return self.file_extension == 'pdf'

    @property
    def is_word(self):
        return self.file_extension in ['doc', 'docx']

    @property
    def is_ppt(self):
        return self.file_extension in ['ppt', 'pptx']
