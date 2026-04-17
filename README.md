# TurnoSalud — Sistema de gestión de turnos médicos

Aplicación web para gestionar turnos médicos con tres roles: **administrador**, **médico** y **paciente**.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3 + Flask |
| Base de datos | MySQL (via PyMySQL) |
| Frontend | Tailwind CSS (CDN) + Alpine.js (CDN) + Inter (Google Fonts) |
| Templates | Jinja2 |

No requiere bundler ni pasos de build para el frontend.

---

## Requisitos previos

- Python 3.8 o superior
- MySQL Server corriendo en `localhost:3306`
- MySQL Workbench (opcional, para inspeccionar la base)

---

## Instalación

### 1. Clonar / abrir el proyecto en VS Code

```bash
cd "ruta/al/proyecto"
```

### 2. Crear entorno virtual

```bash
python -m venv venv
```

### 3. Activar el entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Mac / Linux:**
```bash
source venv/bin/activate
```

El prompt debería mostrar `(venv)` al inicio.

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## Configurar MySQL

### Crear la base de datos (una sola vez)

Abrí MySQL Workbench, conectate a `localhost` con tu usuario `root` y ejecutá:

```sql
CREATE DATABASE turnosalud CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Configurar credenciales en el proyecto

Abrí [app.py](app.py) y editá las líneas 12–15:

```python
DB_HOST     = 'localhost'
DB_USER     = 'root'
DB_PASSWORD = 'tu_password'   # ← tu contraseña de MySQL
DB_NAME     = 'turnosalud'
```

---

## Ejecutar la aplicación

```bash
python app.py
```

Al correr por primera vez, Flask crea automáticamente todas las tablas y carga datos de prueba.

Abrí el navegador en:

```
http://127.0.0.1:5000
```

---

## Cuentas de prueba

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | `admin@turnosalud.com` | `admin123` |
| Médico | `carlos@turnosalud.com` | `medico123` |
| Médico | `ana@turnosalud.com` | `medico123` |
| Médico | `luis@turnosalud.com` | `medico123` |
| Médico | `maria@turnosalud.com` | `medico123` |
| Paciente | `juan@email.com` | `paciente123` |

---

## Roles y funcionalidades

### Administrador (`admin@turnosalud.com`)
- Dashboard con estadísticas globales (médicos, pacientes, turnos, reservas)
- Crear cuentas de médicos (especialidad se elige de un catálogo fijo de 33 especialidades)
- Eliminar médicos (solo si no tienen reservas futuras activas)
- Ver listado de pacientes registrados

### Médico (panel de gestión de agenda)
- Dashboard personal con stats y próximas reservas
- Agregar turnos en modo **simple** (uno) o **bloque** (múltiples con preview en vivo)
- Editar fecha y horario de un turno
- Habilitar / deshabilitar turnos sin eliminarlos
- Eliminar turnos sin paciente asignado
- Ver todas las reservas de sus pacientes
- **Mi perfil**: definir precio de consulta, reglas de convivencia y descripción profesional (se muestran al paciente al reservar)

### Paciente
- Registro propio con email y contraseña
- Buscar turnos disponibles filtrando por especialidad, médico y fecha (el dropdown de médico se filtra al elegir especialidad)
- Solo ve turnos cuya fecha+hora todavía no pasó
- Modal de reserva con precio visible, reglas de convivencia del médico y aviso si el día tiene alta demanda (>=70% reservado)
- Ver historial de turnos propios (próximos e historial cancelado)
- Cancelar una reserva confirmada

---

## Estructura del proyecto

```
Proyecto 1/
├── app.py                        # Aplicación Flask (rutas, lógica, DB)
├── requirements.txt              # Dependencias Python
├── turnos.db                     # Solo si usás SQLite (no aplica con MySQL)
└── templates/
    ├── base.html                 # Layout base (navbar, flash messages, footer)
    ├── index.html                # Landing page con listado de especialistas
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── admin/
    │   ├── dashboard.html        # Stats globales + actividad reciente
    │   ├── medicos.html          # Listado y eliminación de médicos
    │   ├── crear_medico.html     # Formulario de alta de médico
    │   └── pacientes.html        # Listado de pacientes
    ├── medico/
    │   ├── dashboard.html        # Stats + próximas reservas + accesos rápidos
    │   ├── turnos.html           # Tabla de turnos con filtros y acciones CRUD
    │   ├── agregar_turno.html    # Modo simple / bloque con preview Alpine.js
    │   ├── editar_turno.html     # Editar fecha u horario de un turno
    │   └── reservas.html         # Historial de reservas de pacientes
    └── paciente/
        ├── turnos.html           # Buscar y reservar turnos (modal Alpine.js)
        └── mis_turnos.html       # Mis reservas con cancelación inline
```

---

## Base de datos

### Tablas

| Tabla | Descripción |
|---|---|
| `usuarios` | Pacientes, médicos y administradores |
| `medicos` | Especialidad, matrícula, descripción, **precio_consulta** y **notas** (reglas de convivencia) |
| `turnos` | Fecha, horario y estado de cada turno |
| `reservas` | Relación paciente ↔ turno con motivo y estado |

### Estados de un turno

| Estado | Descripción |
|---|---|
| `disponible` | Visible y reservable por pacientes |
| `ocupado` | Tiene una reserva confirmada |
| `deshabilitado` | Ocultado por el médico, no reservable |

### Estados de una reserva

| Estado | Descripción |
|---|---|
| `confirmada` | Reserva activa |
| `cancelada` | Cancelada por el paciente |

### Catálogo de especialidades

Definido en [app.py](app.py) como `ESPECIALIDADES` (lista) y `ESPECIALIDADES_COLORES` (dict con clases Tailwind por especialidad). Incluye 33 especialidades médicas (Cardiología, Pediatría, Neurología, Dermatología, etc.), cada una con su color asignado. Para agregar una nueva: editar ambas estructuras en `app.py`.

---

## Comandos útiles

**Levantar la app (cada vez):**
```bash
venv\Scripts\activate
python app.py
```

**Reinstalar dependencias:**
```bash
pip install -r requirements.txt
```

**Ver tablas en MySQL Workbench:**
Conectate a `localhost`, abrí el schema `turnosalud` y navegá las tablas desde el panel izquierdo.
