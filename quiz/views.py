# quiz/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import inlineformset_factory
from .forms import QuizForm, QuestionForm
from .models import Quiz, Question, Score

def show_main(request):
    quizzes = Quiz.objects.all()
    roles = []
    authorized = False

    if request.user.is_authenticated:
        roles = list(request.user.groups.values_list('name', flat=True))
    for role in roles:
        if role == "Content Staff":
            quizzes = quizzes.filter(user=request.user)
            authorized = True
        else:
            quizzes = quizzes.filter(is_published=True)
        context = {'quizzes': quizzes, 'authorized':authorized, 'role':role}
    return render(request, "quiz/main.html", context)

def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    
    # Tambahkan .select_related('user') untuk menghindari N+1 query
    leaderboard = Score.objects.filter(quiz=quiz).select_related('user').order_by('-score')[:10]
    
    # Ambil total pertanyaan untuk ditampilkan di leaderboard
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
        extra=1, # Mulai dengan 1 form kosong saja
        can_delete=True # Izinkan penghapusan form
    )

    if request.method == 'POST':
        quiz_form = QuizForm(request.POST)
        # Tambahkan instance kosong agar formset tahu ini adalah pembuatan baru
        question_formset = QuestionFormSet(request.POST, instance=Quiz())

        if quiz_form.is_valid() and question_formset.is_valid():
            quiz = quiz_form.save(commit=False)
            quiz.user = request.user
            quiz.save()

            # Simpan formset yang terhubung dengan quiz yang baru dibuat
            question_formset.instance = quiz
            question_formset.save()

            return redirect('quiz:quiz_detail', quiz_id=quiz.id)
    else:
        quiz_form = QuizForm()
        # Tambahkan instance kosong di sini juga
        question_formset = QuestionFormSet(instance=Quiz())

    context = {
        'quiz_form': quiz_form,
        'question_formset': question_formset,
    }
    return render(request, 'quiz/create_quiz.html', context)

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.questions.all()

    if request.method == 'POST':
        score_value = 0
        total_questions = questions.count()

        for question in questions:
            # Ambil jawaban user dari data POST
            user_answer = request.POST.get(f'question_{question.id}')
            # Cek jika jawaban user sama dengan kunci jawaban
            if user_answer == question.correct_answer:
                score_value += 1
        
        # Hitung persentase
        percentage = (score_value / total_questions) * 100 if total_questions > 0 else 0
        Score.objects.update_or_create(
            user=request.user,
            quiz=quiz,
            defaults={'score':score_value},
        )
        leaderboard = Score.objects.filter(quiz=quiz).select_related('user').order_by('-score')[:10]

        context = {
            'quiz': quiz,
            'score': score_value,
            'total_questions': total_questions,
            'percentage': round(percentage, 2),
            'leaderboard':leaderboard,
        }
        # Tampilkan halaman hasil
        return render(request, 'quiz/quiz_result.html', context)

    # Jika metodenya GET, tampilkan halaman kuis

    context = {'quiz': quiz, 'questions': questions,}
    return render(request, 'quiz/take_quiz.html', context)

def deleteQuiz(request, quiz_id):
    # Pastikan hanya metode POST yang diizinkan untuk menghapus
    if request.method == 'POST':
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        
        # Tambahan: Pastikan hanya pemilik kuis yang bisa menghapus
        if quiz.user == request.user:
            quiz.delete()
            messages.success(request, f"Kuis '{quiz.title}' berhasil dihapus.")
            # Gunakan redirect setelah berhasil, bukan render
            return redirect('quiz:show_main')
        else:
            # Jika bukan pemilik, kirim pesan error (atau 403 Forbidden)
            messages.error(request, "Anda tidak memiliki izin untuk menghapus kuis ini.")
            return redirect('quiz:quiz_detail', quiz_id=quiz.id)
            
    # Jika metodenya bukan POST, arahkan kembali ke halaman detail
    return redirect('quiz:quiz_detail', quiz_id=quiz.id)

@login_required
def edit_quiz(request, quiz_id):
    # Ambil kuis yang ada, atau 404 jika tidak ditemukan
    quiz = get_object_or_404(Quiz, pk=quiz_id)

    # Otorisasi: Pastikan hanya pemilik kuis yang bisa mengedit
    if quiz.user != request.user:
        messages.error(request, "Anda tidak memiliki izin untuk mengedit kuis ini.")
        return redirect('quiz:quiz_detail', quiz_id=quiz.id)

    # Siapkan FormSet yang sama dengan create, tapi izinkan 'delete'
    QuestionFormSet = inlineformset_factory(
        Quiz, 
        Question, 
        form=QuestionForm, 
        extra=1, # Tampilkan 1 form kosong ekstra untuk menambah pertanyaan baru
        can_delete=True # Izinkan penghapusan pertanyaan yang ada
    )

    if request.method == 'POST':
        # Isi form dengan data POST dan instance kuis yang ada
        quiz_form = QuizForm(request.POST, instance=quiz)
        question_formset = QuestionFormSet(request.POST, instance=quiz)

        if quiz_form.is_valid() and question_formset.is_valid():
            quiz_form.save()
            question_formset.save() # Ini akan menangani update, create, dan delete pertanyaan
            
            messages.success(request, f"Kuis '{quiz.title}' berhasil diperbarui.")
            return redirect('quiz:quiz_detail', quiz_id=quiz.id)
        else:
            messages.error(request, "Terjadi kesalahan. Silakan periksa kembali isian Anda.")

    else: # request.method == 'GET'
        # Isi form dengan data dari instance kuis yang ada
        quiz_form = QuizForm(instance=quiz)
        question_formset = QuestionFormSet(instance=quiz)

    context = {
        'quiz_form': quiz_form,
        'question_formset': question_formset,
        'quiz': quiz # Kirim 'quiz' agar template bisa membedakan create/edit
    }
    # Gunakan template yang sama dengan 'create_quiz'
    return render(request, 'quiz/create_quiz.html', context)

@login_required
def toggle_publish(request, quiz_id):
    # Hanya izinkan metode POST
    if request.method == 'POST':
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        
        # Pastikan hanya pemilik yang bisa mengubah
        if quiz.user == request.user:
            quiz.is_published = not quiz.is_published # Balikkan status
            quiz.save()
            
            if quiz.is_published:
                messages.success(request, f"Kuis '{quiz.title}' telah dipublikasikan.")
            else:
                messages.info(request, f"Kuis '{quiz.title}' telah diubah menjadi pribadi (draft).")
        else:
            messages.error(request, "Anda tidak memiliki izin untuk mengubah status kuis ini.")
        
        return redirect('quiz:quiz_detail', quiz_id=quiz.id)
    
    # Jika GET, kembalikan ke detail
    return redirect('quiz:quiz_detail', quiz_id=quiz.id)

@login_required
def display_score(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    score = Score.objects.filter(quiz=quiz).order_by('-score')[:10]
    return 
