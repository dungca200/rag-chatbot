"""URL configuration for RAG Chatbot project."""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

from apps.chatbot.urls import admin_urlpatterns


def health_check(request):
    """Health check endpoint for container orchestration."""
    return JsonResponse({'status': 'healthy'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/chat/', include('apps.chatbot.urls')),
    path('api/documents/', include('apps.documents.urls')),
    path('api/admin/', include(admin_urlpatterns)),
]
