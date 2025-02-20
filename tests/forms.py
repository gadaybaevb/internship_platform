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

    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        # Убрать опцию 'true_false' из списка выбора
        self.fields['question_type'].choices = [
            choice for choice in self.fields['question_type'].choices
            if choice[0] != 'true_false'
        ]


AnswerFormSet = inlineformset_factory(Question, Answer, fields=('text', 'is_correct', 'sequence_order', 'match_pair'),
                                      labels={
                                            'match_pair': 'Соответствие',
                                            'sequence_order': 'Последовательность'
                                      }, extra=4)


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
        labels = {
            'text': 'Ответ'
        }