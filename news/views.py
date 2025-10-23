from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.urls import reverse
from news.models import News
from news.forms import NewsForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
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
    form_for_modal_choices = NewsForm()
    context = {
        'news' : news,
        'news_form' : form_for_modal_choices
    }
    return render(request, "detail_news.html", context)

@require_GET
def get_news_data_json(request, news_id):
    try:
        news = News.objects.get(pk=news_id)
        data = {
            'id': str(news.id),
            'title': news.title,
            'content': news.content,
            'category': news.category,
            'sports': news.sports,
            'thumbnail': news.thumbnail,
            'is_featured': news.is_featured
        }
        return JsonResponse(data)
    except News.DoesNotExist:
        return JsonResponse({'error': 'News not found'}, status=404)
    except Exception as e:
        print(f"Error fetching news JSON: {e}")
        return JsonResponse({'error': 'Server error fetching data'}, status=500)

@login_required
@require_POST
@csrf_exempt
def edit_news_ajax(request, news_id):
    news = get_object_or_404(News, pk=news_id)
    if request.user != news.author:
        return JsonResponse({'ok': False, 'error': 'Permission denied.'}, status=403)
    
    form = NewsForm(request.POST or None, instance=news)
    if form.is_valid():
        try:
            updated_news = form.save()
            redirect_url = reverse('news:detail_news', kwargs={'news_id': updated_news.id})
            return JsonResponse({
                'ok': True,
                'message': f'News "{updated_news.title}" updated successfully!',
                'redirect_url': redirect_url
            })
        except Exception as e:
            print(f"Error updating news via AJAX: {e}")
            return JsonResponse({'ok': False, 'error': 'Could not update news.'}, status=500)
    else:
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
        

@login_required
@require_POST
@csrf_exempt
def delete_news_ajax(request, news_id):
    news = get_object_or_404(News, pk=news_id)
    if request.user != news.author:
        return JsonResponse({'ok': False, 'error': 'Permission Denied.'}, status=403)
    
    try:
        news_title = news.title # Untuk pesan
        news.delete()

        success_msg = f'News "{news_title}" has been deleted.'
        redirect_url = reverse('news:show_news')

        return JsonResponse({
            'ok': True,
            'message': success_msg,
            'redirect_url': redirect_url
        })
    except Exception as e:
        print(f"Error deleting news via AJAX: {e}")
        return JsonResponse({'ok': False, 'error': 'Could not delete this news.'}, status=500)

@login_required
@csrf_exempt
@require_POST
def add_news_ajax(request):
    if not request.user.profile.is_content_staff:
        return JsonResponse({'error': 'Permission Denied.'}, status=403)
    
    title = strip_tags(request.POST.get("title", "")) 
    content = strip_tags(request.POST.get("content", "")) 
    category = request.POST.get("category", "")
    sports = request.POST.get("sports", "")
    thumbnail = request.POST.get("thumbnail", "")
    is_featured = request.POST.get("is_featured") == 'on'

    if not title or not content or not category or not sports:
        return JsonResponse({'error': 'Missing required fields (Title, Content, Category, Sports)'}, status=400)
    
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

        news_data = {
            'id': str(new_news.id),
            'title': new_news.title,
            # 'content': new_news.content, # Biasanya tidak perlu konten lengkap di list
            'category_display': new_news.get_category_display(),
            'sports_display': new_news.get_sports_display(),
            'thumbnail': new_news.thumbnail,
            'detail_url': reverse('news:detail_news', args=[new_news.id])
        }
        return JsonResponse(news_data, status=201)
    
    except Exception as e:
        print(f"Error saving news via AJAX: {e}")
        return JsonResponse({'error': 'Internal Server Error'}, status=500)
    

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

def quiz(request):
    context = {
        'page-title' : 'Quiz'
    }
    return render(request, "quiz.html", context)