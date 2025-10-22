from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.urls import reverse
from news.models import News
from news.forms import NewsForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.html import strip_tags
from django.contrib import messages

def show_news(request):
    filter_sports = request.GET.get("filter", "all")
    hot_news_for_slider = News.objects.filter(news_views__gt=20).order_by('-created_at')[:5] 
    news_list_queryset = News.objects.all()
    if filter_sports != "all":
        news_list_queryset = news_list_queryset.filter(sports=filter_sports)

    news_list = news_list_queryset.order_by('-is_featured', '-created_at')
    all_sports_choices = News.SPORTS_CHOICES
    form_for_modal = NewsForm()
    context = {
        'news_list': news_list,
        'featured_news': hot_news_for_slider,
        'last_login': request.COOKIES.get('last_login', 'Never'),
        'all_sports': all_sports_choices, 
        'current_filter': filter_sports, 
        'user': request.user, 
        'news_form': form_for_modal,
    }

    return render(request, "news.html", context)

def detail_news(request, news_id):
    news = get_object_or_404(News, pk=news_id)
    news.increment_views() 
    context = {
        'news' : news
    }
    return render(request, "detail_news.html", context)

@login_required
@csrf_exempt
def edit_news(request, news_id):
    news = get_object_or_404(News, pk=news_id)
    if request.user != news.author:
        return HttpResponseForbidden("You do not have permission to edit this news.")

    if request.method == "POST":
        form = NewsForm(request.POST or None, instance=news)
        if form.is_valid():
            form.save()
            messages.success(request, f'News "{news.title}" updated successfully!')
            return redirect('news:detail_news', news_id=news.id)
    else:
        form = NewsForm(instance=news)

    context = {
        'form': form,
        'news': news
    }
    return render(request, "edit_news.html", context)

@login_required
@require_POST
def delete_news(request, news_id):
    news = get_object_or_404(News, pk=news_id)
    if request.user != news.author:
        return HttpResponseForbidden("You do not have permission to delete this news.")

    news_title = news.title
    news.delete()
    messages.success(request, f'News "{news_title}" has been deleted.')
    return redirect('news:show_news')

@login_required
@csrf_exempt
@require_POST
def add_news_ajax(request):
    if not request.user.profile.is_content_staff:
        return HttpResponseForbidden("Permission Denied.")
    title = strip_tags(request.POST.get("title", "")) 
    content = strip_tags(request.POST.get("content", "")) 
    category = request.POST.get("category", "")
    sports = request.POST.get("sports", "")
    thumbnail = request.POST.get("thumbnail", "")
    is_featured = request.POST.get("is_featured") == 'on'

    if not title or not content or not category or not sports:
        return HttpResponse(b"Missing required fields (Title, Content, Category, Sports)", status=400)
    
    try:
        new_news = News(
            title=title,
            content=content,
            category=category,
            sports=sports,
            thumbnail=thumbnail if thumbnail else None,
            is_featured=is_featured,
            author=request.user
        )
        new_news.save()
        return HttpResponse(b"CREATED", status=201)
    
    except Exception as e:
        print(f"Error saving news via AJAX: {e}") # Log errornya
        return HttpResponse(b"Internal Server Error", status=500)
    

# DUMMY
def discussion(request):
    context = {
        'page-title': "Discussions"
    }
    return render(request, "discussions.html", context)

def league(request):
    context = {
        'page-title': "League"
    }
    return render(request, "league.html", context)