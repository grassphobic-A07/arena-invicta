from django.contrib import admin

from .models import DiscussionThread, DiscussionComment


@admin.register(DiscussionThread)
class DiscussionThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_locked', 'is_pinned', 'created_at')
    list_filter = ('is_locked', 'is_pinned', 'created_at')
    search_fields = ('title', 'body', 'author__username')
    ordering = ('-is_pinned', '-created_at')


@admin.register(DiscussionComment)
class DiscussionCommentAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'parent', 'is_removed', 'created_at')
    list_filter = ('is_removed', 'created_at')
    search_fields = ('content', 'author__username', 'thread__title')
    ordering = ('created_at',)
