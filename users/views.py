from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from .models import User, Team, SmtpSettings
from .forms import UserRoleForm, TeamForm, AddUserForm, UserProfileForm, SmtpSettingsForm
from django.contrib import messages

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

def is_super_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin)
def manage_users(request):
    # Employee accounts remain in the system for authentication and ticket history,
    # but this administration screen is reserved for portal administrators and reps.
    users = User.objects.exclude(role='employee').order_by('username')
    return render(request, 'manage_users.html', {'users': users})

@user_passes_test(is_admin)
def edit_user(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Successfully updated {user_obj.username}.")
            return redirect('manage_users')
    else:
        form = UserRoleForm(instance=user_obj)
    return render(request, 'edit_user.html', {'form': form, 'user_obj': user_obj})

@user_passes_test(is_admin)
def demote_user(request, pk):
    if request.method == 'POST':
        user_obj = get_object_or_404(User, pk=pk)
        user_obj.role = 'employee'
        user_obj.is_staff = False
        user_obj.is_superuser = False
        user_obj.save()
        user_obj.teams.clear()
        messages.success(request, f"Demoted {user_obj.username} to employee.")
    return redirect('manage_users')

@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        form = AddUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if user.role == 'admin':
                user.is_staff = True
                user.is_superuser = True
            user.save()
            form.save_m2m()
            messages.success(request, f"Successfully created pre-provisioned user {user.username}.")
            return redirect('manage_users')
    else:
        form = AddUserForm()
    return render(request, 'add_user.html', {'form': form})

@user_passes_test(is_admin)
def manage_teams(request):
    teams = Team.objects.all().order_by('name')
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department created.")
            return redirect('manage_teams')
    else:
        form = TeamForm()
    return render(request, 'manage_teams.html', {'teams': teams, 'form': form})

@user_passes_test(is_admin)
def edit_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if request.method == 'POST':
        if 'update_basic' in request.POST:
            form = TeamForm(request.POST, instance=team)
            if form.is_valid():
                form.save()
                messages.success(request, "Department details updated.")
                return redirect('edit_team', team_id=team.id)
                
        # Simple SLA/Close updates
        elif 'update_settings' in request.POST:
            team.sla_days = request.POST.get('sla_days', 1)
            team.auto_close_days = request.POST.get('auto_close_days', 3)
            team.save()
            messages.success(request, "Department settings updated.")
            return redirect('edit_team', team_id=team.id)
            
        # Add Canned Response
        elif 'add_canned' in request.POST:
            title = request.POST.get('title')
            body = request.POST.get('body')
            import json
            try:
                responses = json.loads(team.canned_responses) if team.canned_responses else []
            except:
                responses = []
            responses.append({'id': str(len(responses)+1), 'title': title, 'body': body})
            team.canned_responses = json.dumps(responses)
            team.save()
            messages.success(request, "Canned response added.")
            return redirect('edit_team', team_id=team.id)
            
        # Update Workflow Rules
        elif 'update_workflow' in request.POST:
            rules = request.POST.get('workflow_rules', '[]')
            import json
            try:
                json.loads(rules)
                team.workflow_rules = rules
                team.save()
                messages.success(request, "Workflow rules updated successfully.")
            except Exception:
                messages.error(request, "Invalid JSON format for workflow rules.")
            return redirect('edit_team', team_id=team.id)
            
        # Upload Resource File
        elif 'upload_resource' in request.POST:
            file = request.FILES.get('file')
            if file:
                from tickets.models import Attachment
                Attachment.objects.create(team=team, file=file)
                messages.success(request, "Resource file uploaded.")
            return redirect('edit_team', team_id=team.id)
            
    else:
        form = TeamForm(instance=team)
        
    import json
    try:
        canned_responses = json.loads(team.canned_responses) if team.canned_responses else []
    except:
        canned_responses = []
        
    return render(request, 'edit_team.html', {'team': team, 'form': form, 'canned_responses': canned_responses})

@user_passes_test(is_admin)
def delete_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    if request.method == 'POST':
        # Safely delete department
        team.delete()
        messages.success(request, f"Department '{team.name}' deleted successfully.")
        return redirect('manage_teams')
    return render(request, 'delete_team.html', {'team': team})

@user_passes_test(is_super_admin)
def manage_branding(request):
    from .models import Branding
    from .forms import BrandingForm
    branding = Branding.get_settings()
    
    if request.method == 'POST':
        form = BrandingForm(request.POST, request.FILES, instance=branding)
        if form.is_valid():
            form.save()
            messages.success(request, "Branding settings updated. The portal is now looking fresh!")
            return redirect('manage_branding')
    else:
        form = BrandingForm(instance=branding)
        
    return render(request, 'manage_branding.html', {'form': form})


@user_passes_test(is_super_admin)
def manage_smtp(request):
    """SMTP configuration page for superadmins."""
    smtp = SmtpSettings.get_settings()

    if request.method == 'POST':
        if 'test_email' in request.POST:
            # Send a quick test email using current (already-saved) settings
            from users.email_utils import send_mail_with_settings
            try:
                send_mail_with_settings(
                    subject='Test Email from Ticketing Portal',
                    body='This is a test message sent from the SMTP settings page.',
                    to=[request.user.email or request.POST.get('test_to', '')],
                )
                messages.success(request, 'Test email sent successfully — check your inbox!')
            except Exception as exc:
                messages.error(request, f'Failed to send test email: {exc}')
            return redirect('manage_smtp')

        form = SmtpSettingsForm(request.POST, instance=smtp)
        if form.is_valid():
            form.save()
            messages.success(request, 'SMTP settings saved.')
            return redirect('manage_smtp')
    else:
        form = SmtpSettingsForm(instance=smtp)

    return render(request, 'manage_smtp.html', {'form': form, 'smtp': smtp})


@login_required
def profile_setup(request):

    if request.method == 'POST':
        from .forms import UserProfileForm
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('dashboard')
    else:
        from .forms import UserProfileForm
        form = UserProfileForm(instance=request.user)
    return render(request, 'profile.html', {'form': form})

import os
import secrets
import requests
import jwt
from django.contrib.auth import login
from django.urls import reverse
from django.conf import settings

def microsoft_login(request):
    if not settings.MS_SSO_ENABLED:
        messages.error(request, "Microsoft SSO is only available in the configured production environment.")
        return redirect('login')

    client_id = os.environ['MS_CLIENT_ID']
    tenant_id = os.environ['MS_TENANT_ID']
    redirect_uri = settings.SITE_URL + reverse('microsoft_callback')
    state = secrets.token_urlsafe(32)
    request.session['microsoft_oauth_state'] = state
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&response_mode=query&scope=openid profile email&state={state}"
    return redirect(url)

def microsoft_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    if not settings.MS_SSO_ENABLED or not code or not state or state != request.session.pop('microsoft_oauth_state', None):
        messages.error(request, "Microsoft SSO failed.")
        return redirect('login')
        
    client_id = os.environ['MS_CLIENT_ID']
    client_secret = os.environ['MS_CLIENT_SECRET']
    tenant_id = os.environ['MS_TENANT_ID']
    redirect_uri = settings.SITE_URL + reverse('microsoft_callback')
    
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        'client_id': client_id,
        'scope': 'openid profile email',
        'code': code,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
        'client_secret': client_secret,
    }
    
    r = requests.post(token_url, data=data, timeout=15)
    if r.status_code != 200:
        messages.error(request, "Failed to exchange token with Microsoft.")
        return redirect('login')
        
    tokens = r.json()
    id_token = tokens.get('id_token')
    if not id_token:
        messages.error(request, "No identity token returned.")
        return redirect('login')
        
    try:
        metadata_url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        metadata = requests.get(metadata_url, timeout=15).json()
        signing_key = jwt.PyJWKClient(metadata['jwks_uri']).get_signing_key_from_jwt(id_token)
        decoded = jwt.decode(
            id_token, signing_key.key, algorithms=['RS256'], audience=client_id,
            issuer=metadata['issuer'],
        )
    except (requests.RequestException, KeyError, jwt.PyJWTError, ValueError):
        messages.error(request, "Microsoft identity validation failed.")
        return redirect('login')
    email = decoded.get('preferred_username') or decoded.get('email')
    
    if not email:
        messages.error(request, "No email in Microsoft token.")
        return redirect('login')
        
    user, created = User.objects.get_or_create(username=email, defaults={
        'email': email,
        'first_name': decoded.get('given_name', ''),
        'last_name': decoded.get('family_name', ''),
        'role': 'employee'
    })
    
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('dashboard')

@login_required
def role_selection(request):
    # Only admins and reps need to select a role
    if request.user.role not in ['admin', 'functional_rep']:
        return redirect('dashboard')
        
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['admin', 'employee']:
            request.session['active_role'] = role
            return redirect('dashboard')
            
    return render(request, 'role_selection.html')


@login_required
def switch_role(request, role):
    """Switch the current session between employee and agent views."""
    if request.method != 'POST' or request.user.role not in ['admin', 'functional_rep']:
        return redirect('dashboard')
    if role not in ['employee', 'admin']:
        return redirect('dashboard')
    request.session['active_role'] = role
    return redirect('dashboard')
