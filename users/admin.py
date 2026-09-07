from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from .models import User, Team

@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    fieldsets = DefaultUserAdmin.fieldsets + (
        ('Ticketing Info', {'fields': ('role', 'teams', 'ad_username')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'get_teams', 'is_staff')
    list_filter = ('role', 'teams', 'is_staff', 'is_superuser')

    def get_teams(self, obj):
        return ", ".join([t.name for t in obj.teams.all()])
    get_teams.short_description = 'Teams'

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
