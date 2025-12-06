from django.shortcuts import render, redirect, get_object_or_404 # type: ignore
from django.contrib.auth.decorators import login_required # type: ignore
from django.contrib import messages # type: ignore
from django.forms import inlineformset_factory # type: ignore
from django.http import JsonResponse # type: ignore
from django.template.loader import render_to_string # type: ignore
from django.urls import reverse # type: ignore
from django.views.decorators.csrf import csrf_exempt # type: ignore
from .forms import QuizForm, QuestionForm 
from .models import Quiz, Question, Score
from django.db.models import Count, Q # type: ignore
import json

# Helper function to detect AJAX requests
def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'

@login_required
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
            messages()
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

def calculate_quiz_result(quiz, user, answers_dict):
    """
    Calculates score and handles 'High Score' logic.
    answers_dict: Dictionary where key is question_id (str or int) and value is the answer char.
    """
    score = 0
    results = []
    questions = quiz.questions.all()
    total_questions = questions.count()

    # 1. Grade the Quiz
    for question in questions:
        # Handle string keys from JSON or Form data
        user_answer = answers_dict.get(str(question.id))
        is_correct = user_answer == question.correct_answer
        
        if is_correct:
            score += 1
            
        results.append({
            "question_id": question.id,
            "correct": is_correct
        })

    # 2. Save Score (Only if User is Authenticated)
    if user.is_authenticated:
        # Check existing score to ensure we only save the highest
        old_score_obj = Score.objects.filter(user=user, quiz=quiz).first()
        old_score_value = old_score_obj.score if old_score_obj else 0

        # Only update if the new score is higher, or if no score exists
        final_score = max(score, old_score_value)
        
        Score.objects.update_or_create(
            user=user,
            quiz=quiz,
            defaults={'score': final_score}
        )
    
    return score, total_questions, results

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.questions.all()

    if request.method == 'POST':

        answers = {}
        for key, value in request.POST.items():
            if (key.startswith('question_')):
                q_id = key.split('_')[1]
                answers[q_id] = value

        score_value, total_questions, _ = calculate_quiz_result(quiz, request.user, answers)
        
        percentage = (score_value / total_questions) * 100 if total_questions > 0 else 0
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
                message_text = f"Quiz '{quiz.title}' has been set to private."
            
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

def quiz_admin_detail(request, quiz_id):
    quiz = Quiz.objects.get(id=quiz_id)

    if quiz.user != request.user:
        return JsonResponse({"error": "Forbidden"}, status=403)

    answers = []
    for q in quiz.questions.all():
        answers.append({
            "question_id": q.id,
            "correct_answer": q.correct_answer
        })

    scores = [
        {
            "user": s.user.username,
            "score": s.score
        }
        for s in quiz.scores.all()
    ]

    return JsonResponse({
        "id": quiz.id,
        "title": quiz.title,
        "correct_answers": answers,
        "scores": scores
    })

def quiz_admin_quizzez(request):
    roles = []  

    if request.user.is_authenticated:
        roles = list(request.user.groups.values_list('name', flat=True))

    if "Content Staff" not in roles:
        return JsonResponse({"error": "Forbidden"}, status=403)
    quiz = Quiz.objects.filter(user=request.user).annotate(
        question_count=Count('questions', distinct=True),
        score_count=Count('scores', distinct=True),
    )
    data = []
    for q in quiz:
        data.append({
            'id':q.id,
            'title':q.title,
            'description':q.description,
            'category': q.category,
            'is_quiz_hot': q.score_count >= 5,
            'total_question': q.question_count,
            'is_published': q.is_published,
        })
    return JsonResponse(data, safe=False)

def get_all_quizzes(request):
    quizzes = Quiz.objects.filter(is_published=True).select_related('user').annotate(
        question_count=Count('questions', distinct=True),
        score_count=Count('scores', distinct=True),
    )
    category = request.GET.get("category")
    search = request.GET.get("search")
    created_by = request.GET.get("created_by")

    if category:
        quizzes = quizzes.filter(category__iexact=category)

    if search:
        quizzes = quizzes.filter(title__icontains=search)

    if created_by:
        quizzes = quizzes.filter(user__username__iexact=created_by)

    data = []

    for q in quizzes:
        is_hot = q.score_count >= 5
        data.append({
            "id": q.id,
            "title": q.title,
            "description": q.description,
            "category": q.category,
            "is_quiz_hot": is_hot,
            "total_questions": q.question_count,
            "created_by": q.user.username,
        })

    return JsonResponse(data, safe=False)

@csrf_exempt
@login_required
def create_quiz_flutter(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 1. Create Quiz
            quiz = Quiz.objects.create(
                user=request.user,
                title=data.get('title'),
                description=data.get('description', ''),
                category=data.get('category', 'football'),
                is_published=data.get('is_published', False)
            )

            # 2. Create Questions
            questions_data = data.get('questions', [])
            for q_data in questions_data:
                Question.objects.create(
                    quiz=quiz,
                    text=q_data['text'],
                    option_a=q_data['option_a'],
                    option_b=q_data['option_b'],
                    option_c=q_data['option_c'],
                    option_d=q_data['option_d'],
                    correct_answer=q_data['correct_answer']
                )

            return JsonResponse({"status": "success", "message": "Quiz created successfully!"}, status=200)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=401)


@csrf_exempt
@login_required
def edit_quiz_flutter(request, quiz_id):
    if request.method == 'POST':
        try:
            quiz = Quiz.objects.get(pk=quiz_id)
            if quiz.user != request.user:
                return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)

            data = json.loads(request.body)

            # 1. Update Quiz Fields
            quiz.title = data.get('title', quiz.title)
            quiz.description = data.get('description', quiz.description)
            quiz.category = data.get('category', quiz.category)
            quiz.is_published = data.get('is_published', quiz.is_published)
            quiz.save()

            # 2. Handle Questions (Complex: Add, Edit, Delete)
            questions_data = data.get('questions', [])
            
            # Logic: We replace all questions for simplicity and robustness in API
            # ensuring the order and data matches exactly what the user sent.
            # Alternatively, you can implement ID matching, but wiping and recreating 
            # for a small quiz app is cleaner for sync.
            quiz.questions.all().delete() 

            for q_data in questions_data:
                Question.objects.create(
                    quiz=quiz,
                    text=q_data['text'],
                    option_a=q_data['option_a'],
                    option_b=q_data['option_b'],
                    option_c=q_data['option_c'],
                    option_d=q_data['option_d'],
                    correct_answer=q_data['correct_answer']
                )

            return JsonResponse({"status": "success", "message": "Quiz updated successfully!"}, status=200)

        except Quiz.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Quiz not found"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=401)


@csrf_exempt
@login_required
def delete_quiz_flutter(request, quiz_id):
    if request.method == 'POST':
        try:
            quiz = Quiz.objects.get(pk=quiz_id)
            if quiz.user != request.user:
                return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)
            
            quiz.delete()
            return JsonResponse({"status": "success", "message": "Quiz deleted successfully!"}, status=200)
        
        except Quiz.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Quiz not found"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=401)

@login_required
def get_quiz_for_edit_flutter(request, quiz_id):
    """
    Returns full quiz details including questions for the Edit Form.
    """
    try:
        quiz = Quiz.objects.get(pk=quiz_id)
        if quiz.user != request.user:
            return JsonResponse({"status": "error", "message": "Permission denied"}, status=403)
        
        questions = []
        for q in quiz.questions.all():
            questions.append({
                "text": q.text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_answer": q.correct_answer
            })
            
        return JsonResponse({
            "status": "success",
            "data": {
                "title": quiz.title,
                "description": quiz.description,
                "category": quiz.category,
                "is_published": quiz.is_published,
                "questions": questions
            }
        }, status=200)
    except Quiz.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Quiz not found"}, status=404)
    
def get_quiz_detail(request, quiz_id):
    quiz = Quiz.objects.get(id=quiz_id, is_published=True)

    questions = []
    for q in quiz.questions.all():
        questions.append({
            "id": q.id,
            "text": q.text,
            "options": {
                "A": q.option_a,
                "B": q.option_b,
                "C": q.option_c,
                "D": q.option_d,
            }
        })

    # Get Leaderboard
    leaderboard_qs = Score.objects.filter(quiz=quiz).select_related('user').order_by('-score')[:10]
    leaderboard = [{"user": s.user.username, "score": s.score} for s in leaderboard_qs]

    data = {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "questions": questions,
        "leaderboard": leaderboard, # Added this
    }

    return JsonResponse(data)

@csrf_exempt
def submit_quiz(request, quiz_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    quiz = Quiz.objects.get(id=quiz_id, is_published=True)
    body = json.loads(request.body.decode())
    answers = body.get("answers", {})

    score, total, results = calculate_quiz_result(quiz, request.user, answers)

    # Get Updated Leaderboard after score calculation
    leaderboard_qs = Score.objects.filter(quiz=quiz).select_related('user').order_by('-score')[:10]
    leaderboard = [{"user": s.user.username, "score": s.score} for s in leaderboard_qs]

    return JsonResponse({
        "score": score,
        "total": total,
        "result": results,
        "leaderboard": leaderboard, # Added this
    })