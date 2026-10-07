from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Event(models.Model):
    # Se deja abierto el tipo de evento, permitiendo registrar cualquier
    # tipo de evento

    # los eventos creados sin login quedan con organizador=None
    # y dejan de ser visibles para cualquier
    # usuario autenticado una vez se activa el aislamiento por organizador.

    organizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="eventos",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

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


class Subtask(models.Model):
    # estado de la gestion. este se añade ahora porque la vista hoy
    # necesita distinguir gestiones pendientes de las que
    # ya se marcaron como hechas o pospuestas (lo de pospuestas se completara
    # en otro sprint pero el campo se deja listo desde ya)

    PENDIENTE = "pendiente"
    HECHA = "hecha"
    ESTADO_CHOICES = [
        (PENDIENTE, "Pendiente"),
        (HECHA, "Hecha"),
    ]

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
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=PENDIENTE,
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_objetivo"]

    def __str__(self):
        return f"{self.titulo} ({self.evento.nombre})"


# Límite de horas de trabajo por día de cada organizador (US-12).
# Si el organizador nunca lo configuró, no hay fila y se usa el valor por defecto.
LIMITE_DIARIO_DEFECTO = 6


class LimiteDiario(models.Model):
    organizador = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="limite_diario",
        on_delete=models.CASCADE,
    )
    horas = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=LIMITE_DIARIO_DEFECTO,
        validators=[MinValueValidator(1), MaxValueValidator(16)],
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.organizador} - {self.horas} h/día"