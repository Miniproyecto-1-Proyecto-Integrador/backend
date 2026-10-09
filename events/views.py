
from datetime import date, timedelta
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
)
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .carga import dias_que_se_pasarian, horas_del_dia, limite_de
from .models import Event, LimiteDiario, Subtask
from .serializers import (
    EventSerializer,
    HoySubtaskSerializer,
    LimiteDiarioSerializer,
    SubtaskSerializer,
)


EJEMPLO_CONFLICTO = OpenApiExample(
    "Conflicto de horas (5 h + 2 h = 7 h, límite 6 h)",
    value={
        "detail": (
            "Con esta gestión, el 08/10/2026 quedarían 7 h planificadas "
            "(5 h + 2 h) y tu límite diario es de 6 h."
        ),
        "conflicto": {
            "fecha": "2026-10-08",
            "horas_ya_planificadas": "5.00",
            "horas_gestion": "2.00",
            "horas_total": "7.00",
            "limite_diario": "6.00",
            "horas_disponibles": "1.00",
            "exceso": "1.00",
        },
    },
    response_only=True,
    status_codes=["409"],
)

DESCRIPCION_CONFLICTO = (
    "**Conflicto (409):** suma las horas de las gestiones *pendientes* del "
    "organizador en esa fecha (todos sus eventos; las hechas no cuentan) y "
    "usa el límite diario del organizador. Cabe si el total es menor o igual "
    "al límite. Si se pasa, no se guarda nada y se responde con las cifras: "
    "`horas_ya_planificadas`, `horas_gestion`, `horas_total`, `limite_diario`, "
    "`horas_disponibles` y `exceso`."
)

## view generica de health check para el back. Se deja publica (no
## requiere login) para que el front y las herramientas de despliegue
## puedan usarla como ping.
def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend funcionando correctamente'
    })


## Implementacion de view de eventos US-1
## Requiere autenticacion y filtra/asigna por organizador.
class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(organizador=self.request.user)

    def perform_create(self, serializer):
        serializer.save(organizador=self.request.user)

@extend_schema_view(
    post=extend_schema(
        summary="Crear una gestión logística (con validación de horas por día)",
        description=(
            "Crea una gestión del evento. Antes de guardarla se calcula la "
            "carga del día (US-07).\n\n" + DESCRIPCION_CONFLICTO
        ),
        request=SubtaskSerializer,
        responses={
            201: SubtaskSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Nueva gestión",
                value={
                    "titulo": "Confirmar catering",
                    "fecha_objetivo": "2026-10-08",
                    "horas_estimadas": "2",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Evento inexistente o de otro organizador",
                value={"detail": "El evento no existe."},
                response_only=True,
                status_codes=["404"],
            ),
            EJEMPLO_CONFLICTO,
        ],
    ),
)
    
## Implementacion de view de subtasks US 2
class SubtaskListCreateView(generics.ListCreateAPIView):
    serializer_class = SubtaskSerializer
    permission_classes = [IsAuthenticated]

    def get_event(self):
        evento = Event.objects.filter(
            pk=self.kwargs["event_id"], organizador=self.request.user
        ).first()
        if evento is None:
            # 404 y no 403: no revelamos si el evento existe pero es de
            # otro organizador o si simplemente no existe.
            raise NotFound("El evento no existe.")
        return evento

    def get_queryset(self):
        return Subtask.objects.filter(evento=self.get_event())

    def perform_create(self, serializer):
        serializer.save(evento=self.get_event())

    ## fix de times de eventos
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["evento"] = self.get_event()
        return ctx

class ProximaFechaDisponibleView(APIView):
    """
    GET /api/events/<event_id>/subtasks/proxima-fecha/
    Busca la primera fecha posterior a la indicada donde quepan
    las horas completas de una gestión.
    Permite excluir una subtarea cuando se está editando.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        evento = Event.objects.filter(
            pk=event_id,
            organizador=request.user,
        ).first()

        if evento is None:
            raise NotFound("El evento no existe.")

        fecha_param = request.query_params.get("fecha")
        horas_param = request.query_params.get("horas")
        excluir_id_param = request.query_params.get("excluir_id")

        if not fecha_param or not horas_param:
            raise ValidationError({
                "detail": "Debes indicar la fecha y las horas estimadas."
            })

        try:
            fecha_inicio = date.fromisoformat(fecha_param)
        except ValueError:
            raise ValidationError({
                "fecha": "La fecha debe tener el formato AAAA-MM-DD."
            })

        try:
            horas = Decimal(horas_param)
            if not horas.is_finite() or horas <= 0:
                raise ValueError
        except (ValueError, TypeError, ArithmeticError):
            raise ValidationError({
                "horas": "Las horas deben ser un número mayor que cero."
            })

        excluir_id = None

        if excluir_id_param:
            try:
                excluir_id = int(excluir_id_param)
                if excluir_id <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                raise ValidationError({
                    "excluir_id": "El ID de la subtarea no es válido."
                })

            subtarea = Subtask.objects.filter(
                pk=excluir_id,
                evento=evento,
            ).first()

            if subtarea is None:
                raise ValidationError({
                    "excluir_id": "La subtarea no pertenece a este evento."
                })

        hoy = timezone.localdate()
        fecha_maxima = timezone.localtime(evento.fecha_hora).date()
        fecha_inicio = max(fecha_inicio, hoy)

        limite = limite_de(request.user)
        fecha_candidata = fecha_inicio + timedelta(days=1)

        while fecha_candidata <= fecha_maxima:
            ocupadas = horas_del_dia(
                request.user,
                fecha_candidata,
                excluir_id=excluir_id,
            )

            if ocupadas + horas <= limite:
                return Response({
                    "disponible": True,
                    "fecha": fecha_candidata.isoformat(),
                    "horas_estimadas": str(horas),
                    "horas_ya_planificadas": str(ocupadas),
                    "limite_diario": str(limite),
                })

            fecha_candidata += timedelta(days=1)

        return Response({
            "disponible": False,
            "mensaje": (
                "No hay una fecha disponible antes o el día del evento "
                "para la duración completa de esta gestión."
            ),
        })

## Implementacion de US-3
## aqui ya tenemos creados los eventos, las subtasks, por lo que
## solo necesitamos que el back soporte otro tipo de peticiones
class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/PUT/DELETE /api/events/<pk>/"""
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(organizador=self.request.user)

@extend_schema_view(
    patch=extend_schema(
        summary="Editar una gestión: fecha objetivo, horas o estado (US-06 / US-08)",
        description=(
            "Edición parcial: se envía solo lo que cambia. Sirve para cambiar "
            "la fecha objetivo (US-06), marcar como hecha/pendiente y resolver "
            "un conflicto de horas moviendo la gestión a otra fecha o "
            "reduciendo sus horas (US-08); el backend recalcula las horas del "
            "día en cada intento. El cambio queda guardado y `/api/hoy/` la "
            "devuelve en el grupo que corresponde a la nueva fecha.\n\n"
            "| Status | Cuándo |\n"
            "|---|---|\n"
            "| 400 | Fecha anterior a hoy, posterior al evento, vacía o inválida; "
            "horas ≤ 0, no numéricas o mayores a 999.99; estado distinto de "
            "pendiente/hecha |\n"
            "| 401 | Sin token |\n"
            "| 404 | La gestión no existe o es de otro organizador |\n"
            "| 409 | El cambio pasa el límite diario |\n\n"
            + DESCRIPCION_CONFLICTO
        ),
        request=SubtaskSerializer,
        responses={
            200: SubtaskSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            409: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample("Mover a otra fecha", value={"fecha_objetivo": "2026-10-09"}, request_only=True),
            OpenApiExample("Reducir las horas estimadas", value={"horas_estimadas": "1"}, request_only=True),
            OpenApiExample(
                "Mover y reducir a la vez",
                value={"fecha_objetivo": "2026-10-09", "horas_estimadas": "1"},
                request_only=True,
            ),
            OpenApiExample(
                "Gestión actualizada",
                value={
                    "id": 1, "evento": 1, "titulo": "Confirmar catering",
                    "fecha_objetivo": "2026-10-09", "horas_estimadas": "2.00",
                    "estado": "pendiente", "creado_en": "2026-10-05T16:41:02-05:00",
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Fecha anterior a hoy",
                value={"fecha_objetivo": ["La fecha objetivo no puede ser anterior a hoy."]},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Fecha posterior al evento",
                value={"fecha_objetivo": ["La fecha objetivo no puede ser posterior a la fecha del evento (04/11/2026)."]},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Horas no válidas",
                value={"horas_estimadas": ["Las horas estimadas deben ser mayores a cero."]},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Gestión inexistente o de otro organizador",
                value={"detail": "La gestión no existe."},
                response_only=True,
                status_codes=["404"],
            ),
            EJEMPLO_CONFLICTO,
        ],
    ),
)

class SubtaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/PUT/DELETE /api/events/<event_id>/subtasks/<pk>/"""
    serializer_class = SubtaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # asegura que la subtarea pertenezca a un evento del organizador autenticado.
        return Subtask.objects.filter(
            evento_id=self.kwargs['event_id'],
            evento__organizador=self.request.user,
        )

    def get_object(self):
        gestion = self.get_queryset().filter(pk=self.kwargs['pk']).first()
        if gestion is None:
            raise NotFound("La gestión no existe.")
        return gestion

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        evento = Event.objects.filter(
            pk=self.kwargs['event_id'], organizador=self.request.user
        ).first()
        if evento is not None:
            ctx["evento"] = evento
        return ctx


REGLA_PRIORIDAD = (
    "Se ordenan primero las gestiones vencidas, luego las de hoy y por "
    "último las próximas. Dentro de cada grupo, la gestión con la fecha "
    "objetivo más próxima aparece primero; si dos gestiones caen el "
    "mismo día, se prioriza la que requiere menos horas estimadas."
)

ESTADOS_VALIDOS = {Subtask.PENDIENTE, Subtask.HECHA, "todas"}


class HoyView(APIView):
    """
    GET /api/hoy/?evento=<id>&estado=<pendiente|hecha|todas>

    Devuelve, para el organizador autenticado, sus gestiones logisticas
    agrupadas en "vencidas", "hoy" y "proximas".
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Gestiones agrupadas: Vencidas / Hoy / Próximas",
        description=(
            "Devuelve, para el organizador autenticado, sus gestiones "
            "ordenadas por fecha objetivo (desempate por menor esfuerzo "
            "estimado) y agrupadas en vencidas / hoy / proximas."
        ),
        parameters=[
            OpenApiParameter(
                name="evento",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Id de un evento propio. Si se omite, incluye todos los eventos del organizador.",
            ),
            OpenApiParameter(
                name="estado",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[Subtask.PENDIENTE, Subtask.HECHA, "todas"],
                description="Filtra por estado de la gestión. Default: pendiente.",
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Éxito con gestiones",
                value={
                    "hoy": "2026-09-26",
                    "regla_prioridad": REGLA_PRIORIDAD,
                    "filtros_aplicados": {"evento": None, "estado": "pendiente"},
                    "grupos": {
                        "vencidas": [{
                            "id": 12, "titulo": "Confirmar catering",
                            "fecha_objetivo": "2026-09-20", "horas_estimadas": "2.00",
                            "estado": "pendiente",
                            "evento_id": 5, "evento_nombre": "Boda Andrea y Luis",
                            "grupo": "vencida",
                        }],
                        "hoy": [],
                        "proximas": [{
                            "id": 15, "titulo": "Enviar invitaciones",
                            "fecha_objetivo": "2026-10-01", "horas_estimadas": "1.50",
                            "estado": "pendiente",
                            "evento_id": 5, "evento_nombre": "Boda Andrea y Luis",
                            "grupo": "proxima",
                        }],
                    },
                    "total": 2,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Sin gestiones (estado vacío)",
                value={
                    "hoy": "2026-09-26",
                    "regla_prioridad": REGLA_PRIORIDAD,
                    "filtros_aplicados": {"evento": None, "estado": "pendiente"},
                    "grupos": {"vencidas": [], "hoy": [], "proximas": []},
                    "total": 0,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Estado inválido",
                value={"estado": ["Valor inválido. Usa uno de: hecha, pendiente, todas."]},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Evento no numérico",
                value={"evento": ["Debe ser el id numérico de un evento."]},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Evento inexistente o ajeno",
                value={"detail": "El evento no existe."},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def get(self, request):
        estado_param = request.query_params.get("estado", Subtask.PENDIENTE)
        if estado_param not in ESTADOS_VALIDOS:
            raise ValidationError({
                "estado": [
                    f"Valor inválido. Usa uno de: "
                    f"{', '.join(sorted(ESTADOS_VALIDOS))}."
                ]
            })

        evento_param = request.query_params.get("evento")
        evento_obj = None
        if evento_param is not None:
            try:
                evento_id = int(evento_param)
            except (TypeError, ValueError):
                raise ValidationError({"evento": ["Debe ser el id numérico de un evento."]})
            evento_obj = Event.objects.filter(
                pk=evento_id, organizador=request.user
            ).first()
            if evento_obj is None:
                raise NotFound("El evento no existe.")

        queryset = Subtask.objects.filter(evento__organizador=request.user)
        if evento_obj is not None:
            queryset = queryset.filter(evento=evento_obj)
        if estado_param != "todas":
            queryset = queryset.filter(estado=estado_param)

        # Orden global: fecha objetivo asc, desempate por menor esfuerzo.
        queryset = queryset.select_related("evento").order_by(
            "fecha_objetivo", "horas_estimadas"
        )

        hoy = timezone.localdate()
        vencidas, para_hoy, proximas = [], [], []
        for gestion in queryset:
            if gestion.fecha_objetivo < hoy:
                gestion._grupo = "vencida"
                vencidas.append(gestion)
            elif gestion.fecha_objetivo == hoy:
                gestion._grupo = "hoy"
                para_hoy.append(gestion)
            else:
                gestion._grupo = "proxima"
                proximas.append(gestion)

        data = {
            "hoy": hoy.isoformat(),
            "regla_prioridad": REGLA_PRIORIDAD,
            "filtros_aplicados": {
                "evento": evento_obj.id if evento_obj else None,
                "estado": estado_param,
            },
            "grupos": {
                "vencidas": HoySubtaskSerializer(vencidas, many=True).data,
                "hoy": HoySubtaskSerializer(para_hoy, many=True).data,
                "proximas": HoySubtaskSerializer(proximas, many=True).data,
            },
            "total": len(vencidas) + len(para_hoy) + len(proximas),
        }
        return Response(data, status=status.HTTP_200_OK)


## US-12: limite diario de horas por organizador
class LimiteDiarioView(APIView):
    """GET/PUT /api/limite-diario/"""

    permission_classes = [IsAuthenticated]


    @extend_schema(
        summary="Consultar el límite diario de horas (US-12)",
        description=(
            "Devuelve el límite de horas por día del organizador autenticado. "
            "Si nunca lo configuró, responde el valor por defecto (6 h). "
            "Cada organizador tiene el suyo."
        ),
        responses={200: LimiteDiarioSerializer, 401: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample(
                "Límite actual",
                value={"horas": "6.00"},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )

    def get(self, request):
        # Si el organizador nunca lo configuro, se responde el valor por
        # defecto sin crear nada en la base de datos.
        data = LimiteDiarioSerializer({"horas": limite_de(request.user)}).data
        return Response(data, status=status.HTTP_200_OK)


    @extend_schema(
        summary="Configurar el límite diario de horas (US-12)",
        description=(
            "Guarda el límite del organizador autenticado. Rango válido: "
            "1 a 16 horas, con máximo 2 decimales."
        ),
        request=LimiteDiarioSerializer,
        responses={200: LimiteDiarioSerializer, 400: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample("Límite de 8 horas", value={"horas": 8}, request_only=True),
            OpenApiExample(
                "Límite guardado",
                value={"horas": "8.00"},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Fuera de rango",
                value={"horas": ["El límite diario debe estar entre 1 y 16 horas."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    
    def put(self, request):
        serializer = LimiteDiarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nuevas_horas = serializer.validated_data["horas"]

        # No se puede bajar el límite si ya hay días con gestiones
        # pendientes que quedarían por encima del nuevo valor.
        excedidos = dias_que_se_pasarian(request.user, nuevas_horas)
        if excedidos:
            ejemplos = ", ".join(
                f"{fecha:%d/%m/%Y} ({total.normalize():f} h)"
                for fecha, total in excedidos[:3]
            )
            resto = len(excedidos) - 3
            if resto > 0:
                ejemplos += f" y {resto} más"
            raise ValidationError({
                "horas": [
                    f"No puedes bajar el límite a {nuevas_horas.normalize():f} h "
                    f"porque ya tienes días que lo superarían: {ejemplos}. "
                    "Reprograma o completa esas gestiones primero."
                ]
            })

        LimiteDiario.objects.update_or_create(
            organizador=request.user,
            defaults={"horas": nuevas_horas},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)