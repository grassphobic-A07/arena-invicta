# quiz/models.py
from django.contrib.auth.models import User
from django.db import models

# Create your models here.
class Quiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ])

    def __str__(self):
        return f"{self.quiz.title} - {self.text[:50]}"
    
class Score(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="scores")
    score = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'quiz')  # One score per user per quiz

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}: {self.score}"