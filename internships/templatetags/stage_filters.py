from django import template
from internships.models import StageProgress

register = template.Library()

@register.filter
def get_stage_completed(stage_progress, stage_number):
    """
    Фильтр проверяет, завершён ли этап с номером stage_number
    для текущего стажёра.
    """
    return stage_progress.filter(stage=stage_number, completed=True).exists()
