from django.urls import path
from .views import health_check
from .views import EventListCreateView

urlpatterns = [
    path('health/', health_check),
    path('events/', EventListCreateView.as_view(), name="event-list-create")
]