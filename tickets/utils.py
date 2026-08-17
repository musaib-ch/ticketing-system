from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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
