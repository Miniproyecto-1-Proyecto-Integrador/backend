from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    creamos registro para poder crear cuentas necesarias para
    probar el aislamiento entre organizadores fuera
    del admin de django.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "min_length": "La contraseña debe tener al menos 8 caracteres.",
            "blank": "La contraseña es obligatoria.",
            "required": "La contraseña es obligatoria.",
        },
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            "blank": "El correo es obligatorio.",
            "required": "El correo es obligatorio.",
            "invalid": "Ingresa un correo válido.",
        },
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        extra_kwargs = {
            "username": {"error_messages": {
                "blank": "El usuario es obligatorio.",
                "required": "El usuario es obligatorio.",
            }},
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Intenta utilizando otro correo.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Intenta utilizando otro nombre de usuario.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )