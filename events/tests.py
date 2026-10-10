from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Event, Subtask


User = get_user_model()



class ProgresoEventoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(
            username="organizador1",
            password="PruebaSegura123!",
        )
        self.otro_usuario = User.objects.create_user(
            username="organizador2",
            password="PruebaSegura123!",
        )

        self.evento = Event.objects.create(
            organizador=self.usuario,
            nombre="Evento de prueba",
            tipo="Conferencia",
            fecha_hora=timezone.now() + timedelta(days=10),
        )

        self.url = f"/api/events/{self.evento.id}/progreso/"

    def crear_subtarea(self, titulo, estado):
        return Subtask.objects.create(
            evento=self.evento,
            titulo=titulo,
            fecha_objetivo=date.today(),
            horas_estimadas=Decimal("1.00"),
            estado=estado,
        )

    def test_calcula_porcentaje_de_progreso(self):
        self.client.force_authenticate(user=self.usuario)

        self.crear_subtarea("Tarea hecha 1", Subtask.HECHA)
        self.crear_subtarea("Tarea hecha 2", Subtask.HECHA)
        self.crear_subtarea("Tarea pendiente", Subtask.PENDIENTE)
        self.crear_subtarea("Tarea pospuesta", Subtask.POSPUESTA)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["evento_id"], self.evento.id)
        self.assertEqual(respuesta.data["total_subtareas"], 4)
        self.assertEqual(respuesta.data["subtareas_hechas"], 2)
        self.assertEqual(respuesta.data["porcentaje"], 50)

    def test_evento_sin_subtareas_tiene_cero_porcentaje(self):
        self.client.force_authenticate(user=self.usuario)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["total_subtareas"], 0)
        self.assertEqual(respuesta.data["subtareas_hechas"], 0)
        self.assertEqual(respuesta.data["porcentaje"], 0)

    def test_requiere_autenticacion(self):
        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 401)

    def test_no_permite_consultar_evento_de_otro_usuario(self):
        self.client.force_authenticate(user=self.otro_usuario)

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 404)


class ActualizacionSubtaskTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(
            username="organizador_us09",
            password="PruebaSegura123!",
        )

        self.evento = Event.objects.create(
            organizador=self.usuario,
            nombre="Evento US-09",
            tipo="Conferencia",
            fecha_hora=timezone.now() + timedelta(days=10),
        )

        self.subtarea = Subtask.objects.create(
            evento=self.evento,
            titulo="Confirmar proveedor",
            fecha_objetivo=date.today(),
            horas_estimadas=Decimal("1.00"),
            estado=Subtask.PENDIENTE,
        )

        self.url = (
            f"/api/events/{self.evento.id}/subtasks/{self.subtarea.id}/"
        )
        self.client.force_authenticate(user=self.usuario)

    def test_marcar_como_hecha(self):
        respuesta = self.client.patch(
            self.url,
            {"estado": "hecha"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["estado"], "hecha")

        self.subtarea.refresh_from_db()
        self.assertEqual(self.subtarea.estado, Subtask.HECHA)

    def test_posponer_con_nota(self):
        respuesta = self.client.patch(
            self.url,
            {
                "estado": "pospuesta",
                "nota": "El proveedor pidió cambiar la fecha.",
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["estado"], "pospuesta")
        self.assertEqual(
            respuesta.data["nota"],
            "El proveedor pidió cambiar la fecha.",
        )

        self.subtarea.refresh_from_db()
        self.assertEqual(self.subtarea.estado, Subtask.POSPUESTA)
        self.assertEqual(
            self.subtarea.nota,
            "El proveedor pidió cambiar la fecha.",
        )

    def test_rechaza_estado_invalido(self):
        respuesta = self.client.patch(
            self.url,
            {"estado": "cancelada"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_permite_posponer_sin_nota(self):
        respuesta = self.client.patch(
            self.url,
            {"estado": "pospuesta"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["estado"], "pospuesta")
        self.assertEqual(respuesta.data["nota"], "")