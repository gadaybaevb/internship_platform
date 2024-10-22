from django import forms
from .models import Material, Internship


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['title', 'description', 'file', 'position', 'stage']


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = ['intern_feedback', 'mentor_feedback']