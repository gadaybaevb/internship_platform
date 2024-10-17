from django.urls import path
from .views import (
    register,
    user_list,
    user_edit,
    user_delete,
    CustomLoginView,
    CustomLogoutView,
    home,
)

urlpatterns = [
    path('', home, name='home'),

    path('register/', register, name='register'),
    path('users/', user_list, name='user_list'),
    path('users/edit/<int:user_id>/', user_edit, name='user_edit'),
    path('users/delete/<int:user_id>/', user_delete, name='user_delete'),

    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]
