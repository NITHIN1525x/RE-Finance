from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    # Server-rendered login (CSRF-protected Django form). Reached through the Vite /api proxy.
    path("api/auth/login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("api/auth/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/", include("qbo.urls")),
]
