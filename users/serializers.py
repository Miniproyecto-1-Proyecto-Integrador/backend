from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework.validators import UniqueValidator
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

    username = serializers.CharField(
        max_length=150,
        validators=[
            UnicodeUsernameValidator(message="Usa solo letras, números y @/./+/-/_."),
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",
                message="Intenta utilizando otro nombre de usuario.",
            ),
        ],
        error_messages={
            "blank": "El usuario es obligatorio.",
            "required": "El usuario es obligatorio.",
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

class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Permite iniciar sesión con correo o con nombre de usuario
    """
    
    default_error_messages = {
        "no_active_account": "Correo o contraseña incorrectos.",
    }
    
    def validate(self, attrs):
        login = attrs.get("username", "")
        if "@" in login:
            user_obj = User.objects.filter(email__iexact=login).first()
            if user_obj is not None:
                attrs["username"] = user_obj.get_username()
    
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed(
                "Correo o contraseña incorrectos.", "no_active_account"
            )
    
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
        }
        return data