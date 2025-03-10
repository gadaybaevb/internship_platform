from django import forms
from .models import Material, Internship, Position
from users.models import CustomUser


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['title', 'description', 'file', 'position', 'stage']


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = ['intern_feedback']


class AddInternForm(forms.ModelForm):
    mentor = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='mentor'),
        label="Ментор",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    intern = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='intern'),
        label="Стажер",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    position = forms.ModelChoiceField(
        queryset=Position.objects.all(),
        label="Позиция",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Internship
        fields = ['intern', 'mentor', 'position']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Установка отображения full_name в выпадающем списке
        self.fields['mentor'].label_from_instance = lambda obj: obj.full_name
        self.fields['intern'].label_from_instance = lambda obj: obj.full_name


class MentorReviewForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = ['mentor_feedback']
        widgets = {
            'mentor_feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Напишите отзыв о стажере'
            })
        }
