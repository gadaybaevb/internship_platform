from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser  # Предполагается, что у тебя кастомная модель пользователя


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ['username', 'email', 'full_name', 'department', 'role', 'password1', 'password2']  # Добавляем full_name
        labels = {
            'username': 'Имя пользователя',
            'email': "Почта",
            'full_name': "ФИО",
            'department': "Отдел",
            'role': "Роль",
            'password1': "Пароль",
            'password2': "Повторить пароль"
        }


class CustomUserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'full_name', 'department', 'role']