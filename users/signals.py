from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser
from internships.models import Internship


@receiver(post_save, sender=CustomUser)
def create_internship_for_intern(sender, instance, created, **kwargs):
    if created and instance.role == 'intern':  # Только для новых пользователей с ролью 'intern'
        Internship.objects.create(intern=instance)
        print(f"Стажировка создана для {instance.username}")
