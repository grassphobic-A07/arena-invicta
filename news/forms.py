from django.forms import ModelForm
from news.models import News

class NewsForm(ModelForm):
    class Meta:
        model = News
        fields = ["title", "content", "category", "sports", "thumbnail", "is_featured"]