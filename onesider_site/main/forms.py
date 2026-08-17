from django import forms
from .models import ContactMessage

INPUT_CLASSES = "input-premium bg-transparent w-full py-2 text-sm"


class ContactForm(forms.ModelForm):

    # Honeypot: a field real visitors never see or fill in (hidden via
    # CSS, not the `type="hidden"` attribute, since some bots skip those
    # specifically). If it's filled, the submission is silently treated
    # as spam without telling the bot why - not shown as an error.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'autocomplete': 'off',
        'tabindex': '-1',
        'class': 'hp-field',
    }))

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Your name',
                'maxlength': 100,
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'you@example.com',
            }),
            'message': forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'What do you want to say?',
                'rows': 6,
                'maxlength': 3000,
            }),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if len(name) < 2:
            raise forms.ValidationError("That name looks too short.")
        return name

    def clean_message(self):
        message = self.cleaned_data['message'].strip()
        if len(message) < 10:
            raise forms.ValidationError(
                "Say a little more - at least 10 characters."
            )
        return message

    def is_spam(self):
        """Call after is_valid(). True if the honeypot was filled."""
        return bool(self.cleaned_data.get('website'))