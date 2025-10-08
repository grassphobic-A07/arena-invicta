from django.urls import path

from . import views

app_name = 'discussions'

urlpatterns = [
    path('', views.thread_list, name='thread-list'),
    path('threads/create/', views.thread_create, name='thread-create'),
    path('threads/<int:pk>/', views.thread_detail, name='thread-detail'),
    path('threads/<int:pk>/edit/', views.thread_edit, name='thread-edit'),
    path('threads/<int:pk>/delete/', views.thread_delete, name='thread-delete'),
    path('threads/<int:thread_pk>/comments/add/', views.comment_create, name='comment-create'),
    path('comments/<int:pk>/edit/', views.comment_edit, name='comment-edit'),
    path('comments/<int:pk>/delete/', views.comment_delete, name='comment-delete'),
]
