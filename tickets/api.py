from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.cache import cache
from .models import Ticket
from .serializers import TicketSerializer


class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API mirroring the same access rules as the web queue views."""
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Ticket.objects.all()
        if user.role == 'functional_rep' and user.teams.exists():
            return Ticket.objects.filter(team__in=user.teams.all())
        return Ticket.objects.filter(requester=user)

    @action(detail=True, methods=['post'])
    def viewing(self, request, pk=None):
        ticket = self.get_object()
        user_id = request.user.id
        user_name = request.user.get_full_name() or request.user.username
        cache_key = f"ticket_viewers_{ticket.id}"
        viewers = cache.get(cache_key, {})
        import time
        current_time = time.time()
        viewers[user_id] = {'name': user_name, 'last_seen': current_time}
        active_viewers = {
            uid: data for uid, data in viewers.items()
            if current_time - data['last_seen'] < 20
        }
        cache.set(cache_key, active_viewers, 60)
        others = [data['name'] for uid, data in active_viewers.items() if uid != user_id]
        return Response({'viewers': others})
