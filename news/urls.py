from django.urls import path
from news.views import *

app_name = 'news'

urlpatterns = [
    path('', show_news, name='show_news'),
    path('news/<uuid:news_id>/', detail_news, name='detail_news'),
    path('create-news-ajax', add_news_ajax, name='add_news_ajax'),
    path('news/<uuid:news_id>/delete', delete_news, name='delete_news'),
    path('news/<uuid:news_id>/edit', edit_news, name='edit_news'),

    path('discussions/', discussion, name='discussions'),
    path('league/', league, name='league'),
    path('quiz/', quiz, name='quiz'),
]