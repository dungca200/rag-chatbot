"""URL configuration for RAG Chatbot project."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/', include('apps.chatbot.urls')),
    path('api/documents/', include('apps.documents.urls')),
]
