from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.manage_users, name='manage_users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:pk>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:pk>/demote/', views.demote_user, name='demote_user'),
    path('departments/', views.manage_teams, name='manage_teams'),
    path('departments/<int:team_id>/edit/', views.edit_team, name='edit_team'),
    path('departments/<int:team_id>/delete/', views.delete_team, name='delete_team'),
    path('branding/', views.manage_branding, name='manage_branding'),
    path('profile/', views.profile_setup, name='profile_setup'),
    path('auth/microsoft/login/', views.microsoft_login, name='microsoft_login'),
    path('auth/microsoft/callback/', views.microsoft_callback, name='microsoft_callback'),
    path('role-selection/', views.role_selection, name='role_selection'),
    path('switch-role/<str:role>/', views.switch_role, name='switch_role'),
]
