from django import forms
from .models import Department, Position


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['name', 'department', 'duration_days', 'stages_count', 'intermediate_test_after_stage', 'final_test_after_days']
