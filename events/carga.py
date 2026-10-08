from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import APIException

from .models import LIMITE_DIARIO_DEFECTO, LimiteDiario, Subtask


def limite_de(usuario):
    """Límite diario de horas del organizador (o el valor por defecto)."""
    fila = LimiteDiario.objects.filter(organizador=usuario).first()
    return fila.horas if fila else Decimal(LIMITE_DIARIO_DEFECTO)


def horas_del_dia(usuario, fecha, excluir_id=None):
    """
    Suma las horas estimadas de las gestiones PENDIENTES del organizador
    que caen en esa fecha, en todos sus eventos. Las hechas no cuentan.
    excluir_id evita contar dos veces la gestión que se está editando.
    """
    gestiones = Subtask.objects.filter(
        evento__organizador=usuario,
        fecha_objetivo=fecha,
        estado=Subtask.PENDIENTE,
    )
    if excluir_id is not None:
        gestiones = gestiones.exclude(pk=excluir_id)
    total = gestiones.aggregate(total=Sum("horas_estimadas"))["total"]
    return total or Decimal("0")


class ConflictoHoras(APIException):
    """409: el día se pasaría del límite diario del organizador."""

    status_code = 409
    default_detail = "La gestión supera el límite diario de horas."
    default_code = "conflicto_horas"


def _num(valor):
    """7.00 -> '7' y 7.50 -> '7.5' (para el mensaje en texto)."""
    return format(Decimal(valor).normalize(), "f")


def _dos(valor):
    """Siempre con dos decimales, como el resto de la API ('7.00')."""
    return f"{Decimal(valor):.2f}"


def verificar_conflicto(usuario, fecha, horas, excluir_id=None):
    """
    Lanza ConflictoHoras si agregar `horas` a `fecha` pasa el límite del
    organizador. Si cabe (incluso justo en el límite), no hace nada.
    """
    ya_planificadas = horas_del_dia(usuario, fecha, excluir_id)
    limite = limite_de(usuario)
    total = ya_planificadas + Decimal(horas)
    if total <= limite:
        return

    raise ConflictoHoras({
        "detail": (
            f"Con esta gestión, el {fecha:%d/%m/%Y} quedarían {_num(total)} h "
            f"planificadas ({_num(ya_planificadas)} h + {_num(horas)} h) y tu "
            f"límite diario es de {_num(limite)} h."
        ),
        "conflicto": {
            "fecha": fecha.isoformat(),
            "horas_ya_planificadas": _dos(ya_planificadas),
            "horas_gestion": _dos(horas),
            "horas_total": _dos(total),
            "limite_diario": _dos(limite),
            "horas_disponibles": _dos(max(limite - ya_planificadas, Decimal("0"))),
            "exceso": _dos(total - limite),
        },
    })

def dias_que_se_pasarian(usuario, limite):
    """
    Días (con gestiones PENDIENTES del organizador) cuyo total de horas
    supera `limite`. Devuelve [(fecha, total), ...] ordenado por fecha.
    """
    filas = (
        Subtask.objects.filter(
            evento__organizador=usuario,
            estado=Subtask.PENDIENTE,
        )
        .values("fecha_objetivo")
        .annotate(total=Sum("horas_estimadas"))
        .filter(total__gt=limite)
        .order_by("fecha_objetivo")
    )
    return [(f["fecha_objetivo"], f["total"]) for f in filas]