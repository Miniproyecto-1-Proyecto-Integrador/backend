from django.db import models

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