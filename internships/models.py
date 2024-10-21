from django.db import models
from departments.models import Position
from django.contrib.auth import get_user_model
from users.models import CustomUser
from django.utils import timezone
from datetime import timedelta


class Material(models.Model):
    title = models.CharField(max_length=255)  # Название материала
    description = models.TextField()  # Описание материала
    file = models.FileField(upload_to='materials/', null=True, blank=True)  # Файл (PDF, видео и т.д.)
    position = models.ForeignKey(Position, on_delete=models.CASCADE)  # Связь с позицией
    stage = models.IntegerField()  # Номер этапа

    def __str__(self):
        return f'{self.title} (Этап {self.stage} для {self.position.name})'


class Internship(models.Model):
    intern = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='intern_internships')
    mentor = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name='mentor_internships')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True)  # Позиция для стажера
    start_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.intern.username}'s Internship with {self.mentor.username if self.mentor else 'No Mentor'}"

    def all_stages_completed(self):
        """Проверка, завершены ли все этапы."""
        # Проверяем, завершены ли все этапы для данного стажера
        return StageProgress.objects.filter(intern=self.intern, completed=False).count() == 0

    def all_materials_completed(self):
        """Проверка, завершены ли все материалы."""
        # Проверяем, завершены ли все материалы для позиции стажера
        return MaterialProgress.objects.filter(intern=self.intern, completed=False).count() == 0



    # def is_completed(self):
    #     # Проверка, завершены ли все этапы
    #     all_stages_completed = StageProgress.objects.filter(intern=self.intern, completed=False).count() == 0
    #     # Проверка, истёк ли срок стажировки
    #     end_date = self.start_date + timedelta(days=self.position.duration_days)
    #     time_expired = timezone.now().date() > end_date

    def all_tests_completed(self):
        """Проверка, сдал ли стажер все тесты."""
        # Выполняем запрос к TestResult без прямого импорта модели
        from tests.models import Test, TestResult  # Импортируем модель внутри метода, чтобы избежать цикла
        return TestResult.objects.filter(user=self.intern).count() == Test.objects.filter(position=self.position).count()

    def is_completed(self):
        """Проверка, завершены ли все этапы, материалы и тесты."""
        return self.all_stages_completed() and self.all_materials_completed() and self.all_tests_completed()

    def internship_duration_expired(self):
        """Проверка, истёк ли срок стажировки."""
        end_date = self.start_date + timedelta(days=self.position.duration_days)
        return timezone.now().date() > end_date


class StageProgress(models.Model):
    intern = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='stage_progresses')
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    stage = models.IntegerField(default=1)  # Номер этапа
    completed = models.BooleanField(default=False)  # Завершён ли этап
    completion_date = models.DateTimeField(null=True, blank=True)  # Дата завершения этапа

    def __str__(self):
        return f"{self.intern.full_name} - Этап {self.stage} ({'Завершён' if self.completed else 'Не завершён'})"


class MaterialProgress(models.Model):
    STATUS_CHOICES = (
        ('not_started', 'Не пройден'),
        ('pending', 'Ожидание'),
        ('completed', 'Завершен'),
    )
    intern = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    mentor_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')

    # Дата завершения и подтверждения можно хранить как дополнительные поля
    completion_date = models.DateTimeField(null=True, blank=True)
    confirmation_date = models.DateTimeField(null=True, blank=True)

