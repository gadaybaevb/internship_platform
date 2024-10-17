from django.urls import path
from .views import notifications_view, mark_notification_read

urlpatterns = [
    path('notifications/', notifications_view, name='notifications'),
    path('notifications/read/<int:notification_id>/', mark_notification_read, name='mark_notification_read'),
]
