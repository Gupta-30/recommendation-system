from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

class RegisterForm(UserCreationForm):
     name = forms.CharField(max_length=100)
     email = forms.CharField(max_length=100)
     class Meta:
        model = User
        fields = ('name', 'email', 'username', 'password1', 'password2', )
        labels = {'name': 'Name', 'email': 'Email', }
        