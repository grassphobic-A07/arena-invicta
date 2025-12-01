from django import forms
from .models import Quiz, Question

class QuizForm(forms.ModelForm):
    """
    Form to create and edit a quiz
    """
    class Meta:
        model = Quiz

        fields = ['title', 'description', 'category', 'is_published']
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Example: Sports Quiz'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'A brief description of this quiz.'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
        }
        
        labels = {
            'title': 'Quiz Title',
            'description': 'Description',
            'category': 'Category',
        }


class QuestionForm(forms.ModelForm):
    """
    Form to create and edit a Question within a Quiz.
    """
    class Meta:
        model = Question

        fields = ['text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']

        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 3,
                'placeholder': 'Write the question here...'
            }),
            'option_a': forms.TextInput(attrs={'placeholder': 'Answer A'}),
            'option_b': forms.TextInput(attrs={'placeholder': 'Answer B'}),
            'option_c': forms.TextInput(attrs={'placeholder': 'Answer C'}),
            'option_d': forms.TextInput(attrs={'placeholder': 'Answer D'}),
            'correct_answer': forms.RadioSelect(),
        }
        
        labels = {
            'text': 'Question Text',
            'option_a': 'Option A',
            'option_b': 'Option B',
            'option_c': 'Option C',
            'option_d': 'Option D',
            'correct_answer': 'Correct Answer Key',
        }
