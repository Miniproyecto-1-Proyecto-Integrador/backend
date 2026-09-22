from django.http import JsonResponse
from rest_framework import generics
from rest_framework.exceptions import NotFound
from .models import Event,Subtask
from .serializers import EventSerializer
from .serializers import SubtaskSerializer
from django.shortcuts import get_object_or_404

##view generica de health check para el back.
def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend funcionando correctamente'
    })

##Implementacion de view de eventos US-1
class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


##Implementacion de view de subtasks US 2
class SubtaskListCreateView(generics.ListCreateAPIView):
    serializer_class = SubtaskSerializer

    def get_event(self):
        try:
            return Event.objects.get(pk=self.kwargs["event_id"])
        except Event.DoesNotExist:
            raise NotFound("El evento no existe.")

    def get_queryset(self):
        return Subtask.objects.filter(evento=self.get_event())

    def perform_create(self, serializer):
        serializer.save(evento=self.get_event())


##Implementacion de US-3
##aqui ya tenemos creados los eventos, las subtasks, por lo que 
##solo necesitamos que el back soporte otro tipo de peticiones
class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/PUT/DELETE /api/events/<pk>/"""
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class SubtaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/PUT/DELETE /api/events/<event_id>/subtasks/<pk>/"""
    serializer_class = SubtaskSerializer

    def get_queryset(self):
        # asegura que la subtarea pertenezca al evento de la URL
        return Subtask.objects.filter(evento_id=self.kwargs['event_id'])

    def get_object(self):
        queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs['pk'])