from django.contrib.auth.models import AbstractUser
from django.db import models
from departments.models import Department, Position
from datetime import timedelta
from django.utils import timezone
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

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Отдел")
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Должность')
    role = models.CharField(max_length=10, choices=ROLES, default='intern', verbose_name="Роль")  # Добавляем поле role
    full_name = models.CharField(max_length=255, verbose_name='ФИО')  # Добавляем поле ФИО
    last_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.username} ({self.position.name if self.position else "No position"})'

    def last_login_adjusted(self):
        if self.last_login:
            return self.last_login + timedelta(hours=5)
        return None
    # @property
    # def all_stages_completed(self):
    #     """Проверка, завершены ли все этапы стажировки."""
    #     return StageProgress.objects.filter(intern=self, completed=False).count() == 0
    #
    # @property
    # def all_tests_completed(self):
    #     """Проверка, сдал ли пользователь все тесты."""
    #     return TestResult.objects.filter(user=self).count() == Test.objects.filter(position=self.position).count()