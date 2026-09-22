from django.db import models
from django.core.validators import MinValueValidator

class Event(models.Model):
    #creamos modelos, incialmente se deja de manera abierta, pudiendo
    #registrar cualquier tipo de evento
    
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100)
    fecha_hora = models.DateTimeField()
    cliente_contacto = models.CharField(max_length=200, blank=True, default="")
    lugar = models.CharField(max_length=200, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"

##Implementacion de historia 2, la subtask
class Subtask(models.Model):
    evento = models.ForeignKey(
        Event,
        related_name="subtasks",
        on_delete=models.CASCADE,
    )
    titulo = models.CharField(max_length=255)
    fecha_objetivo = models.DateField()
    horas_estimadas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_objetivo"]

    def __str__(self):
        return f"{self.titulo} ({self.evento.nombre})"