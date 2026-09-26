from django.urls import path
from .views import health_check
from .views import EventListCreateView
from .views import SubtaskListCreateView
from .views import HoyView
from events import views  ##importamos views para evitar problemas
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

urlpatterns = [
    path('health/', health_check),
    path('events/', EventListCreateView.as_view(), name="event-list-create"),
    path("events/<int:event_id>/subtasks/", SubtaskListCreateView.as_view(), name="subtask-list-create"),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event-detail'),
    path('events/<int:event_id>/subtasks/<int:pk>/', views.SubtaskDetailView.as_view(), name='subtask-detail'),
    path('hoy/', HoyView.as_view(), name='hoy'),
    path('schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny]), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny]), name='swagger-ui'),
]