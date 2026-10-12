from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.me),
    path("clients/", views.client_list),
    path("audit/", views.audit_list),
    path("qbo/connect", views.oauth_connect),
    path("qbo/callback", views.oauth_callback),
    path("qbo/<slug:slug>/test", views.test_connection),
    path("qbo/<slug:slug>/disconnect", views.disconnect),
]
