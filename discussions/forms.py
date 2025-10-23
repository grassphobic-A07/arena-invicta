from django import forms

from .models import DiscussionThread, DiscussionComment


class ThreadForm(forms.ModelForm):
    """Form dasar untuk membuat atau memperbarui thread diskusi."""

    class Meta:
        model = DiscussionThread
        fields = ['title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Judul diskusi'}),
            'body': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Tulis pembuka diskusi Anda di sini'}),
        }


class CommentForm(forms.ModelForm):
    """Form sederhana untuk menambah atau mengubah komentar."""

    class Meta:
        model = DiscussionComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Sampaikan tanggapan Anda'}),
        }
