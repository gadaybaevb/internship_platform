from django.shortcuts import render
from .models import Notification
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Count

from django.core.paginator import Paginator

from django.core.paginator import Paginator


def notifications_view(request):
    # Сортировка: сначала непрочитанные, затем по дате
    notifications = Notification.objects.filter(user=request.user).order_by('is_read', '-created_at')

    # Пагинация: 10 уведомлений на страницу
    paginator = Paginator(notifications, 10)  # Показывать по 10 уведомлений на странице
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    unread_count = notifications.filter(is_read=False).count()  # Количество непрочитанных уведомлений
    read_count = notifications.filter(is_read=True).count()  # Количество прочитанных уведомлений
    total_count = notifications.count()  # Общее количество уведомлений

    return render(request, 'notifications.html', {
        'page_obj': page_obj,  # Передаем объект пагинации
        'unread_count': unread_count,  # Количество непрочитанных
        'read_count': read_count,  # Количество прочитанных
        'total_count': total_count,  # Общее количество уведомлений
    })


def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications')