from django import forms
from .models import Profile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['display_name', 'avatar']

class RegisterForm(UserCreationForm):

    email = forms.EmailField(required=True)

    class Meta:
        model = User

        fields = (
            'username',
            'email',
            'password1',
            'password2'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Replace Django's default (generic, framework-y) help text with
        # copy that matches OneSider's tone.
        self.fields['username'].help_text = (
            "3-150 characters. Letters, digits, and @/./+/-/_ only."
        )
        self.fields['email'].help_text = ""
        self.fields['password1'].help_text = (
            "At least 8 characters. Not entirely numeric, not too common, "
            "not too close to your username or email."
        )
        self.fields['password2'].help_text = (
            "Enter the same password again to confirm."
        )