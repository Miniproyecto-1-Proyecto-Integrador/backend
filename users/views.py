from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import EmailOrUsernameTokenObtainPairSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/  (publico)"""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/  (publico)
    Body: {"username": "<correo o usuario>", "password": "..."}
    -> 200 {"access": "...", "refresh": "...", "user": {...}}
    -> 401 {"detail": "Correo o contraseña incorrectos."}
    """
    serializer_class = EmailOrUsernameTokenObtainPairSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    """
    GET /api/auth/me/  (requiere access token)
    Usado por el front para verificar si la sesion sigue activa al entrar
    a una ruta protegida y para recuperar los datos
    del usuario tras recargar la pagina.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {"id": user.id, "username": user.username, "email": user.email},
            status=status.HTTP_200_OK,
        )