from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# --- File upload validation -------------------------------------------------
# Extensions that are safe to store and safe to serve back to a browser.
# Deliberately excludes executable/script-bearing formats (html, svg, js, etc.)
# to prevent stored-XSS or code execution via uploaded files served from
# MEDIA_URL on the same origin as the app.
SAFE_DOCUMENT_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'txt',
}
SAFE_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
SAFE_ATTACHMENT_EXTENSIONS = SAFE_DOCUMENT_EXTENSIONS | SAFE_IMAGE_EXTENSIONS


def validate_uploaded_file(uploaded_file, allowed_extensions=None, max_size_mb=None):
    """Raise ValidationError if the uploaded file's extension or size is not allowed.

    Used for uploads that are not routed through a ModelForm (and therefore
    would not otherwise run field validators), such as ticket/message
    attachments and department resource files.
    """
    if not uploaded_file:
        return
    allowed_extensions = allowed_extensions or SAFE_ATTACHMENT_EXTENSIONS
    max_size_mb = max_size_mb or getattr(settings, 'MAX_ATTACHMENT_SIZE_MB', 10)

    ext = uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Unsupported file type \".{ext}\". Allowed types: {', '.join(sorted(allowed_extensions))}."
        )

    max_bytes = max_size_mb * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(f"File is too large. Maximum size is {max_size_mb} MB.")


# --- Ticket list search / sort / pagination --------------------------------
# Shared by the dashboard, queue, department queue and CSV export views so
# the filtering rules only need to be changed in one place.
TICKET_SORT_FIELDS = {
    'ticket': 'ticket_number',
    'requester': 'requester__first_name',
    'subject': 'title',
    'priority': 'priority',
    'date': 'created_at',
}


def search_tickets(queryset, query):
    """Apply the free-text ticket search box filter."""
    query = (query or '').strip()
    if not query:
        return queryset
    from django.db.models import Q
    return queryset.filter(
        Q(ticket_number__icontains=query) |
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(requester__first_name__icontains=query) |
        Q(requester__last_name__icontains=query)
    )


def sort_tickets(queryset, sort_by, direction):
    """Apply column sorting, or the default status/recency ordering."""
    order_field = TICKET_SORT_FIELDS.get(sort_by)
    if order_field:
        if direction == 'desc':
            order_field = f'-{order_field}'
        return queryset.order_by(order_field)

    from django.db.models import Case, When, Value, IntegerField
    status_order = Case(
        When(status='open', then=Value(1)),
        When(status='in_progress', then=Value(2)),
        When(status='resolved', then=Value(3)),
        When(status='closed', then=Value(4)),
        output_field=IntegerField(),
    )
    return queryset.order_by(status_order, '-created_at')


def filter_and_sort_tickets(queryset, request):
    """Apply the standard search + sort query-string params to a ticket queryset."""
    queryset = search_tickets(queryset, request.GET.get('q'))
    queryset = sort_tickets(queryset, request.GET.get('sort', ''), request.GET.get('dir', 'asc'))
    return queryset


def paginate_tickets(queryset, request, per_page=25):
    """Paginate a ticket queryset, preserving the current page number from the request."""
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    return paginator.get_page(page_number)


def sanitize_csv_field(value):
    """Neutralise CSV/Excel formula injection ("CSV injection").

    If an exported field starts with a character Excel/Sheets treats as the
    start of a formula (=, +, -, @, tab, CR), prefix it with a leading
    apostrophe so it is opened as literal text instead of executed.
    """
    text = "" if value is None else str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text

def send_ticket_notification(ticket, is_new=True):
    """
    Sends an email to the Functional Reps (Team members) when a new ticket is assigned to them.
    """
    if not ticket.team:
        return # Unassigned, handled by Admin dashboard

    # Get all functional reps for this team
    reps = ticket.team.members.filter(role='functional_rep')
    recipient_list = [rep.email for rep in reps if rep.email]
    
    if not recipient_list:
        logger.warning(f"No functional reps with emails found for team {ticket.team.name}")
        return
        
    subject = f"[{ticket.ticket_number}] New Request: {ticket.title}"
    if not is_new:
        subject = f"Re: [{ticket.ticket_number}] {ticket.title}"

    message = f"Hello {ticket.team.name} Team,\n\n"
    if is_new:
        message += f"A new ticket has been assigned to your department by {ticket.requester.get_full_name() or ticket.requester.username}.\n\n"
        message += f"Details: {ticket.description}\n\n"
    else:
        message += f"There is an update on ticket {ticket.ticket_number}.\n\n"
        
    message += f"View it here: {settings.SITE_URL}/ticket/{ticket.id}/\n\n"
    message += "---\nReply to this email to add a comment to the ticket."
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def send_reply_to_requester(ticket_message):
    """
    Sends an email to the employee when a Functional Rep replies to their ticket.
    """
    ticket = ticket_message.ticket
    requester_email = ticket.requester.email
    
    if not requester_email:
        return
        
    subject = f"Re: [{ticket.ticket_number}] {ticket.title}"
    
    message = f"Hello {ticket.requester.first_name or ticket.requester.username},\n\n"
    message += f"{ticket_message.sender.get_full_name() or ticket_message.sender.username} has replied to your request:\n\n"
    message += f"\"{ticket_message.body}\"\n\n"
    message += f"View it here: {settings.SITE_URL}/ticket/{ticket.id}/\n\n"
    message += "---\nReply to this email to add a comment to the ticket."
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [requester_email],
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
