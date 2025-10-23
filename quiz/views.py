from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import inlineformset_factory
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from .forms import QuizForm, QuestionForm
from .models import Quiz, Question, Score


# Helper function to detect AJAX requests
def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def show_main(request):
    quizzes = Quiz.objects.all()
    roles = []
    authorized = False
    role = None

    if request.user.is_authenticated:
        roles = list(request.user.groups.values_list('name', flat=True))
    
    if "Content Staff" in roles:
        quizzes = quizzes.filter(user=request.user)
        authorized = True
        role = "Content Staff"
    else:
        quizzes = quizzes.filter(is_published=True)
        if roles:
            role = roles[0]

    context = {'quizzes': quizzes, 'authorized': authorized, 'role': role}
    return render(request, "quiz/main.html", context)


def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    leaderboard = Score.objects.filter(quiz=quiz).select_related('user').order_by('-score')[:10]
    total_questions = quiz.questions.count()
    
    context = {
        'quiz': quiz, 
        'leaderboard': leaderboard,
        'total_questions': total_questions 
    }
    return render(request, 'quiz/quiz_detail.html', context)


@login_required
def create_quiz_with_questions(request):
    QuestionFormSet = inlineformset_factory(
        Quiz, 
        Question, 
        form=QuestionForm, 
        extra=1, 
        can_delete=True
    )

    if request.method == 'POST':
        quiz_form = QuizForm(request.POST)
        question_formset = QuestionFormSet(request.POST) 

        if quiz_form.is_valid() and question_formset.is_valid():
            quiz = quiz_form.save(commit=False)
            quiz.user = request.user
            quiz.save()

            question_formset.instance = quiz 
            question_formset.save()

            message_text = f"Quiz '{quiz.title}' has been successfully created."

            if is_ajax(request):
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('quiz:quiz_detail', args=[quiz.id]),
                    'message': message_text
                })
            return redirect('quiz:quiz_detail', quiz_id=quiz.id)
        else:
            message_text = "An error occurred. Please check your input and try again."
            if is_ajax(request):
                context = {
                    'quiz_form': quiz_form,
                    'question_formset': question_formset,
                }
                html = render_to_string('quiz/_quiz_form_partial.html', context, request=request)
                return JsonResponse({'success': False, 'html': html, 'message': message_text}, status=400)
    else:
        quiz_form = QuizForm()
        question_formset = QuestionFormSet(instance=Quiz())

    context = {
        'quiz_form': quiz_form,
        'question_formset': question_formset,
    }

    if is_ajax(request):
        return render(request, 'quiz/_quiz_form_partial.html', context)
    
    return render(request, 'quiz/create_quiz.html', context)


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.questions.all()

    if request.method == 'POST':
        score_value = 0
        total_questions = questions.count()

        for question in questions:
            user_answer = request.POST.get(f'question_{question.id}')
            if user_answer == question.correct_answer:
                score_value += 1
        
        percentage = (score_value / total_questions) * 100 if total_questions > 0 else 0

        old_score_object = Score.objects.filter(user=request.user, quiz=quiz).first()
        old_score_value = old_score_object.score if old_score_object else 0 

        if old_score_object and score_value > old_score_value:
            new_score_value = score_value
        elif not old_score_object:
            new_score_value = score_value
        else:
            new_score_value = old_score_value  # Keep the higher score

        Score.objects.update_or_create(
            user=request.user,
            quiz=quiz,
            defaults={'score': new_score_value},
        )
        
        leaderboard = Score.objects.filter(quiz=quiz).select_related('user').order_by('-score')[:10]

        context = {
            'quiz': quiz,
            'score': score_value,
            'total_questions': total_questions,
            'percentage': round(percentage, 2),
            'leaderboard': leaderboard,
        }

        if is_ajax(request):
            html = render_to_string('quiz/_quiz_result_partial.html', context, request=request)
            result_url = reverse('quiz:quiz_result', args=[quiz.id])
            return JsonResponse({'success': True, 'html': html, 'result_url': result_url})

        return render(request, 'quiz/quiz_result.html', context)

    context = {'quiz': quiz, 'questions': questions}
    return render(request, 'quiz/take_quiz.html', context)


@login_required
def deleteQuiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    if quiz.user != request.user:
        messages.error(request, "You do not have permission to delete this quiz.")
        if is_ajax(request):
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        return redirect('quiz:quiz_detail', quiz_id=quiz.id)

    if request.method == 'POST':
        quiz_title = quiz.title
        quiz.delete()
        messages.success(request, f"Quiz '{quiz_title}' has been successfully deleted.")
        
        if is_ajax(request):
            return JsonResponse({
                'success': True, 
                'redirect_url': reverse('quiz:show_main')
            })
        return redirect('quiz:show_main')

    if is_ajax(request):
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    return redirect('quiz:quiz_detail', quiz_id=quiz_id)


@login_required
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    if quiz.user != request.user:
        messages.error(request, "You do not have permission to edit this quiz.")
        if is_ajax(request):
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
        return redirect('quiz:quiz_detail', quiz_id=quiz.id)

    QuestionFormSet = inlineformset_factory(
        Quiz, 
        Question, 
        form=QuestionForm, 
        extra=1,
        can_delete=True
    )

    if request.method == 'POST':
        quiz_form = QuizForm(request.POST, instance=quiz)
        question_formset = QuestionFormSet(request.POST, instance=quiz)

        if quiz_form.is_valid() and question_formset.is_valid():
            quiz_form.save()
            question_formset.save() 

            message_text = f"Quiz '{quiz.title}' has been successfully updated."
            
            if is_ajax(request):
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('quiz:quiz_detail', args=[quiz.id]),
                    'message': message_text 
                })
            return redirect('quiz:quiz_detail', quiz_id=quiz.id)
        else:
            message_text = "An error occurred. Please check your input and try again."
            if is_ajax(request):
                context = {
                    'quiz_form': quiz_form,
                    'question_formset': question_formset,
                    'quiz': quiz,
                }
                html = render_to_string('quiz/_quiz_form_partial.html', context, request=request)
                return JsonResponse({'success': False, 'html': html, 'message': message_text}, status=400)
    else: 
        quiz_form = QuizForm(instance=quiz)
        question_formset = QuestionFormSet(instance=quiz)

    context = {
        'quiz_form': quiz_form,
        'question_formset': question_formset,
        'quiz': quiz
    }
    
    if is_ajax(request):
        return render(request, 'quiz/_quiz_form_partial.html', context)
        
    return render(request, 'quiz/create_quiz.html', context)


@login_required
def toggle_publish(request, quiz_id):
    if request.method == 'POST':
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        
        if quiz.user == request.user:
            quiz.is_published = not quiz.is_published
            quiz.save()
            
            if quiz.is_published:
                message_text = f"Quiz '{quiz.title}' has been published."
            else:
                message_text = f"Quiz '{quiz.title}' has been set to private (draft)."
            
            return JsonResponse({
                'success': True,
                'is_published': quiz.is_published,
                'message': message_text
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'You do not have permission to change this quiz status.'
            }, status=403) 
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405) 


@login_required
def display_score(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    score_obj = Score.objects.filter(user=request.user, quiz=quiz).first()

    if not score_obj:
        messages.error(request, "You must complete this quiz before viewing your score.")
        return redirect('quiz:take_quiz', quiz_id=quiz.id)

    score_value = score_obj.score
    total_questions = quiz.questions.count()
    percentage = (score_value / total_questions) * 100 if total_questions > 0 else 0
    leaderboard = Score.objects.filter(quiz=quiz).select_related('user').order_by('-score')[:10]

    context = {
        'quiz': quiz,
        'score': score_value,
        'total_questions': total_questions,
        'percentage': round(percentage, 2),
        'leaderboard': leaderboard,
    }
    
    return render(request, 'quiz/quiz_result.html', context)
