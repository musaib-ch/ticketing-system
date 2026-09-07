from django import forms
from django.core.exceptions import ValidationError
from .models import Ticket, TicketMessage, KnowledgeArticle
from .utils import validate_uploaded_file

class KnowledgeArticleForm(forms.ModelForm):
    class Meta:
        model = KnowledgeArticle
        fields = ['title', 'content', 'team', 'file', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Article Title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Write your article text or details...'}),
            'team': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.ppt,.pptx,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.webp'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'file': 'Attachment (PPT, PDF, Word, Excel, Image)'
        }

from .models import Attachment
from users.models import Team

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'team', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief summary of your request'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Provide details...'}),
            'team': forms.Select(attrs={'class': 'form-control', 'id': 'team-select'}),
            'priority': forms.Select(attrs={'class': 'form-control'})
        }
        
    query_relevance = forms.CharField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'query-relevance-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['team'].required = False
        self.fields['team'].empty_label = "Other / Unsure (Send to Admin)"
    
    attachment = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.gif,.webp'})
    )

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        try:
            validate_uploaded_file(attachment)
        except ValidationError as exc:
            raise forms.ValidationError(exc.message)
        return attachment


class TicketMessageForm(forms.ModelForm):
    is_internal = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    class Meta:
        model = TicketMessage
        fields = ['body', 'is_internal']
        widgets = {
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Type your reply here...'}),
        }
    
    attachment = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.gif,.webp'})
    )

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        try:
            validate_uploaded_file(attachment)
        except ValidationError as exc:
            raise forms.ValidationError(exc.message)
        return attachment
