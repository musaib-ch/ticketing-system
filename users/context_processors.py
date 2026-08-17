from django.conf import settings
from .models import Branding

def branding(request):
    user = getattr(request, 'user', None)
    can_switch_role = bool(
        user and user.is_authenticated and user.role in ('admin', 'functional_rep')
    )
    active_role = request.session.get('active_role') if can_switch_role else 'employee'
    is_employee_mode = active_role == 'employee'
    return {
        'branding': Branding.get_settings(),
        'DEBUG': settings.DEBUG,
        'active_role': active_role,
        'is_employee_mode': is_employee_mode,
        'is_agent_mode': can_switch_role and not is_employee_mode,
        'is_admin_agent_mode': bool(user and user.is_authenticated and user.role == 'admin' and not is_employee_mode),
        'can_switch_role': can_switch_role,
    }
