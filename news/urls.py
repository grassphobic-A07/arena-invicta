from django.urls import path
from news.views import *

app_name = 'news'

urlpatterns = [
    path('', show_news, name='show_news'),
    path('news/<uuid:news_id>/', detail_news, name='detail_news'),
    path('create-news-ajax', add_news_ajax, name='add_news_ajax'),
    path('news/<uuid:news_id>/json-data', get_news_data_json, name='get_news_data_json'),
    path('news/<uuid:news_id>/edit_news_ajax', edit_news_ajax, name='edit_news_ajax'),
    path('news/<uuid:news_id>/delete-news-ajax', delete_news_ajax, name='delete_news_ajax'),
    path('discussions/', discussion, name='discussions'),
    path('league/', league, name='league'),
]