from django.db import models
from users.models import CustomUser
from internships.models import StageProgress
from departments.models import Position
from django.apps import apps


class Test(models.Model):
    title = models.CharField(max_length=200)
    stage_number = models.IntegerField()  # Этап стажировки
    position = models.ForeignKey(Position, on_delete=models.CASCADE)  # Привязка к позиции
    required_questions = models.IntegerField(default=5)  # Сколько вопросов должно быть в тесте
    passing_score = models.DecimalField(max_digits=5, decimal_places=2)  # Проходной балл
    time_limit = models.IntegerField(default=30)  # Время на тест в минутах

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
    text = models.TextField()  # Текст вопроса
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)

    def __str__(self):
        return f"{self.text} ({self.get_question_type_display()})"


class Answer(models.Model):
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    text = models.CharField(max_length=200)  # Вариант ответа
    is_correct = models.BooleanField(default=False)  # Верный или неверный ответ
    sequence_order = models.IntegerField(null=True, blank=True)  # Порядок для последовательности (если нужно)
    match_pair = models.CharField(max_length=200, null=True, blank=True)  # Пара для соответствия (если нужно)

    def __str__(self):
        return self.text


class TestResult(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    score = models.FloatField()
    completed_at = models.DateTimeField(auto_now_add=True)
    correct_answers_count = models.IntegerField(default=0)  # Количество правильных ответов
    total_questions_count = models.IntegerField(default=0)  # Общее количество вопросов

    def __str__(self):
        return f"{self.user.username} - {self.test.title} - {self.score}"

    def all_tests_completed(self):
        """Проверка, сдал ли стажер все тесты."""
        # Проверяем, сдал ли стажер все тесты для его позиции
        return TestResult.objects.filter(user=self.intern).count() == Test.objects.filter(
            position=self.position).count()
