from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
]