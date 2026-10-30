# Organizador de Eventos — Backend

API REST del miniproyecto "Organizador de Eventos" (Proyecto Integrador I).
Permite planear, ejecutar y reprogramar la logística de eventos independientes.

- **API desplegada:** https://backend-wy15.onrender.com
- **Health check:** https://backend-wy15.onrender.com/api/health/
- **Documentación Swagger:** https://backend-wy15.onrender.com/api/docs/]
- **Frontend:** https://frontend-equipo-fisica.vercel.app

## Stack

- Python 3.13
- Django 6.1.1 + Django REST Framework 3.18.1
- Autenticación JWT (djangorestframework-simplejwt): access token 20 min, refresh 1 h
- Documentación OpenAPI: drf-spectacular
- Base de datos: PostgreSQL (Supabase)
- Servidor de producción: gunicorn
- Despliegue: Render

## Estructura

- `config/`: configuración del proyecto Django
- `events/`: eventos, subtareas, progreso y vista "Hoy"
- `users/`: usuarios y autenticación

## Instalación local

1. Clonar el repositorio:
   `git clone https://github.com/Miniproyecto-1-Proyecto-Integrador/backend.git`
2. Crear y activar el entorno virtual:
   - Windows: `python -m venv venv` y `venv\Scripts\activate`
   - Linux/Mac: `python3 -m venv venv` y `source venv/bin/activate`
3. Instalar dependencias:
   `pip install -r requirements.txt`
4. Crear un archivo `.env` en la raíz con las variables de la sección siguiente.
5. Aplicar migraciones:
   `python manage.py migrate`
6. Iniciar el servidor:
   `python manage.py runserver`

La API queda en http://127.0.0.1:8000/.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `True` en local, `False` en producción |
| `DB_NAME` | Nombre de la base de datos |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña de la base de datos |
| `DB_HOST` | Host de la base de datos (Supabase) |
| `DB_PORT` | Puerto de la base de datos |
| `RENDER_EXTERNAL_HOSTNAME` | Lo define Render automáticamente; agrega el dominio a `ALLOWED_HOSTS` |

Nunca subas el archivo `.env` al repositorio, Se recomienda manejarlo en un gitignore en caso de usar control de versiones.

> Nota: el entorno local y Render usan la misma base de datos de Supabase, para pruebas aisladas, desligar el front de render modificando el .env
> Los cambios hechos en local afectan los datos de producción.

## Pruebas

Las pruebas usan una base PostgreSQL aparte, activada con `DJANGO_TESTING=1`
(variables opcionales `TEST_DB_NAME`, `TEST_DB_USER`, `TEST_DB_PASSWORD`,
`TEST_DB_HOST`, `TEST_DB_PORT`; por defecto `127.0.0.1:5433`).

    DJANGO_TESTING=1 python manage.py test

## Despliegue en Render

El servicio está vinculado a la rama `main`: cada commit o PR fusionado en `main`
dispara un redespliegue automático.

- **Build Command:** [manuelajeje]
- **Start Command:** [manuelajeje]
- **Migraciones:** se ejecutan en cada despliegue. Si el modelo no cambió,
  la migración termina rápido sin modificar nada.
- **Variables de entorno:** se configuran en el dashboard de Render
  (Environment), no en el repositorio.

Nota: en el plan gratuito el servicio se duerme tras un periodo de inactividad;
la primera petición puede tardar en responder.

## Autenticación

Los endpoints requieren un token JWT en el encabezado:

    Authorization: Bearer <access_token>

## Endpoints principales

| Método HTTP | Endpoint | Descripción |
|---|---|---|
| GET, POST | `/api/events/` | Consultar los eventos del usuario y crear un evento. |
| GET, PATCH, PUT, DELETE | `/api/events/{id}/` | Consultar, actualizar o eliminar un evento. |
| GET, POST | `/api/events/{event_id}/subtasks/` | Listar o crear subtareas de un evento. |
| GET, PATCH, PUT, DELETE | `/api/events/{event_id}/subtasks/{pk}/` | Consultar, actualizar o eliminar una subtarea específica. |
| GET | `/api/events/{event_id}/progreso/` | Consultar el total de subtareas, las hechas y el porcentaje de progreso. |
| GET | `/api/events/{event_id}/subtasks/proxima-fecha/` | Consultar una próxima fecha disponible para una subtarea. |
| GET | `/api/hoy/` | Consultar las subtareas organizadas para la vista Hoy. |
| GET, PUT | `/api/limite-diario/` | Consultar o actualizar el límite diario de carga. |
| GET | `/api/health/` | Comprobar que el backend está funcionando. |
| GET | `/api/schema/` | Obtener el esquema OpenAPI. |
| GET | `/api/docs/` | Abrir la documentación interactiva Swagger. |

## Manejo de errores

La API usa un manejador de excepciones propio (`events/exception_handler.py`)
que devuelve respuestas de error con formato estándar y códigos HTTP
convencionales (400, 401, 403, 404).
