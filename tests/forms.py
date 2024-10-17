from django import forms
from .models import Question, Answer, Test
from django.forms import inlineformset_factory


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['title', 'stage_number', 'position', 'required_questions', 'passing_score', 'time_limit']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'stage_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'required_questions': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control'}),  # Поле для указания времени на тест
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control'}),
            'question_type': forms.Select(attrs={'class': 'form-control'}),
        }


# class AnswerFormSet(forms.BaseInlineFormSet):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         for i in range(4):  # Делаем 4 формы для 4 ответов
#             self.forms.append(AnswerForm())


AnswerFormSet = inlineformset_factory(Question, Answer, fields=('text', 'is_correct'), extra=4)



class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text', 'is_correct', 'sequence_order', 'match_pair']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sequence_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'match_pair': forms.TextInput(attrs={'class': 'form-control'}),
        }