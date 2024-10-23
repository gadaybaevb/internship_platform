from django.db import models
from django.contrib.auth import get_user_model


class Notification(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField(verbose_name='Сообщение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Созданов в')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"
