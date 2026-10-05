from decimal import Decimal
from rest_framework import serializers
from .carga import verificar_conflicto
from .models import Event, Subtask
from django.utils import timezone


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id", "nombre", "tipo", "fecha_hora", "cliente_contacto",
            "lugar", "creado_en", "organizador",
        ]

        # organizador ya no se recibe del cliente: la vista lo asigna
        # automaticamente a partir de request.user
        read_only_fields = ["id", "creado_en", "organizador"]

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
        fields = [
            "id", "evento", "titulo", "fecha_objetivo", "horas_estimadas",
            "estado", "creado_en",
        ]
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

    estado = serializers.ChoiceField(
        choices=Subtask.ESTADO_CHOICES,
        required=False,
        error_messages={
            "invalid_choice": "El estado solo puede ser 'pendiente' o 'hecha'."
        },
    )

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

    # La gestion no puede programarse antes de hoy.
    def validate_fecha_objetivo(self, value):
        hoy = timezone.localdate()
        if value < hoy:
            raise serializers.ValidationError(
                "La fecha objetivo no puede ser anterior a hoy."
            )
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
        self._verificar_horas_del_dia(attrs)
        return attrs

    # US-07: el dia no puede pasarse del limite diario del organizador.
    def _verificar_horas_del_dia(self, attrs):
        request = self.context.get("request")
        if request is None:
            return
        actual = self.instance
        fecha = attrs.get("fecha_objetivo", getattr(actual, "fecha_objetivo", None))
        horas = attrs.get("horas_estimadas", getattr(actual, "horas_estimadas", None))
        estado = attrs.get("estado", getattr(actual, "estado", Subtask.PENDIENTE))

        # Una gestion hecha no cuenta para las horas del dia.
        if estado == Subtask.HECHA or fecha is None or horas is None:
            return
        # Si se edita sin tocar fecha, horas ni estado (ej. solo el titulo),
        # no hay nada nuevo que validar.
        if (
            actual is not None
            and fecha == actual.fecha_objetivo
            and horas == actual.horas_estimadas
            and estado == actual.estado
        ):
            return

        verificar_conflicto(
            request.user, fecha, horas,
            excluir_id=actual.pk if actual is not None else None,
        )
    


# Serializer de solo lectura usado por /hoy/. ademas de los campos de la
# gestión, expone el nombre del evento al que pertenece y el grupo al que
# fue asignada (vencida/hoy/proxima)
class HoySubtaskSerializer(serializers.ModelSerializer):
    evento_id = serializers.IntegerField(source="evento.id")
    evento_nombre = serializers.CharField(source="evento.nombre")
    grupo = serializers.SerializerMethodField()

    class Meta:
        model = Subtask
        fields = [
            "id", "titulo", "fecha_objetivo", "horas_estimadas",
            "estado", "evento_id", "evento_nombre", "grupo",
        ]

    def get_grupo(self, obj):
        # La vista anota cada objeto con `_grupo` antes de serializar.
        return getattr(obj, "_grupo", None)


# US-12: límite diario de horas del organizador.
MENSAJE_RANGO_LIMITE = "El límite diario debe estar entre 1 y 16 horas."


class LimiteDiarioSerializer(serializers.Serializer):
    horas = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=Decimal("1"),
        max_value=Decimal("16"),
        error_messages={
            "required": "El límite diario es obligatorio.",
            "null": "El límite diario es obligatorio.",
            "invalid": "El límite diario debe ser un número válido.",
            "min_value": MENSAJE_RANGO_LIMITE,
            "max_value": MENSAJE_RANGO_LIMITE,
            "max_digits": MENSAJE_RANGO_LIMITE,
            "max_whole_digits": MENSAJE_RANGO_LIMITE,
            "max_decimal_places": "El límite diario admite máximo 2 decimales.",
        },
    )