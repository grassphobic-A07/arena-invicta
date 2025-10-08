from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ThreadForm, CommentForm
from .models import DiscussionThread, DiscussionComment


def thread_list(request):
    threads = DiscussionThread.objects.select_related('author')
    context = {'threads': threads}
    return render(request, 'discussions/thread_list.html', context)


def thread_detail(request, pk):
    thread = get_object_or_404(DiscussionThread.objects.select_related('author'), pk=pk)
    comments = thread.comments.filter(is_removed=False).select_related('author', 'parent')
    comment_form = CommentForm()
    context = {
        'thread': thread,
        'comments': comments,
        'comment_form': comment_form,
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
def comment_edit(request, pk):
    comment = get_object_or_404(DiscussionComment.objects.select_related('thread'), pk=pk)
    if not _can_manage_comment(request.user, comment):
        raise PermissionDenied

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('discussions:thread-detail', pk=comment.thread.pk)
    else:
        form = CommentForm(instance=comment)

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


def _can_manage_thread(user, thread):
    return user.is_authenticated and (thread.author == user or user.is_staff)


def _can_manage_comment(user, comment):
    return user.is_authenticated and (comment.author == user or user.is_staff)
