from django import template

register = template.Library()

@register.filter
def get_answer_text(answers, answer_id):
    """
    Возвращает текст ответа по его ID из списка answers.
    """
    for answer in answers:
        if str(answer.get('id')) == str(answer_id):
            return answer.get('text')
    return "Неизвестный ответ"
