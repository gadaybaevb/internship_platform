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
    intern_report,
    reports_view,
    test_reports_view,
    completed_internships_report,
    mentor_report,
    department_materials_report,
    add_intern,
    weekly_report,
    delete_internship,
)

urlpatterns = [
    path('materials/', material_list, name='material_list'),
    path('materials/create/', material_create, name='material_create'),
    path('materials/edit/<int:material_id>/', material_edit, name='material_edit'),
    path('materials/delete/<int:material_id>/', material_delete, name='material_delete'),
    path('my_materials/', intern_materials, name='intern_materials'),

    path('interships/<int:internship_id>/assign-mentor/', assign_mentor, name='assign_mentor'),
    path('internships/add/', add_intern, name='add_intern'),
    path('internships/delete/<int:internship_id>/', delete_internship, name='delete_internship'),

    path('internships/', internship_list, name='internship_list'),

    path('dashboard/', dashboard, name='dashboard'),
    path('stage-progress/<int:stage_id>/update/', update_stage_progress, name='update_stage_progress'),

    path('materials/<int:material_id>/complete/', mark_material_completed, name='mark_material_completed'),
    path('interns/<int:intern_id>/materials/', mentor_view_intern_materials, name='mentor_view_intern_materials'),
    path('materials/confirm/<int:progress_id>/', confirm_material_completion, name='confirm_material_completion'),

    path('intern_report/<int:intern_id>/', intern_report, name='intern_report'),
    path('reports/', reports_view, name='reports'),
    path('reports/tests/', test_reports_view, name='test_reports'),
    path('reports/completed-internships/', completed_internships_report, name='completed_internships_report'),
    path('reports/mentors-report/', mentor_report, name='mentor_report'),
    path('reports/materials/', department_materials_report, name='department_materials_report'),
    path('reports/weekly-report/', weekly_report, name='weekly_report'),
]
