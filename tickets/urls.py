from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('queue/', views.queue, name='queue'),
    path('department-queue/', views.department_queue, name='department_queue'),
    path('export/', views.export_tickets_csv, name='export_tickets_csv'),
    path('submit/', views.submit_ticket, name='submit_ticket'),
    path('ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('kb/', views.knowledge_base, name='knowledge_base'),
    path('kb/<int:pk>/', views.article_detail, name='article_detail'),
    path('kb/manage/', views.manage_kb, name='manage_kb'),
    path('kb/add/', views.edit_article, name='add_article'),
    path('kb/<int:pk>/edit/', views.edit_article, name='edit_article'),
    path('kb/<int:pk>/delete/', views.delete_article, name='delete_article'),
    path('api/v1/dashboard-prefs/', views.update_dashboard_prefs, name='update_dashboard_prefs'),
]
