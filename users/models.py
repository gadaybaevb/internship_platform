from django.contrib.auth.models import AbstractUser
from django.db import models
from departments.models import Department, Position
# from internships.models import StageProgress
# from tests.models import TestResult, Test


class CustomUser(AbstractUser):
    # Дополнительные поля
    DEPARTMENTS = (
        ('finance', 'Finance'),
        ('hr', 'HR'),
        ('it', 'IT'),
        ('facility', 'Facility'),
        ('csd', 'CSD'),
        ('marketing', 'Marketing'),
        ('academic', 'Academic'),
        # Добавь свои департаменты
    )

    ROLES = (
        ('admin', 'Administrator'),
        ('mentor', 'Mentor'),
        ('intern', 'Intern'),
    )

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLES, default='intern')  # Добавляем поле role
    full_name = models.CharField(max_length=255)  # Добавляем поле ФИО

    def __str__(self):
        return f'{self.username} ({self.position.name if self.position else "No position"})'


    # @property
    # def all_stages_completed(self):
    #     """Проверка, завершены ли все этапы стажировки."""
    #     return StageProgress.objects.filter(intern=self, completed=False).count() == 0
    #
    # @property
    # def all_tests_completed(self):
    #     """Проверка, сдал ли пользователь все тесты."""
    #     return TestResult.objects.filter(user=self).count() == Test.objects.filter(position=self.position).count()