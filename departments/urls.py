from django.urls import path
from .views import (
    department_create,
    department_list,
    department_delete,
    department_edit,
    position_create,
    position_list,
    position_edit,
    position_delete,

)

urlpatterns = [
    path('departments/', department_list, name='department_list'),
    path('departments/create/', department_create, name='department_create'),
    path('departments/edit/<int:department_id>/', department_edit, name='department_edit'),
    path('departments/delete/<int:department_id>/', department_delete, name='department_delete'),

    path('positions/', position_list, name='position_list'),
    path('positions/create/', position_create, name='position_create'),
    path('positions/edit/<int:position_id>/', position_edit, name='position_edit'),
    path('positions/delete/<int:position_id>/', position_delete, name='position_delete'),
]
