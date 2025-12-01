# quiz/urls.py

from django.urls import path
from quiz.views import (
    show_main,
    create_quiz_with_questions,
    quiz_detail, 
    take_quiz,
    deleteQuiz,
    edit_quiz,
    toggle_publish,
    display_score,
    get_all_quizzes,
    get_quiz_detail,
    submit_quiz,
    quiz_admin_detail,
    quiz_admin_quizzez
)

app_name = 'quiz'

urlpatterns = [
    path('', show_main, name='show_main'),
    path('api/', get_all_quizzes, name="get_all_quizzes"),
    path('api/admin', quiz_admin_quizzez, name="get_admin_quizzes"),
    path('api/<int:quiz_id>/', get_quiz_detail, name="get_quiz_detail"), 
    path('api/<int:quiz_id>/submit/', submit_quiz, name="submit_quiz"),   
    path('api/<int:quiz_id>/admin/', quiz_admin_detail, name="quiz_admin_detail"),  
    path('create/', create_quiz_with_questions, name='create_quiz'),
    path('<int:quiz_id>/', quiz_detail, name='quiz_detail'),
    path('<int:quiz_id>/take/', take_quiz, name='take_quiz'),
    path('<int:quiz_id>/delete/', deleteQuiz, name='delete_quiz'),
    path('<int:quiz_id>/edit/', edit_quiz, name='edit_quiz'),
    path('<int:quiz_id>/toggle_publish/', toggle_publish, name='toggle_publish'),
    path('<int:quiz_id>/result/', display_score, name='quiz_result'),
]