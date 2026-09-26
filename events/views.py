from datetime import date

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Event, Subtask
from .serializers import EventSerializer, SubtaskSerializer, HoySubtaskSerializer


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


## Implementacion de US-3
## aqui ya tenemos creados los eventos, las subtasks, por lo que
## solo necesitamos que el back soporte otro tipo de peticiones
class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/PUT/DELETE /api/events/<pk>/"""
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(organizador=self.request.user)


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
        queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs['pk'])

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
    GET /api/hoy/?evento=<id>&estado=<pendiente|hecha|pospuesta|todas>

    Devuelve, para el organizador autenticado, sus gestiones logisticas
    agrupadas en "vencidas", "hoy" y "proximas".
    """

    permission_classes = [IsAuthenticated]

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