from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    duration_days = models.IntegerField(default=30)  # Срок стажировки (в днях)
    stages_count = models.IntegerField(default=1)  # Количество этапов
    intermediate_test_after_stage = models.IntegerField(null=True, blank=True)  # Номер этапа для промежуточного теста
    final_test_after_days = models.IntegerField(null=True, blank=True)  # Через сколько дней финальный тест

    def __str__(self):
        return f'{self.name} ({self.department.name})'


