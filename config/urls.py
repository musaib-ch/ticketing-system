from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from tickets.api import TicketViewSet
from users.api import UserViewSet, TeamViewSet

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'users', UserViewSet, basename='user')
router.register(r'departments', TeamViewSet, basename='team')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('accounts/', include('django.contrib.auth.urls')),
    path('manage/', include('users.urls')),
    path('', include('tickets.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
