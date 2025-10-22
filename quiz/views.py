# quiz/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.forms import inlineformset_factory
from .forms import QuizForm, QuestionForm
from .models import Quiz, Question

# ... (show_main, quiz_detail, create_quiz_with_questions tetap sama) ...

def show_main(request):
    quizzes = Quiz.objects.all()
    roles = []
    authorized = False
    if request.user.is_authenticated:
        roles = list(request.user.groups.values_list('name', flat=True))

    for role in roles:
        if role == "Writer":
            authorized = True
    context = {'quizzes': quizzes, 'authorized':authorized}
    return render(request, "quiz/main.html", context)

def quiz_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    context = {'quiz': quiz}
    return render(request, 'quiz/quiz_detail.html', context)

@login_required
def create_quiz_with_questions(request):
    # Ubah baris di bawah ini
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

# 👇 FUNGSI BARU UNTUK MENGERJAKAN KUIS 👇
@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    questions = quiz.questions.all()

    if request.method == 'POST':
        score = 0
        total_questions = questions.count()

        for question in questions:
            # Ambil jawaban user dari data POST
            user_answer = request.POST.get(f'question_{question.id}')
            # Cek jika jawaban user sama dengan kunci jawaban
            if user_answer == question.correct_answer:
                score += 1
        
        # Hitung persentase
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0

        context = {
            'quiz': quiz,
            'score': score,
            'total_questions': total_questions,
            'percentage': round(percentage, 2),
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