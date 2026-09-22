from django.http import JsonResponse
from rest_framework import generics
from rest_framework.exceptions import NotFound
from .models import Event,Subtask
from .serializers import EventSerializer
from .serializers import SubtaskSerializer

##view generica de health check para el back.
def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend funcionando correctamente'
    })

##Implementacion de view de eventos
class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


##Implementacion de view de subtasks
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