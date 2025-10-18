# news/views.py
from django.shortcuts import render, redirect, get_object_or_404
from news.models import News
from news.forms import NewsForm

# @login_required # Opsional: uncomment ini jika halaman berita hanya bisa diakses setelah login
def show_news(request):
    filter_sports = request.GET.get("filter", "all")

    hot_news_for_slider = News.objects.filter(news_views__gt=20).order_by('-created_at')[:5] 
    
    news_list_queryset = News.objects.all()

    if filter_sports != "all":
        news_list_queryset = news_list_queryset.filter(sports=filter_sports)

    news_list = news_list_queryset.order_by('-is_featured', '-created_at')

    all_sports_choices = News.SPORTS_CHOICES
    
    # Ambil daftar role pengguna, sama seperti di aplikasi accounts
    roles = []
    if request.user.is_authenticated:
        roles = list(request.user.groups.values_list('name', flat=True))
    
    context = {
        'news_list': news_list,
        'featured_news': hot_news_for_slider,
        'last_login': request.COOKIES.get('last_login', 'Never'),
        'all_sports': all_sports_choices, 
        'current_filter': filter_sports, 
        'user': request.user, 
        'roles': roles, # Kirim daftar role ke templat
    }

    return render(request, "news.html", context)

def add_news(request):
    form = NewsForm(request.POST or None)

    if form.is_valid() and request.method == "POST":
        news_entry = form.save(commit=False)
        # Baris ini mungkin perlu disesuaikan jika model News Anda tidak memiliki relasi 'user'
        # news_entry.user = request.user 
        news_entry.save()
        return redirect('news:show_news')

    context = {'form': form}
    return render(request, "add_news.html", context)

def detail_news(request, news_id):
    news = get_object_or_404(News, pk=news_id)
    
    news.increment_views() 

    context = {
        'news' : news
    }
    return render(request, "detail_news.html", context)

