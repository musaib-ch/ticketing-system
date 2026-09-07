from django import forms
from .models import User, Team, Branding

class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role', 'teams']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'teams': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teams'].required = False
        self.fields['role'].choices = [
            ('admin', 'Admin'), 
            ('functional_rep', 'Functional Representative')
        ]

class AddUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'role', 'teams']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AD Username (e.g., john_doe)'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'teams': forms.CheckboxSelectMultiple(),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teams'].required = False
        self.fields['role'].choices = [
            ('admin', 'Admin'), 
            ('functional_rep', 'Functional Representative')
        ]

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'query_categories', 'sla_days', 'auto_close_days', 'canned_responses', 'workflow_rules']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., IT Support'}),
            'query_categories': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Rewards, Policy, CSR'}),
            'sla_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'auto_close_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'canned_responses': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '[{"title": "Reset Password", "body": "Please click here..."}]'}),
            'workflow_rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '[{"keyword": "payroll", "priority": "urgent"}]'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'employee_number', 'location']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': 'required'}),
            'employee_number': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
        }

class BrandingForm(forms.ModelForm):
    class Meta:
        model = Branding
        fields = [
            'portal_name', 'primary_color', 'secondary_color', 
            'chart_color_1', 'chart_color_2', 'chart_color_3', 'chart_color_4', 'chart_color_5',
            'logo', 'background_image', 'ticket_reopen_window_days'
        ]
        
        widgets = {
            'portal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control', 'style': 'height: 45px; padding: 0.25rem;'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control', 'style': 'height: 45px; padding: 0.25rem;'}),
            'chart_color_1': forms.TextInput(attrs={'type': 'color', 'class': 'form-control', 'style': 'height: 45px; padding: 0.25rem;'}),
            'chart_color_2': forms.TextInput(attrs={'type': 'color', 'class': 'form-control', 'style': 'height: 45px; padding: 0.25rem;'}),
            'chart_color_3': forms.TextInput(attrs={'type': 'color', 'class': 'form-control', 'style': 'height: 45px; padding: 0.25rem;'}),
            'chart_color_4': forms.TextInput(attrs={'type': 'color', 'class': 'form-control', 'style': 'height: 45px; padding: 0.25rem;'}),
            'chart_color_5': forms.TextInput(attrs={'type': 'color', 'class': 'form-control', 'style': 'height: 45px; padding: 0.25rem;'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'background_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'ticket_reopen_window_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
