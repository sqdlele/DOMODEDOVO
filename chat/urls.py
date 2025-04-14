from django.urls import path
from . import views

app_name = 'chat'  

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('get_messages/', views.get_messages, name='get_messages'),
    path('chat_list/', views.get_chat_list, name='chat_list'),
    path('mark_read/', views.mark_messages_read, name='mark_read'),
]