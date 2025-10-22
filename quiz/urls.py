# quiz/urls.py

from django.urls import path
from quiz.views import show_main, create_quiz_with_questions, quiz_detail, take_quiz, deleteQuiz

app_name = 'quiz'

urlpatterns = [
    path('', show_main, name='show_main'),
    path('create/', create_quiz_with_questions, name='create_quiz'),
    path('<int:quiz_id>/', quiz_detail, name='quiz_detail'),
    # 👇 TAMBAHKAN PATH INI 👇
    path('<int:quiz_id>/take/', take_quiz, name='take_quiz'),
    path('<int:quiz_id>/delete/', deleteQuiz, name='delete_quiz'),
]