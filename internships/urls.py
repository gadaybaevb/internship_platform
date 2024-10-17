from django.urls import path
from .views import (
    material_edit,
    material_list,
    material_create,
    material_delete,
    assign_mentor,
    internship_list,
    dashboard,
    update_stage_progress,
    intern_materials,
    mark_material_completed,
    mentor_view_intern_materials,
    confirm_material_completion,
)

urlpatterns = [
    path('materials/', material_list, name='material_list'),
    path('materials/create/', material_create, name='material_create'),
    path('materials/edit/<int:material_id>/', material_edit, name='material_edit'),
    path('materials/delete/<int:material_id>/', material_delete, name='material_delete'),
    path('my_materials/', intern_materials, name='intern_materials'),

    path('interships/<int:internship_id>/assign-mentor/', assign_mentor, name='assign_mentor'),
    path('internships/', internship_list, name='internship_list'),

    path('dashboard/', dashboard, name='dashboard'),
    path('stage-progress/<int:stage_id>/update/', update_stage_progress, name='update_stage_progress'),

    path('materials/<int:material_id>/complete/', mark_material_completed, name='mark_material_completed'),
    path('interns/<int:intern_id>/materials/', mentor_view_intern_materials, name='mentor_view_intern_materials'),
    path('materials/confirm/<int:progress_id>/', confirm_material_completion, name='confirm_material_completion'),
]
