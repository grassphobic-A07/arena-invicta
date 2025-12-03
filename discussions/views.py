import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import ThreadForm, CommentForm
from .models import DiscussionThread, DiscussionComment, DiscussionThreadUpvote


def thread_list(request):
    query = request.GET.get('q', '').strip()
    threads_qs = _filter_threads(_thread_queryset(), query)
    threads = list(threads_qs)
    for thread in threads:
        profile = getattr(thread.author, 'profile', None)
        thread.author_profile = profile
        thread.author_display = (
            getattr(profile, 'display_name', None)
            or thread.author.get_full_name()
            or thread.author.get_username()
        )
    context = {
        'threads': threads,
        'search_query': query,
        'thread_form': ThreadForm(),
        'api_list_url': reverse('discussions:thread-list-api'),
        'api_create_url': reverse('discussions:thread-create-api'),
    }
    return render(request, 'discussions/thread_list.html', context)


@require_GET
def thread_list_api(request):
    query = request.GET.get('q', '').strip()
    threads = _filter_threads(_thread_queryset(), query)
    payload = [_serialize_thread(thread) for thread in threads]
    if _should_return_xml(request):
        xml_payload = _threads_to_xml(payload)
        return HttpResponse(xml_payload, content_type='application/xml')
    return JsonResponse({'threads': payload})


@require_GET
def thread_detail_api(request, pk):
    thread = get_object_or_404(_thread_queryset(), pk=pk)
    DiscussionThread.objects.filter(pk=thread.pk).update(views_count=F('views_count') + 1)
    thread.views_count = (thread.views_count or 0) + 1
    
    comments_qs = thread.comments.filter(is_removed=False).select_related(
        'author', 'author__profile', 'parent', 'parent__author', 'parent__author__profile'
    )
    comments = []
    for comment in comments_qs:
        profile = getattr(comment.author, 'profile', None)
        avatar_url = getattr(profile, 'avatar_url', '') or None
        display_name = getattr(profile, 'display_name', '') or ''
        comments.append({
            'id': comment.pk,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'parent_id': comment.parent_id,
            'author': {
                'username': comment.author.get_username(),
                'display_name': display_name or comment.author.get_full_name() or comment.author.get_username(),
                'avatar_url': avatar_url,
            },
        })
    
    user_has_upvoted = False
    if request.user.is_authenticated:
        user_has_upvoted = DiscussionThreadUpvote.objects.filter(thread=thread, user=request.user).exists()
    
    thread_data = _serialize_thread(thread)
    thread_data['user_has_upvoted'] = user_has_upvoted
    
    return JsonResponse({
        'thread': thread_data,
        'comments': comments,
    })


def thread_detail(request, pk):
    thread = get_object_or_404(_thread_queryset(), pk=pk)
    DiscussionThread.objects.filter(pk=thread.pk).update(views_count=F('views_count') + 1)
    thread.views_count = (thread.views_count or 0) + 1
    comments_qs = thread.comments.filter(is_removed=False).select_related('author', 'author__profile', 'parent', 'parent__author', 'parent__author__profile')
    comments = list(comments_qs)
    for comment in comments:
        profile = getattr(comment.author, 'profile', None)
        comment.author_profile = profile
        comment.author_display = (
            getattr(profile, 'display_name', None)
            or comment.author.get_full_name()
            or comment.author.get_username()
        )
    thread_author_profile = getattr(thread.author, 'profile', None)
    thread_author_display = (
        getattr(thread_author_profile, 'display_name', None)
        or thread.author.get_full_name()
        or thread.author.get_username()
    )
    comment_form = CommentForm()
    user_has_upvoted = False
    if request.user.is_authenticated:
        user_has_upvoted = DiscussionThreadUpvote.objects.filter(thread=thread, user=request.user).exists()

    upvote_count = getattr(thread, 'upvote_count', None)
    if upvote_count is None:
        upvote_count = thread.upvotes.count()

    context = {
        'thread': thread,
        'comments': comments,
        'comment_form': comment_form,
        'thread_author_profile': thread_author_profile,
        'thread_author_display': thread_author_display,
        'upvote_count': upvote_count,
        'user_has_upvoted': user_has_upvoted,
    }
    return render(request, 'discussions/thread_detail.html', context)


@login_required
def thread_create(request):
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user
            thread.save()
            return redirect('discussions:thread-detail', pk=thread.pk)
    else:
        form = ThreadForm()
    return render(request, 'discussions/thread_form.html', {'form': form})


@login_required
def thread_edit(request, pk):
    thread = get_object_or_404(DiscussionThread, pk=pk)
    if not _can_manage_thread(request.user, thread):
        raise PermissionDenied

    if request.method == 'POST':
        form = ThreadForm(request.POST, instance=thread)
        if form.is_valid():
            form.save()
            return redirect('discussions:thread-detail', pk=thread.pk)
    else:
        form = ThreadForm(instance=thread)
    return render(request, 'discussions/thread_form.html', {'form': form, 'thread': thread})


@login_required
def thread_delete(request, pk):
    thread = get_object_or_404(DiscussionThread, pk=pk)
    if not _can_manage_thread(request.user, thread):
        raise PermissionDenied

    if request.method == 'POST':
        thread.delete()
        return redirect('discussions:thread-list')

    return render(request, 'discussions/thread_confirm_delete.html', {'object': thread})


@login_required
@require_POST
@csrf_exempt
def thread_create_api(request):
    if request.content_type == 'application/json':
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Payload tidak valid.'}, status=400)
        form = ThreadForm(payload)
    else:
        form = ThreadForm(request.POST)

    if form.is_valid():
        thread = form.save(commit=False)
        thread.author = request.user
        thread.save()
        thread = _thread_queryset().get(pk=thread.pk)
        serialized = _serialize_thread(thread)
        serialized['upvote_count'] = 0
        serialized['views_count'] = thread.views_count
        return JsonResponse(
            {
                'ok': True,
                'message': 'Diskusi berhasil dibuat.',
                'thread': serialized,
            },
            status=201,
        )

    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
def comment_create(request, thread_pk):
    thread = get_object_or_404(DiscussionThread, pk=thread_pk)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.thread = thread
            parent_id = request.POST.get('parent')
            if parent_id:
                comment.parent = get_object_or_404(DiscussionComment, pk=parent_id, thread=thread)
            comment.save()
            return redirect('discussions:thread-detail', pk=thread.pk)
    else:
        form = CommentForm()

    return render(
        request,
        'discussions/comment_form.html',
        {'form': form, 'thread': thread},
    )


@login_required
@require_POST
@csrf_exempt
def comment_create_api(request, thread_pk):
    thread = get_object_or_404(DiscussionThread, pk=thread_pk)
    
    if request.content_type == 'application/json':
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Payload tidak valid.'}, status=400)
        form = CommentForm(payload)
        parent_id = payload.get('parent')
    else:
        form = CommentForm(request.POST)
        parent_id = request.POST.get('parent')
    
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.thread = thread
        if parent_id:
            comment.parent = get_object_or_404(DiscussionComment, pk=parent_id, thread=thread)
        comment.save()
        
        profile = getattr(request.user, 'profile', None)
        avatar_url = getattr(profile, 'avatar_url', '') or None
        display_name = getattr(profile, 'display_name', '') or ''
        
        return JsonResponse({
            'ok': True,
            'comment': {
                'id': comment.pk,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'parent_id': comment.parent_id,
                'author': {
                    'username': request.user.get_username(),
                    'display_name': display_name or request.user.get_full_name() or request.user.get_username(),
                    'avatar_url': avatar_url,
                },
            },
        }, status=201)
    
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)


@login_required
def comment_edit(request, pk):
    comment = get_object_or_404(DiscussionComment.objects.select_related('thread'), pk=pk)
    if not _can_manage_comment(request.user, comment):
        raise PermissionDenied
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept', '').startswith('application/json')

    if request.method == 'GET':
        form = CommentForm(instance=comment)
        if is_ajax:
            return JsonResponse({'ok': True, 'content': comment.content})
        return render(
            request,
            'discussions/comment_form.html',
            {'form': form, 'thread': comment.thread, 'comment': comment},
        )

    form = CommentForm(request.POST, instance=comment)
    if form.is_valid():
        form.save()
        if is_ajax:
            return JsonResponse({'ok': True, 'content': comment.content})
        return redirect('discussions:thread-detail', pk=comment.thread.pk)

    if is_ajax:
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    return render(
        request,
        'discussions/comment_form.html',
        {'form': form, 'thread': comment.thread, 'comment': comment},
    )


@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(DiscussionComment.objects.select_related('thread'), pk=pk)
    if not _can_manage_comment(request.user, comment):
        raise PermissionDenied

    if request.method == 'POST':
        thread_pk = comment.thread.pk
        comment.delete()
        return redirect('discussions:thread-detail', pk=thread_pk)

    return render(
        request,
        'discussions/comment_confirm_delete.html',
        {'object': comment, 'thread': comment.thread},
    )


@login_required
@require_POST
@csrf_exempt
def thread_toggle_upvote(request, pk):
    thread = get_object_or_404(DiscussionThread, pk=pk)
    upvote, created = DiscussionThreadUpvote.objects.get_or_create(thread=thread, user=request.user)
    if created:
        state = 'added'
    else:
        upvote.delete()
        state = 'removed'

    upvote_count = thread.upvotes.count()
    payload = {'ok': True, 'state': state, 'upvote_count': upvote_count}

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept', '').startswith('application/json'):
        return JsonResponse(payload)

    return redirect('discussions:thread-detail', pk=pk)


@login_required
@require_POST
@csrf_exempt
def thread_toggle_upvote_api(request, pk):
    """API endpoint for mobile - always returns JSON"""
    thread = get_object_or_404(DiscussionThread, pk=pk)
    upvote, created = DiscussionThreadUpvote.objects.get_or_create(thread=thread, user=request.user)
    if created:
        state = 'added'
    else:
        upvote.delete()
        state = 'removed'

    upvote_count = thread.upvotes.count()
    return JsonResponse({'ok': True, 'state': state, 'upvote_count': upvote_count})


def _can_manage_thread(user, thread):
    return user.is_authenticated and (thread.author == user or user.is_staff)


def _can_manage_comment(user, comment):
    return user.is_authenticated and (comment.author == user or user.is_staff)


def _thread_queryset():
    return (
        DiscussionThread.objects.select_related('author', 'author__profile', 'news')
        .annotate(
            comment_count=Count(
                'comments',
                filter=Q(comments__is_removed=False),
            ),
            upvote_count=Count('upvotes', distinct=True),
        )
    )


def _filter_threads(queryset, query):
    if query:
        queryset = queryset.filter(
            Q(news__title__icontains=query)
            | Q(news__id__icontains=query)
        )
    return queryset


def _serialize_thread(thread):
    profile = getattr(thread.author, 'profile', None)
    avatar_url = getattr(profile, 'avatar_url', '') or None
    display_name = getattr(profile, 'display_name', '') or ''
    news = thread.news

    return {
        'id': thread.pk,
        'title': thread.title,
        'body': thread.body,
        'created_at': thread.created_at.isoformat(),
        'is_locked': thread.is_locked,
        'is_pinned': thread.is_pinned,
        'views_count': getattr(thread, 'views_count', 0),
        'upvote_count': getattr(thread, 'upvote_count', thread.upvotes.count() if hasattr(thread, 'upvotes') else 0),
        'comment_count': getattr(thread, 'comment_count', 0),
        'detail_url': reverse('discussions:thread-detail', args=[thread.pk]),
        'news': {
            'uuid': str(news.id) if news else None,
            'title': news.title if news else None,
            'detail_url': reverse('news:detail_news', kwargs={'news_id': news.id}) if news else None,
            'summary': _news_excerpt(news),
        } if news else None,
        'author': {
            'username': thread.author.get_username(),
            'display_name': display_name or thread.author.get_full_name() or thread.author.get_username(),
            'avatar_url': avatar_url,
        },
    }


def _news_excerpt(news, word_limit=24):
    if not news or not getattr(news, 'content', None):
        return ''
    text = (news.content or '').strip()
    if not text:
        return ''
    words = text.split()
    if len(words) <= word_limit:
        return text
    return ' '.join(words[:word_limit]) + '…'


def _should_return_xml(request):
    """
    Decide whether the response should be XML based on `format` query param
    or explicit Accept header preference.
    """
    fmt = (request.GET.get('format') or '').lower()
    if fmt == 'xml':
        return True
    if fmt == 'json':
        return False
    accept_header = request.headers.get('accept', '')
    accepted_types = [part.strip() for part in accept_header.split(',') if part.strip()]
    first_type = accepted_types[0] if accepted_types else ''
    return first_type.startswith('application/xml') or first_type.startswith('text/xml')


def _threads_to_xml(serialized_threads):
    root = Element('threads')
    for thread in serialized_threads:
        thread_el = SubElement(root, 'thread')
        _dict_to_xml(thread_el, thread)
    return tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')


def _dict_to_xml(parent, data):
    for key, value in data.items():
        if value is None:
            continue
        child = SubElement(parent, key)
        if isinstance(value, dict):
            _dict_to_xml(child, value)
        else:
            child.text = str(value)
from xml.etree.ElementTree import Element, SubElement, tostring
