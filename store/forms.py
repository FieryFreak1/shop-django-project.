from django import forms
from .models import StoreContact

class StoreContactForm(forms.ModelForm):
    class Meta:
        model = StoreContact
        fields = ['phone', 'email', 'address']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'].widget.attrs.update({'placeholder': '+7 (999) 000-00-00'})
        self.fields['email'].widget.attrs.update({'placeholder': 'mail@zoneshop.ru'})