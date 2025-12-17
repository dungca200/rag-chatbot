from django.urls import path

from . import views

urlpatterns = [
    path('upload/', views.upload_document, name='upload_document'),
    path('', views.list_documents, name='list_documents'),
    path('<uuid:document_id>/', views.get_document, name='get_document'),
    path('<uuid:document_id>/delete/', views.delete_document, name='delete_document'),
]
