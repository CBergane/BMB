from django import forms
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.contrib.auth.models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        field_classes = {'username': UsernameField}
        labels = {
            'first_name': 'Förnamn',
            'last_name': 'Efternamn',
            'username': 'Användarnamn',
            'email': 'E-mail',
        }
        error_messages = {
            'first_name': {'max_length': 'Ange högst %(limit_value)d tecken.'},
            'last_name': {'max_length': 'Ange högst %(limit_value)d tecken.'},
            'username': {
                'required': 'Ange ett användarnamn.',
                'invalid': 'Använd endast bokstäver, siffror och @/./+/-/_.',
                'unique': 'Användarnamnet är redan upptaget.',
                'max_length': 'Ange högst %(limit_value)d tecken.',
            },
            'email': {
                'invalid': 'Ange en giltig e-postadress.',
                'max_length': 'Ange högst %(limit_value)d tecken.',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'w-full mt-2 py-4 px-4 bg-gray-100 rounded-xl'


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'w-full mt-2 py-4 px-6 bg-white rounded-xl'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'w-full mt-2 py-4 px-6 bg-white rounded-xl'}))
    email = forms.EmailField(max_length=255, required=True, widget=forms.EmailInput(attrs={'class': 'w-full mt-2 py-4 px-6 bg-white rounded-xl'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2',]

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'w-full mt-2 py-4 px-6 bg-white rounded-xl'})
        self.fields['password1'].widget.attrs.update({'class': 'w-full mt-2 py-4 px-6 bg-white rounded-xl'})
        self.fields['password2'].widget.attrs.update({'class': 'w-full mt-2 py-4 px-6 bg-white rounded-xl'})
