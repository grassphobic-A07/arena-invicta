# quiz/forms.py
from django import forms
from .models import Quiz, Question

class QuizForm(forms.ModelForm):
    """
    Form untuk membuat dan mengedit sebuah Quiz.
    """
    class Meta:
        model = Quiz
        # Tentukan field mana dari model yang ingin ditampilkan di form.
        # 'user' dan 'created_at' diatur secara otomatis, jadi tidak perlu dimasukkan.
        fields = ['title', 'description', 'is_published']
        
        # (Opsional) Menambahkan atribut ke elemen HTML untuk styling.
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Contoh: Kuis Pengetahuan Olahraga'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'Deskripsi singkat tentang kuis ini.'
            }),
        }
        
        # (Opsional) Mengubah label default yang ditampilkan.
        labels = {
            'title': 'Judul Kuis',
            'description': 'Deskripsi',
        }


class QuestionForm(forms.ModelForm):
    """
    Form untuk membuat dan mengedit sebuah Pertanyaan dalam sebuah Quiz.
    """
    class Meta:
        model = Question
        # 'quiz' akan dihubungkan di dalam view, jadi kita tidak menampilkannya di form.
        fields = ['text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']

        # Menggunakan RadioSelect untuk pilihan jawaban agar lebih intuitif.
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3   ,
                'placeholder': 'Tuliskan pertanyaan di sini...'
            }),
            'option_a': forms.TextInput(attrs={'placeholder': 'Jawaban A'}),
            'option_b': forms.TextInput(attrs={'placeholder': 'Jawaban B'}),
            'option_c': forms.TextInput(attrs={'placeholder': 'Jawaban C'}),
            'option_d': forms.TextInput(attrs={'placeholder': 'Jawaban D'}),
            'correct_answer': forms.RadioSelect(), # Ini akan merender pilihan A, B, C, D sebagai radio button.
        }
        
        labels = {
            'text': 'Teks Pertanyaan',
            'option_a': 'Pilihan A',
            'option_b': 'Pilihan B',
            'option_c': 'Pilihan C',
            'option_d': 'Pilihan D',
            'correct_answer': 'Kunci Jawaban yang Benar',
        }