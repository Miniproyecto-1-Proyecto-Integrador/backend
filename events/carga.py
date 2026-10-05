from decimal import Decimal

from .models import LIMITE_DIARIO_DEFECTO, LimiteDiario


def limite_de(usuario):
    """Límite diario de horas del organizador (o el valor por defecto)."""
    fila = LimiteDiario.objects.filter(organizador=usuario).first()
    return fila.horas if fila else Decimal(LIMITE_DIARIO_DEFECTO)