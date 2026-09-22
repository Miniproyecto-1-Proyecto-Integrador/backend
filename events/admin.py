from django.contrib import admin
from .models import Event,Subtask

# Register your models here.

#registramos el primer modelo de Eventos. HS 1
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo", "fecha_hora", "creado_en")

@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "evento", "fecha_objetivo", "horas_estimadas", "creado_en")
    list_filter = ("evento",)
