from django import forms

from news.models import News

from .models import DiscussionThread, DiscussionComment


class ThreadForm(forms.ModelForm):
    """Form dasar untuk membuat atau memperbarui thread diskusi."""

    news = forms.ModelChoiceField(
        queryset=News.objects.all().order_by('-created_at'),
        label='Berita terkait',
        help_text='Pilih berita yang ingin Anda diskusikan.',
        widget=forms.Select(attrs={
            'class': 'w-full rounded-lg border border-surface/20 bg-white px-3 py-2 text-sm text-surface/80 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20'
        }),
    )

    class Meta:
        model = DiscussionThread
        fields = ['news', 'title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Judul diskusi',
                'class': 'w-full rounded-lg border border-surface/20 bg-white px-3 py-2 text-sm text-surface/80 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20',
            }),
            'body': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Tulis pembuka diskusi Anda di sini',
                'class': 'w-full rounded-lg border border-surface/20 bg-white px-3 py-2 text-sm text-surface/80 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['news'].label_from_instance = lambda obj: f"{obj.title} ({obj.id})"


class CommentForm(forms.ModelForm):
    """Form sederhana untuk menambah atau mengubah komentar."""

    class Meta:
        model = DiscussionComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Sampaikan tanggapan Anda',
                'class': 'mt-1 w-full rounded-lg border border-surface/20 bg-white px-3 py-2 text-sm text-surface/80 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20',
            }),
        }
