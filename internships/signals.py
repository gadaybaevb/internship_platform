from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from .models import StageProgress
from django.core.mail import send_mail

@receiver(post_save, sender=StageProgress)
def check_deadline(sender, instance, **kwargs):
    # Если до дедлайна меньше 3 дней и этап не завершён
    if not instance.completed and (instance.completion_date - now()).days <= 3:
        send_mail(
            'Приближается дедлайн по этапу стажировки',
            f'Этап {instance.stage} для стажировки должен быть завершён в ближайшие 3 дня.',
            'noreply@company.com',
            [instance.intern.email, instance.intern.mentor.email if instance.intern.mentor else None],
            fail_silently=False,
        )
