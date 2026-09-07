from rest_framework import serializers
from .models import Ticket, TicketMessage, Attachment
from users.serializers import UserSerializer, TeamSerializer


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'file', 'uploaded_at']


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'sender', 'sender_name', 'body', 'is_internal', 'created_at', 'attachments']


class TicketSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.get_full_name', read_only=True)
    assigned_agent_name = serializers.CharField(source='assigned_agent.get_full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_number', 'title', 'description', 'priority', 'status', 'query_relevance',
            'requester', 'requester_name', 'assigned_agent', 'assigned_agent_name', 'team', 'team_name',
            'created_at', 'updated_at', 'resolved_at', 'closed_at'
        ]
        read_only_fields = fields
