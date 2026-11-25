# TecnoAndes | Asistencia y permisos

Aplicación Django para gestionar empleados, marcaciones, solicitudes, aprobaciones, reportes y auditoría del personal de TecnoAndes S.A.C.

## Instalación

1. `python -m venv .venv`
2. Activar el entorno: Windows `.venv\Scripts\Activate.ps1`; macOS/Linux `source .venv/bin/activate`.
3. `pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py createsuperuser`
6. `python manage.py seed_demo`
7. `python manage.py runserver` y abrir <http://127.0.0.1:8000/>.

`seed_demo` crea las áreas y grupos de roles, 10 empleados, 50 asistencias y 10 solicitudes. Cuentas demostrativas (no usar en producción):

- Empleado: `empleado01` / `Demo2026!`
- Jefe de Sistemas: `jefe.sistemas` / `TecnoAndes2026!`
- Las operaciones de RRHH están disponibles para el superusuario creado en el paso 5. También se puede asignar el grupo `RRHH` a una cuenta desde **Administración → Usuarios**.

## Requisitos funcionales implementados

### RF1 — Empleados y áreas

- Registro desde **Registrar empleado**, disponible solo para RRHH; se crea una cuenta de acceso y su perfil de empleado.
- Campos: usuario, email corporativo, DNI, nombres, apellidos, cargo, área, fecha de ingreso y contrato (planilla/locación).
- El formulario valida DNI de ocho dígitos y único, email `@tecnoandes.pe` único, cargo obligatorio y fecha de ingreso no futura.
- Áreas permitidas: Sistemas, Contabilidad, Ventas, Logística y RRHH.
- Antigüedad calculada en años y meses. La ficha de RRHH también muestra el email y saldo de vacaciones.

### RF2 — Asistencia

- Entrada y salida registran el timestamp del servidor en la zona horaria `America/Lima`.
- El middleware de horario solo acepta marcas en días laborables: entrada 06:00–10:00 y salida 15:00–19:00. No permite registrar otra entrada mientras exista una del día sin salida.
- La salida debe ser posterior a la entrada. Se calculan las horas trabajadas y las horas extra después de ocho horas.
- Las marcaciones no se pueden editar desde la cuenta de empleado. Las correcciones son exclusivas de RRHH y exigen motivo (error de sistema, olvido u otro) y justificación de al menos 50 caracteres.

### RF3 — Permisos y vacaciones

- Solicitudes de permiso personal, médico, duelo, maternidad/paternidad, vacaciones u otro; fechas, motivo de al menos 30 caracteres y descripción textual del documento adjunto.
- Se valida que la fecha final no sea anterior a la inicial, que no existan permisos aprobados o pendientes superpuestos y que las vacaciones solicitadas no superen el saldo disponible.
- El saldo se calcula como 30 días menos las vacaciones aprobadas.
- RRHH puede resolver cualquier solicitud; un jefe solo puede resolver solicitudes de su propia área. La decisión queda registrada y se muestra al empleado en la lista y como aviso en su inicio.

### RF4 — Acceso por rol

| Rol | Acceso |
|---|---|
| RRHH / superusuario | Gestión de empleados y usuarios, asistencia, permisos, reportes globales, correcciones y auditoría |
| Jefe de área | Solicitudes y reportes limitados a su área |
| Empleado | Su asistencia, saldo y solicitudes |
| Contador | Reportes globales de asistencia en modo lectura |

- Los roles se asignan desde **Administración → Usuarios**. El portal requiere autenticación y las vistas comprueban permisos en el servidor.
- Jefes y contadores ven identificadores de colaborador, no DNI ni nombres; los datos personales y salariales quedan restringidos a RRHH.
- La sesión expira tras 45 minutos de inactividad efectiva.

### RF5 — Middleware y auditoría

- Al iniciar una sesión, se muestra un recordatorio de entrada en días laborables cuando todavía no existe una marcación.
- Middleware dedicado valida horario y cuenta activa.
- Las operaciones sobre asistencias y permisos registran usuario, acción, registro y timestamp. Las acciones de RRHH en Django Admin también quedan auditadas.

### RF6 — Django Admin y reportes

- En `/admin/`, RRHH puede consultar empleados, asistencias por área/fecha, permisos y auditoría.
- La ficha de empleado incluye antigüedad, vacaciones disponibles y horas extra acumuladas.
- Los permisos se pueden filtrar por estado y aprobar en lote desde la acción **Aprobar permisos seleccionados**.
- El portal de reportes ofrece filtros por fecha y área, total de horas extra por empleado y una exportación textual simulada.

## Ejecución de pruebas

```powershell
python manage.py check
python manage.py test
```

## Manual breve de empleado

1. Inicia sesión con las credenciales entregadas por RRHH.
2. En **Asistencia**, marca entrada al iniciar la jornada y salida al terminar.
3. En **Permisos**, elige tipo y fechas, explica el motivo y agrega una descripción del documento si corresponde.
4. Consulta **Permisos** para revisar el estado. Las decisiones recientes también aparecen como aviso en el inicio.
5. Cierra sesión al terminar. Para solicitar una corrección, contacta a RRHH con la justificación correspondiente.

## Seguridad y despliegue

La configuración incluida es para desarrollo. Antes de producción se deben configurar `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` explícitos, HTTPS y cookies seguras, además de una base de datos y correo adecuados. La base SQLite y las contraseñas demostrativas no deben usarse en producción. `seed_demo` es únicamente para datos de prueba.
