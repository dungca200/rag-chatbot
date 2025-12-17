from django.urls import path
from rag import views

urlpatterns = [
    path('documents/query', views.ChatbotView.as_view()),
    path('documents/classify', views.DocumentClassifierView.as_view())
]