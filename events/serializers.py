from rest_framework import serializers
from .models import Event,Subtask


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "nombre", "tipo", "fecha_hora", "cliente_contacto", "lugar", "creado_en"]
        read_only_fields = ["id", "creado_en"]
      
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


##Serializador de las subtask
class SubtaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtask
        fields = ["id", "evento", "titulo", "fecha_objetivo", "horas_estimadas", "creado_en"]
        read_only_fields = ["id", "evento", "creado_en"]

    def validate_titulo(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("El título de la gestión es obligatorio.")
        return value

    def validate_horas_estimadas(self, value):
        if value <= 0:
            raise serializers.ValidationError("Las horas estimadas deben ser mayores a cero.")
        return value