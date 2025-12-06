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
    quiz_admin_quizzez,
    create_quiz_flutter,
    edit_quiz_flutter,
    delete_quiz_flutter,
    get_quiz_for_edit_flutter, 
)

app_name = 'quiz'

urlpatterns = [
    # APIs
    path('', show_main, name='show_main'),
    path('api/', get_all_quizzes, name="get_all_quizzes"),
    path('api/admin/', quiz_admin_quizzez, name="get_admin_quizzes"),
    path('api/<int:quiz_id>/', get_quiz_detail, name="get_quiz_detail"), 
    path('api/<int:quiz_id>/submit/', submit_quiz, name="submit_quiz"),   
    path('api/<int:quiz_id>/admin/', quiz_admin_detail, name="quiz_admin_detail"),  
    path('api/create-flutter/', create_quiz_flutter, name='create_quiz_flutter'),
    path('api/edit-flutter/<int:quiz_id>/', edit_quiz_flutter, name='edit_quiz_flutter'),
    path('api/delete-flutter/<int:quiz_id>/', delete_quiz_flutter, name='delete_quiz_flutter'),
    path('api/quiz-data/<int:quiz_id>/', get_quiz_for_edit_flutter, name='get_quiz_for_edit_flutter'), 

    # Web routing
    path('create/', create_quiz_with_questions, name='create_quiz'),
    path('<int:quiz_id>/', quiz_detail, name='quiz_detail'),
    path('<int:quiz_id>/take/', take_quiz, name='take_quiz'),
    path('<int:quiz_id>/delete/', deleteQuiz, name='delete_quiz'),
    path('<int:quiz_id>/edit/', edit_quiz, name='edit_quiz'),
    path('<int:quiz_id>/toggle_publish/', toggle_publish, name='toggle_publish'),
    path('<int:quiz_id>/result/', display_score, name='quiz_result'),
]