from django.db import models
from users.models import CustomUser
from internships.models import StageProgress
from departments.models import Position
from django.apps import apps


class Test(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    stage_number = models.IntegerField(verbose_name='Этап стажировки')  # Этап стажировки
    position = models.ForeignKey(Position, on_delete=models.CASCADE, verbose_name='Должность')  # Привязка к позиции
    required_questions = models.IntegerField(default=5, verbose_name='Количество вопросов в тесте')  # Сколько вопросов должно быть в тесте
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Проходной балл')  # Проходной балл
    time_limit = models.IntegerField(default=30, verbose_name='Лимит времени для теста')  # Время на тест в минутах

    def __str__(self):
        return self.title

    def questions_count(self):
        """Возвращает количество вопросов, связанных с этим тестом"""
        return self.questions.count()  # Связь через related_name='questions' в модели Question


class Question(models.Model):
    QUESTION_TYPES = (
        ('single', 'Один верный ответ'),
        ('multiple', 'Несколько верных ответов'),
        ('true_false', 'Верно/Неверно'),
        ('sequence', 'Последовательность'),
        ('match', 'Соответствие'),
    )

    test = models.ForeignKey(Test, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField(verbose_name='Текст вопроса')  # Текст вопроса
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, verbose_name='Тип вопроса')

    def __str__(self):
        return f"{self.text} ({self.get_question_type_display()})"


class Answer(models.Model):
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    text = models.CharField(max_length=200,  verbose_name='Ответ')  # Вариант ответа
    is_correct = models.BooleanField(default=False, verbose_name='Правильный?')  # Верный или неверный ответ
    sequence_order = models.IntegerField(null=True, blank=True)  # Порядок для последовательности (если нужно)
    match_pair = models.CharField(max_length=200, null=True, blank=True)  # Пара для соответствия (если нужно)

    def __str__(self):
        return self.text


class TestResult(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Пользователь')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, verbose_name='Тест')
    score = models.FloatField(verbose_name='Балл')
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name='Тест завершен')
    correct_answers_count = models.IntegerField(default=0, verbose_name='Количество правильных ответов')  # Количество правильных ответов
    total_questions_count = models.IntegerField(default=0, verbose_name='Количество всего вопросов')  # Общее количество вопросов

    def __str__(self):
        return f"{self.user.username} - {self.test.title} - {self.score}"

    def all_tests_completed(self):
        """Проверка, сдал ли стажер все тесты."""
        # Проверяем, сдал ли стажер все тесты для его позиции
        return TestResult.objects.filter(user=self.intern).count() == Test.objects.filter(
            position=self.position).count()
