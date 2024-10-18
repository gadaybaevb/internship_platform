from django.contrib.auth.models import AbstractUser
from django.db import models
from departments.models import Department, Position


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


