from django import forms
from store.models import Store

class StoreOwnerRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150, label='jina la mtumiaji')
    name = forms.CharField(max_length=200, label='Jina la Biashara')
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': '2'}), label='Mahali')
    phone_number = forms.CharField(max_length=50, label='Nambari ya Simu')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Add custom validation if necessary, e.g., check phone number format
        return phone_number
