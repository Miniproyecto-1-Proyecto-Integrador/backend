from rest_framework import serializers
from .models import Event


class EventSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(
        max_length=200,
        error_messages={
            "blank": "El nombre del evento es obligatorio.",
            "required": "El nombre del evento es obligatorio.",
        },
    )
    tipo = serializers.CharField(
        max_length=100,
        error_messages={
            "blank": "El tipo de evento es obligatorio.",
            "required": "El tipo de evento es obligatorio.",
        },
    )
    fecha_hora = serializers.DateTimeField(
        error_messages={
            "required": "La fecha y hora del evento son obligatorias.",
            "invalid": "La fecha y hora ingresadas no son válidas.",
        },
    )
    cliente_contacto = serializers.CharField(
        max_length=200,
        error_messages={
            "blank": "El cliente o contacto es obligatorio.",
            "required": "El cliente o contacto es obligatorio.",
        },
    )
    lugar = serializers.CharField(
        max_length=200,
        error_messages={
            "blank": "El lugar es obligatorio.",
            "required": "El lugar es obligatorio.",
        },
    )

    class Meta:
        model = Event
        fields = ["id", "nombre", "tipo", "fecha_hora", "cliente_contacto", "lugar", "creado_en"]
        read_only_fields = ["id", "creado_en"]