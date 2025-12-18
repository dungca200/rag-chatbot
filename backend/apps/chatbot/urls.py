from django.urls import path

from . import views

urlpatterns = [
    # Chat endpoints (BE-030)
    path('', views.chat_stream, name='chat_stream'),
    path('sync/', views.chat_sync, name='chat_sync'),

    # Conversation history (BE-032)
    path('conversations/', views.list_conversations, name='list_conversations'),
    path('conversations/<uuid:conversation_id>/', views.get_conversation, name='get_conversation'),
    path('conversations/<uuid:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),

    # Document-specific conversation
    path('conversations/document/<str:document_key>/', views.document_conversation, name='document_conversation'),
]

# Admin URLs (BE-034)
admin_urlpatterns = [
    path('stats/', views.admin_stats, name='admin_stats'),
    path('users/', views.admin_users, name='admin_users'),
]
