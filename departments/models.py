from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Отдел')

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='Отдел')
    duration_days = models.IntegerField(default=30, verbose_name='Срок стажировки')  # Срок стажировки (в днях)
    stages_count = models.IntegerField(default=1, verbose_name='Количество этапов')  # Количество этапов
    intermediate_test_after_stage = models.IntegerField(null=True, blank=True, verbose_name='Промежуточный тест')  # Номер этапа для промежуточного теста
    final_test_after_days = models.IntegerField(null=True, blank=True, verbose_name='Финальный тест')  # Через сколько дней финальный тест

    def __str__(self):
        return f'{self.name} ({self.department.name})'


