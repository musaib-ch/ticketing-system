"""Shared role-based access control decorators.

Centralising these means every "staff-only" or "admin-only" view enforces
the same rule and fails the same way: anonymous visitors are sent to the
login page, and authenticated users who lack the required role get a
straightforward HTTP 403 instead of being silently redirected (which is
confusing for the user and can look like a bug/redirect loop).
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Restrict a view to authenticated users whose ``role`` is in ``roles``."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def admin_required(view_func):
    """Admins only."""
    return role_required('admin')(view_func)


def staff_role_required(view_func):
    """Admins and functional reps (i.e. anyone with an agent-side role)."""
    return role_required('admin', 'functional_rep')(view_func)


def superuser_required(view_func):
    """Superusers only (used for portal-wide branding settings)."""
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped
