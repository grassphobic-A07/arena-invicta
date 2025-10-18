from django.urls import path
from news.views import *

app_name = 'news'

urlpatterns = [
    path('', show_news, name='show_news'),
    path('add_news', add_news, name='add_news'),
    path('news/<uuid:news_id>/', detail_news, name='detail_news'),
]