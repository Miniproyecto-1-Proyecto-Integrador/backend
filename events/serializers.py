from rest_framework import serializers
from .models import Event,Subtask
from django.utils import timezone



class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "nombre", "tipo", "fecha_hora", "cliente_contacto", "lugar", "creado_en"]
        read_only_fields = ["id", "creado_en"]

    ## fix: validacion de fecha de asignacion de evento.
    ## para evitar que se asignen eventos del pasado.    
    def validate_fecha_hora(self, value):
        es_nuevo = self.instance is None
        cambio = not es_nuevo and value != self.instance.fecha_hora
        if (es_nuevo or cambio) and value <= timezone.now():
            raise serializers.ValidationError(
                "La fecha y hora del evento ya pasó. Elige una fecha y hora futura."
            )
        return value
    
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
## rework: se modifica subtaskserializer para que se tenga en cuenta
## la hora de creacion, ademas de validar formatos no validos.

class SubtaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtask
        fields = ["id", "evento", "titulo", "fecha_objetivo", "horas_estimadas", "creado_en"]
        read_only_fields = ["id", "evento", "creado_en"]
        extra_kwargs = {
            "titulo": {"error_messages": {
                "blank": "El título de la gestión es obligatorio.",
                "required": "El título de la gestión es obligatorio.",
                "null": "El título de la gestión es obligatorio.",
            }},
            "fecha_objetivo": {"error_messages": {
                "null": "La fecha objetivo es obligatoria.",
                "required": "La fecha objetivo es obligatoria.",
                "invalid": "La fecha objetivo no es válida.",
            }},
            "horas_estimadas": {"error_messages": {
                "null": "Las horas estimadas son obligatorias.",
                "required": "Las horas estimadas son obligatorias.",
                "invalid": "Las horas estimadas deben ser un número válido.",
            }},
        }

    def to_internal_value(self, data):
        data = data.copy()
        for campo in ("fecha_objetivo", "horas_estimadas"):
            if isinstance(data.get(campo), str) and not data[campo].strip():
                data[campo] = None
        return super().to_internal_value(data)

    def validate_horas_estimadas(self, value):
        if value <= 0:
            raise serializers.ValidationError("Las horas estimadas deben ser mayores a cero.")
        return value

    # Corrección 3
    def validate(self, attrs):
        evento = self.context.get("evento") or getattr(self.instance, "evento", None)
        fecha = attrs.get("fecha_objetivo") or getattr(self.instance, "fecha_objetivo", None)
        if evento and fecha:
            limite = timezone.localtime(evento.fecha_hora).date()
            if fecha > limite:
                raise serializers.ValidationError({
                    "fecha_objetivo": f"La fecha objetivo no puede ser posterior a la fecha del evento ({limite:%d/%m/%Y})."
                })
        return attrs