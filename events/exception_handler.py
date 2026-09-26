from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Uniforma las respuestas de error para que el front siempre reciba
    JSON con la forma {"detail": "..."} o {"<campo>": ["..."]}, incluso
    ante errores no manejados explícitamente.
    """
    response = exception_handler(exc, context)
    if response is not None:
        return response

    # Cualquier excepcion no controlada por DRF
    # cae aqui. se responde 500 en JSON en vez de dejar pasar la pagina
    # de error por defecto de django.
    return Response(
        {"detail": "Ocurrió un error inesperado en el servidor."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )