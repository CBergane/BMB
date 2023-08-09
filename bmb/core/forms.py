from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

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
