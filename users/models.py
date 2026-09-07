from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


def validate_branding_image(uploaded_file):
    """Restrict branding uploads to safe, reasonably small image files."""
    from django.conf import settings
    ext = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if ext not in allowed:
        raise ValidationError(f"Unsupported image type \".{ext}\". Allowed types: {', '.join(sorted(allowed))}.")
    max_mb = getattr(settings, 'MAX_IMAGE_SIZE_MB', 5)
    if uploaded_file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Image is too large. Maximum size is {max_mb} MB.")


class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    query_categories = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of categories (e.g., Policy, CSR)")
    sla_days = models.IntegerField(default=1, help_text="Target resolution time in days")
    auto_close_days = models.IntegerField(default=3, help_text="Days after resolved before auto-close")
    canned_responses = models.TextField(blank=True, default="[]", help_text="JSON array of canned responses")
    workflow_rules = models.TextField(blank=True, default="[]", help_text="JSON array of workflow rules (e.g. [{'keyword': 'payroll', 'priority': 'urgent'}])")

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('functional_rep', 'Functional Representative'),
        ('employee', 'Employee'),
    ]
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('away', 'Away'),
        ('offline', 'Offline'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    teams = models.ManyToManyField(Team, blank=True, related_name='members')
    dashboard_prefs = models.TextField(blank=True, default='{}', help_text="JSON preferences for dashboard widgets")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online')
    ad_username = models.CharField(max_length=100, blank=True)
    employee_number = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=100, blank=True)


Team.add_to_class('manager', models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_teams'))


class Branding(models.Model):
    portal_name = models.CharField(max_length=100, default='HR Servicedesk')
    primary_color = models.CharField(max_length=20, default='#4f46e5')
    secondary_color = models.CharField(max_length=20, default='#14b8a6')
    chart_color_1 = models.CharField(max_length=20, default='#4f46e5')
    chart_color_2 = models.CharField(max_length=20, default='#14b8a6')
    chart_color_3 = models.CharField(max_length=20, default='#f59e0b')
    chart_color_4 = models.CharField(max_length=20, default='#ef4444')
    chart_color_5 = models.CharField(max_length=20, default='#8b5cf6')
    logo = models.ImageField(upload_to='branding/', null=True, blank=True, validators=[validate_branding_image])
    background_image = models.ImageField(upload_to='branding/', null=True, blank=True, validators=[validate_branding_image])
    ticket_reopen_window_days = models.IntegerField(default=15)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def primary_rgb(self):
        h = self.primary_color.lstrip('#')
        if len(h) == 6:
            return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
        return "79, 70, 229"

    def accent_rgb(self):
        h = self.secondary_color.lstrip('#')
        if len(h) == 6:
            return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
        return "20, 184, 166"
