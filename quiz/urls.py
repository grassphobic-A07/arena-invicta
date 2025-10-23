# quiz/urls.py

from django.urls import path
from quiz.views import (
    show_main, create_quiz_with_questions, quiz_detail, 
    take_quiz, deleteQuiz, edit_quiz, toggle_publish, display_score
)

app_name = 'quiz'

urlpatterns = [
    path('', show_main, name='show_main'),
    path('create/', create_quiz_with_questions, name='create_quiz'),
    path('<int:quiz_id>/', quiz_detail, name='quiz_detail'),
    path('<int:quiz_id>/take/', take_quiz, name='take_quiz'),
    path('<int:quiz_id>/delete/', deleteQuiz, name='delete_quiz'),
    path('<int:quiz_id>/edit/', edit_quiz, name='edit_quiz'),
    path('<int:quiz_id>/toggle_publish/', toggle_publish, name='toggle_publish'),
    path('<int:quiz_id>/result/', display_score, name='quiz_result'),
]