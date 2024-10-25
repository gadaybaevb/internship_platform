from django.urls import path
from .views import (take_test, create_test, add_question, tests_list, questions_list,
                    edit_test, delete_test, edit_question, delete_question, test_results, test_instructions, test_report)

urlpatterns = [
    path('test/<int:test_id>/start', take_test, name='take_test'),
    path('test/create/', create_test, name='create_test'),
    path('test/<int:test_id>/add-question/', add_question, name='add_question'),
    path('tests/', tests_list, name='tests_list'),
    path('test/<int:test_id>/edit/', edit_test, name='edit_test'),
    path('test/<int:test_id>/delete/', delete_test, name='delete_test'),

    path('test/<int:test_id>/questions/', questions_list, name='questions_list'),
    path('question/<int:question_id>/edit/', edit_question, name='edit_question'),
    path('question/<int:question_id>/delete/', delete_question, name='delete_question'),

    path('test/<int:test_id>/results/', test_results, name='test_results'),
    path('test/<int:test_id>/intro/', test_instructions, name='test_intro'),
    path('test/report/<int:test_result_id>/', test_report, name='test_report'),

]
