from django.contrib import admin
from .models import Ticket, TicketMessage, Attachment, TicketLog

class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'title', 'team', 'status', 'priority', 'requester', 'assigned_agent', 'created_at')
    list_filter = ('team', 'status', 'priority')
    search_fields = ('ticket_number', 'title', 'requester__username')
    inlines = [TicketMessageInline, AttachmentInline]

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'sender', 'created_at', 'is_internal')
    list_filter = ('is_internal',)

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'file', 'uploaded_at')

@admin.register(TicketLog)
class TicketLogAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'action', 'actor', 'created_at')
    list_filter = ('action',)
    search_fields = ('ticket__ticket_number', 'details', 'actor__username')
    readonly_fields = ('ticket', 'actor', 'action', 'details', 'created_at')
