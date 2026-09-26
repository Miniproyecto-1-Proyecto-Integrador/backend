from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework_simplejwt.exceptions import InvalidToken


def custom_exception_handler(exc, context):
    """
    Uniforma las respuestas de error para que el front siempre reciba
    JSON con la forma {"detail": "..."} o {"<campo>": ["..."]}, incluso
    ante errores no manejados explícitamente.
    """
    response = exception_handler(exc, context)
    if response is not None:
        # Personaliza los mensajes de error de autenticacion para que sean
        # mas amigables y consistentes con el resto de la API.
        if isinstance(exc, InvalidToken):
            response.data = {"detail": "El token no es válido o ya expiró. Inicia sesión de nuevo."}
        elif isinstance(exc, NotAuthenticated):
            response.data = {"detail": "No se proporcionaron credenciales de autenticación."}
        return response
 
    # Cualquier excepcion no controlada por DRF
    # cae aqui. se responde 500 en JSON en vez de dejar pasar la pagina
    # de error por defecto de django.
    return Response(
        {"detail": "Ocurrió un error inesperado en el servidor."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )