from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import pymysql.cursors
from datetime import datetime, timedelta, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'turnosalud-dev-secret-2024'

# ─── MySQL config ─────────────────────────────────────────────────────────────
DB_HOST     = 'localhost'
DB_USER     = 'root'
DB_PASSWORD = 'admin'   # ← cambiá esto por tu contraseña de MySQL
DB_NAME     = 'turnosalud'

# ─── DB helpers ───────────────────────────────────────────────────────────────

def get_db():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def query_db(query, args=(), one=False):
    db  = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    rv  = cur.fetchall()
    db.close()
    return (rv[0] if rv else None) if one else rv

def modify_db(query, args=()):
    db  = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    db.commit()
    db.close()

def modify_db_id(query, args=()):
    db      = get_db()
    cur     = db.cursor()
    cur.execute(query, args)
    last_id = cur.lastrowid
    db.commit()
    db.close()
    return last_id

# ─── Template filters ─────────────────────────────────────────────────────────

@app.template_filter('fecha_formato')
def fecha_formato(value):
    d      = datetime.strptime(str(value), '%Y-%m-%d') if isinstance(value, str) else value
    dias   = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    meses  = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
               'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    return f"{dias[d.weekday()]} {d.day} de {meses[d.month - 1]}"

# ─── Auth decorators ──────────────────────────────────────────────────────────

def paciente_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debés iniciar sesión para continuar.', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'paciente':
            flash('Acceso no autorizado.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def medico_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debés iniciar sesión para continuar.', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'medico':
            flash('Acceso no autorizado.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debés iniciar sesión para continuar.', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            flash('Acceso no autorizado.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── Init DB ──────────────────────────────────────────────────────────────────

def init_db():
    db  = get_db()
    cur = db.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            nombre      VARCHAR(100) NOT NULL,
            apellido    VARCHAR(100) NOT NULL,
            email       VARCHAR(255) UNIQUE NOT NULL,
            password    VARCHAR(255) NOT NULL,
            rol         VARCHAR(20)  NOT NULL DEFAULT 'paciente',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS medicos (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id   INT  NOT NULL UNIQUE,
            especialidad VARCHAR(100) NOT NULL,
            matricula    VARCHAR(50),
            descripcion  TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS turnos (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            medico_id   INT  NOT NULL,
            fecha       DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fin    TIME NOT NULL,
            estado      VARCHAR(20) NOT NULL DEFAULT 'disponible',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medico_id) REFERENCES medicos(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            turno_id      INT  NOT NULL UNIQUE,
            paciente_id   INT  NOT NULL,
            motivo        TEXT,
            estado        VARCHAR(20) NOT NULL DEFAULT 'confirmada',
            fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (turno_id)    REFERENCES turnos(id),
            FOREIGN KEY (paciente_id) REFERENCES usuarios(id)
        )
    ''')

    db.commit()

    cur.execute('SELECT COUNT(*) AS count FROM usuarios')
    if cur.fetchone()['count'] == 0:
        _seed(db)

    # Garantizar que siempre exista al menos un admin
    cur.execute("SELECT COUNT(*) AS count FROM usuarios WHERE rol = 'admin'")
    if cur.fetchone()['count'] == 0:
        pw = generate_password_hash('admin123')
        cur.execute(
            'INSERT INTO usuarios (nombre, apellido, email, password, rol) VALUES (%s,%s,%s,%s,%s)',
            ('Admin', 'Sistema', 'admin@turnosalud.com', pw, 'admin')
        )
        db.commit()

    cur.close()
    db.close()


def _seed(db):
    cur     = db.cursor()
    doctors = [
        ('Carlos', 'Rodríguez', 'carlos@turnosalud.com', 'Cardiología',   'MN 12345',
         'Especialista en cardiología clínica con 15 años de experiencia. Diagnóstico y tratamiento de patologías cardíacas.'),
        ('Ana',    'Martínez',  'ana@turnosalud.com',    'Pediatría',     'MN 23456',
         'Pediatra con enfoque en medicina preventiva y desarrollo infantil. Atención de 0 a 18 años.'),
        ('Luis',   'García',    'luis@turnosalud.com',   'Traumatología', 'MN 34567',
         'Especialista en lesiones deportivas y cirugía ortopédica. Recuperación funcional integral.'),
        ('María',  'López',     'maria@turnosalud.com',  'Dermatología',  'MN 45678',
         'Dermatóloga clínica y estética. Diagnóstico y tratamiento de enfermedades de la piel.'),
    ]
    for nombre, apellido, email, esp, mat, desc in doctors:
        pw = generate_password_hash('medico123')
        cur.execute('INSERT INTO usuarios (nombre, apellido, email, password, rol) VALUES (%s,%s,%s,%s,%s)',
                    (nombre, apellido, email, pw, 'medico'))
        uid = cur.lastrowid
        cur.execute('INSERT INTO medicos (usuario_id, especialidad, matricula, descripcion) VALUES (%s,%s,%s,%s)',
                    (uid, esp, mat, desc))

    pw = generate_password_hash('paciente123')
    cur.execute('INSERT INTO usuarios (nombre, apellido, email, password, rol) VALUES (%s,%s,%s,%s,%s)',
                ('Juan', 'Pérez', 'juan@email.com', pw, 'paciente'))

    cur.execute('SELECT id FROM medicos')
    medico_ids = [r['id'] for r in cur.fetchall()]

    today    = date.today()
    weekdays = 0
    offset   = 1
    while weekdays < 10:
        d = today + timedelta(days=offset)
        if d.weekday() < 5:
            for mid in medico_ids:
                for hour in ['09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
                             '14:00', '14:30', '15:00', '15:30', '16:00', '16:30']:
                    h, m  = map(int, hour.split(':'))
                    total = h * 60 + m + 30
                    end   = f"{total // 60:02d}:{total % 60:02d}"
                    cur.execute(
                        'INSERT INTO turnos (medico_id, fecha, hora_inicio, hora_fin) VALUES (%s,%s,%s,%s)',
                        (mid, d.isoformat(), hour, end)
                    )
            weekdays += 1
        offset += 1

    db.commit()
    cur.close()

# ─── Session guard ────────────────────────────────────────────────────────────

@app.before_request
def verificar_sesion():
    """Si el user_id guardado en sesión ya no existe en la BD, limpia la sesión."""
    if 'user_id' in session:
        user = query_db('SELECT id FROM usuarios WHERE id = %s', [session['user_id']], one=True)
        if not user:
            session.clear()

# ─── Context processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return {'current_year': datetime.now().year}

# ─── Public ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    medicos = query_db('''
        SELECT u.id, u.nombre, u.apellido,
               m.id AS medico_id, m.especialidad, m.descripcion,
               COUNT(CASE WHEN t.estado = 'disponible' AND t.fecha >= CURDATE() THEN 1 END) AS disponibles
        FROM usuarios u
        JOIN medicos m  ON u.id = m.usuario_id
        LEFT JOIN turnos t ON m.id = t.medico_id
        GROUP BY u.id, m.id
        ORDER BY m.especialidad
    ''')
    return render_template('index.html', medicos=medicos)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user     = query_db('SELECT * FROM usuarios WHERE email = %s', [email], one=True)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['nombre']  = user['nombre']
            session['rol']     = user['rol']
            flash(f'¡Bienvenido/a, {user["nombre"]}!', 'success')
            destinos = {'medico': 'medico_dashboard', 'admin': 'admin_dashboard'}
            return redirect(url_for(destinos.get(user['rol'], 'paciente_turnos')))

        flash('Email o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if not all([nombre, apellido, email, password]):
            flash('Todos los campos son obligatorios.', 'danger')
        elif password != confirm:
            flash('Las contraseñas no coinciden.', 'danger')
        elif len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        elif query_db('SELECT id FROM usuarios WHERE email = %s', [email], one=True):
            flash('Ya existe una cuenta con ese email.', 'danger')
        else:
            uid = modify_db_id(
                'INSERT INTO usuarios (nombre, apellido, email, password, rol) VALUES (%s,%s,%s,%s,%s)',
                (nombre, apellido, email, generate_password_hash(password), 'paciente')
            )
            session['user_id'] = uid
            session['nombre']  = nombre
            session['rol']     = 'paciente'
            flash('¡Cuenta creada exitosamente!', 'success')
            return redirect(url_for('paciente_turnos'))

    return render_template('auth/register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('index'))

# ─── Paciente ─────────────────────────────────────────────────────────────────

@app.route('/paciente/turnos')
@paciente_required
def paciente_turnos():
    especialidad = request.args.get('especialidad', '')
    medico_id    = request.args.get('medico_id', '')
    fecha        = request.args.get('fecha', '')

    q = '''
        SELECT t.id,
               DATE_FORMAT(t.fecha, '%%Y-%%m-%%d') AS fecha,
               TIME_FORMAT(t.hora_inicio, '%%H:%%i') AS hora_inicio,
               TIME_FORMAT(t.hora_fin,    '%%H:%%i') AS hora_fin,
               t.estado,
               u.nombre, u.apellido, m.id AS medico_id, m.especialidad
        FROM turnos t
        JOIN medicos m  ON t.medico_id  = m.id
        JOIN usuarios u ON m.usuario_id = u.id
        WHERE t.fecha >= CURDATE()
    '''
    params = []
    if especialidad:
        q += ' AND m.especialidad = %s'; params.append(especialidad)
    if medico_id:
        q += ' AND m.id = %s';           params.append(medico_id)
    if fecha:
        q += ' AND t.fecha = %s';        params.append(fecha)
    q += ' ORDER BY t.fecha, t.hora_inicio'

    turnos         = query_db(q, params)
    especialidades = query_db('SELECT DISTINCT especialidad FROM medicos ORDER BY especialidad')
    medicos        = query_db('''
        SELECT m.id, u.nombre, u.apellido, m.especialidad
        FROM medicos m JOIN usuarios u ON m.usuario_id = u.id ORDER BY u.apellido
    ''')

    return render_template('paciente/turnos.html',
                           turnos=turnos, especialidades=especialidades, medicos=medicos,
                           filtro_especialidad=especialidad,
                           filtro_medico=medico_id,
                           filtro_fecha=fecha)


@app.route('/paciente/reservar/<int:turno_id>', methods=['POST'])
@paciente_required
def paciente_reservar(turno_id):
    motivo = request.form.get('motivo', '').strip()
    turno  = query_db('SELECT * FROM turnos WHERE id = %s', [turno_id], one=True)

    if not turno or turno['estado'] != 'disponible':
        flash('Este turno ya no está disponible.', 'warning')
        return redirect(url_for('paciente_turnos'))

    ya_tiene = query_db('''
        SELECT r.id FROM reservas r
        JOIN turnos t ON r.turno_id = t.id
        WHERE r.paciente_id = %s AND t.fecha = %s AND t.medico_id = %s AND r.estado = 'confirmada'
    ''', [session['user_id'], turno['fecha'], turno['medico_id']], one=True)

    if ya_tiene:
        flash('Ya tenés un turno con este médico ese día.', 'warning')
        return redirect(url_for('paciente_turnos'))

    try:
        modify_db('UPDATE turnos SET estado = %s WHERE id = %s', ('ocupado', turno_id))
        modify_db('INSERT INTO reservas (turno_id, paciente_id, motivo) VALUES (%s,%s,%s)',
                  (turno_id, session['user_id'], motivo))
    except Exception:
        # Revertir el estado del turno si la reserva falló
        modify_db('UPDATE turnos SET estado = %s WHERE id = %s', ('disponible', turno_id))
        session.clear()
        flash('Sesión expirada. Iniciá sesión nuevamente.', 'warning')
        return redirect(url_for('login'))

    flash('¡Turno reservado exitosamente!', 'success')
    return redirect(url_for('paciente_mis_turnos'))


@app.route('/paciente/mis-turnos')
@paciente_required
def paciente_mis_turnos():
    reservas = query_db('''
        SELECT r.id, r.motivo, r.estado, r.fecha_reserva,
               t.id AS turno_id,
               DATE_FORMAT(t.fecha, '%%Y-%%m-%%d')    AS fecha,
               TIME_FORMAT(t.hora_inicio, '%%H:%%i')  AS hora_inicio,
               TIME_FORMAT(t.hora_fin,    '%%H:%%i')  AS hora_fin,
               u.nombre, u.apellido, m.especialidad
        FROM reservas r
        JOIN turnos t   ON r.turno_id   = t.id
        JOIN medicos m  ON t.medico_id  = m.id
        JOIN usuarios u ON m.usuario_id = u.id
        WHERE r.paciente_id = %s
        ORDER BY t.fecha DESC, t.hora_inicio DESC
    ''', [session['user_id']])
    return render_template('paciente/mis_turnos.html', reservas=reservas)


@app.route('/paciente/cancelar/<int:reserva_id>', methods=['POST'])
@paciente_required
def paciente_cancelar(reserva_id):
    reserva = query_db('''
        SELECT r.*, t.id AS turno_id FROM reservas r JOIN turnos t ON r.turno_id = t.id
        WHERE r.id = %s AND r.paciente_id = %s
    ''', [reserva_id, session['user_id']], one=True)

    if not reserva or reserva['estado'] != 'confirmada':
        flash('Reserva no encontrada o ya cancelada.', 'warning')
        return redirect(url_for('paciente_mis_turnos'))

    modify_db('UPDATE reservas SET estado = %s WHERE id = %s', ('cancelada', reserva_id))
    modify_db('UPDATE turnos SET estado = %s WHERE id = %s', ('disponible', reserva['turno_id']))
    flash('Turno cancelado.', 'info')
    return redirect(url_for('paciente_mis_turnos'))

# ─── Médico ───────────────────────────────────────────────────────────────────

def _get_medico_id():
    row = query_db('SELECT id FROM medicos WHERE usuario_id = %s', [session['user_id']], one=True)
    return row['id'] if row else None


@app.route('/medico/dashboard')
@medico_required
def medico_dashboard():
    mid = _get_medico_id()
    stats = query_db('''
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN estado = 'disponible' AND fecha >= CURDATE() THEN 1 ELSE 0 END) AS disponibles,
            SUM(CASE WHEN estado = 'ocupado'                           THEN 1 ELSE 0 END) AS ocupados,
            SUM(CASE WHEN estado = 'deshabilitado'                     THEN 1 ELSE 0 END) AS deshabilitados
        FROM turnos WHERE medico_id = %s
    ''', [mid], one=True)

    proximas = query_db('''
        SELECT DATE_FORMAT(t.fecha, '%%Y-%%m-%%d')   AS fecha,
               TIME_FORMAT(t.hora_inicio, '%%H:%%i') AS hora_inicio,
               TIME_FORMAT(t.hora_fin,    '%%H:%%i') AS hora_fin,
               u.nombre, u.apellido, u.email, r.motivo
        FROM reservas r
        JOIN turnos t   ON r.turno_id   = t.id
        JOIN usuarios u ON r.paciente_id = u.id
        WHERE t.medico_id = %s AND t.fecha >= CURDATE() AND r.estado = 'confirmada'
        ORDER BY t.fecha, t.hora_inicio
        LIMIT 6
    ''', [mid])

    return render_template('medico/dashboard.html', stats=stats, proximas=proximas)


@app.route('/medico/turnos')
@medico_required
def medico_turnos():
    mid           = _get_medico_id()
    filtro_fecha  = request.args.get('fecha', '')
    filtro_estado = request.args.get('estado', '')

    q = '''
        SELECT t.id,
               DATE_FORMAT(t.fecha, '%%Y-%%m-%%d')   AS fecha,
               TIME_FORMAT(t.hora_inicio, '%%H:%%i') AS hora_inicio,
               TIME_FORMAT(t.hora_fin,    '%%H:%%i') AS hora_fin,
               t.estado,
               r.id AS reserva_id, r.motivo,
               u.nombre, u.apellido, u.email
        FROM turnos t
        LEFT JOIN reservas r ON t.id = r.turno_id AND r.estado = 'confirmada'
        LEFT JOIN usuarios u ON r.paciente_id = u.id
        WHERE t.medico_id = %s
    '''
    params = [mid]
    if filtro_fecha:
        q += ' AND t.fecha = %s';   params.append(filtro_fecha)
    if filtro_estado:
        q += ' AND t.estado = %s';  params.append(filtro_estado)
    q += ' ORDER BY t.fecha, t.hora_inicio'

    turnos = query_db(q, params)
    return render_template('medico/turnos.html', turnos=turnos,
                           filtro_fecha=filtro_fecha, filtro_estado=filtro_estado)


@app.route('/medico/turnos/agregar', methods=['GET', 'POST'])
@medico_required
def medico_agregar_turno():
    mid      = _get_medico_id()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    if request.method == 'POST':
        modo        = request.form.get('modo', 'simple')
        fecha       = request.form.get('fecha', '')
        hora_inicio = request.form.get('hora_inicio', '')
        hora_fin    = request.form.get('hora_fin', '')

        if not all([fecha, hora_inicio, hora_fin]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('medico/agregar_turno.html', tomorrow=tomorrow)

        if hora_inicio >= hora_fin:
            flash('La hora de inicio debe ser anterior a la hora de fin.', 'danger')
            return render_template('medico/agregar_turno.html', tomorrow=tomorrow)

        if modo == 'bloque':
            intervalo    = int(request.form.get('intervalo', 30))
            h, m         = map(int, hora_inicio.split(':'))
            end_h, end_m = map(int, hora_fin.split(':'))
            end_total    = end_h * 60 + end_m
            created      = 0

            while h * 60 + m + intervalo <= end_total:
                s_str   = f"{h:02d}:{m:02d}"
                t_total = h * 60 + m + intervalo
                e_str   = f"{t_total // 60:02d}:{t_total % 60:02d}"
                if not query_db('SELECT id FROM turnos WHERE medico_id=%s AND fecha=%s AND hora_inicio=%s',
                                [mid, fecha, s_str], one=True):
                    modify_db('INSERT INTO turnos (medico_id, fecha, hora_inicio, hora_fin) VALUES (%s,%s,%s,%s)',
                              (mid, fecha, s_str, e_str))
                    created += 1
                h, m = divmod(t_total, 60)

            flash(f'Se crearon {created} turno(s).', 'success')
        else:
            if query_db('SELECT id FROM turnos WHERE medico_id=%s AND fecha=%s AND hora_inicio=%s',
                        [mid, fecha, hora_inicio], one=True):
                flash('Ya existe un turno en esa fecha y horario.', 'warning')
                return render_template('medico/agregar_turno.html', tomorrow=tomorrow)

            modify_db('INSERT INTO turnos (medico_id, fecha, hora_inicio, hora_fin) VALUES (%s,%s,%s,%s)',
                      (mid, fecha, hora_inicio, hora_fin))
            flash('Turno agregado.', 'success')

        return redirect(url_for('medico_turnos'))

    return render_template('medico/agregar_turno.html', tomorrow=tomorrow)


@app.route('/medico/turnos/<int:turno_id>/toggle', methods=['POST'])
@medico_required
def medico_toggle_turno(turno_id):
    mid   = _get_medico_id()
    turno = query_db('SELECT * FROM turnos WHERE id = %s AND medico_id = %s', [turno_id, mid], one=True)

    if not turno:
        flash('Turno no encontrado.', 'danger')
    elif turno['estado'] == 'ocupado':
        flash('No se puede modificar un turno con paciente asignado.', 'warning')
    else:
        nuevo = 'deshabilitado' if turno['estado'] == 'disponible' else 'disponible'
        modify_db('UPDATE turnos SET estado = %s WHERE id = %s', (nuevo, turno_id))
        flash('Turno deshabilitado.' if nuevo == 'deshabilitado' else 'Turno habilitado.', 'info')

    return redirect(url_for('medico_turnos'))


@app.route('/medico/turnos/<int:turno_id>/eliminar', methods=['POST'])
@medico_required
def medico_eliminar_turno(turno_id):
    mid   = _get_medico_id()
    turno = query_db('SELECT * FROM turnos WHERE id = %s AND medico_id = %s', [turno_id, mid], one=True)

    if not turno:
        flash('Turno no encontrado.', 'danger')
    elif turno['estado'] == 'ocupado':
        flash('No podés eliminar un turno con paciente asignado.', 'warning')
    else:
        modify_db('DELETE FROM turnos WHERE id = %s', [turno_id])
        flash('Turno eliminado.', 'info')

    return redirect(url_for('medico_turnos'))


@app.route('/medico/turnos/<int:turno_id>/editar', methods=['GET', 'POST'])
@medico_required
def medico_editar_turno(turno_id):
    mid   = _get_medico_id()
    turno = query_db('''
        SELECT id,
               DATE_FORMAT(fecha, '%%Y-%%m-%%d')   AS fecha,
               TIME_FORMAT(hora_inicio, '%%H:%%i') AS hora_inicio,
               TIME_FORMAT(hora_fin,    '%%H:%%i') AS hora_fin,
               estado
        FROM turnos WHERE id = %s AND medico_id = %s
    ''', [turno_id, mid], one=True)

    if not turno:
        flash('Turno no encontrado.', 'danger')
        return redirect(url_for('medico_turnos'))

    if turno['estado'] == 'ocupado':
        flash('No se puede editar un turno con paciente asignado.', 'warning')
        return redirect(url_for('medico_turnos'))

    if request.method == 'POST':
        fecha       = request.form.get('fecha', '')
        hora_inicio = request.form.get('hora_inicio', '')
        hora_fin    = request.form.get('hora_fin', '')

        if not all([fecha, hora_inicio, hora_fin]):
            flash('Todos los campos son obligatorios.', 'danger')
        elif hora_inicio >= hora_fin:
            flash('La hora de inicio debe ser anterior a la hora de fin.', 'danger')
        else:
            duplicado = query_db(
                'SELECT id FROM turnos WHERE medico_id=%s AND fecha=%s AND hora_inicio=%s AND id != %s',
                [mid, fecha, hora_inicio, turno_id], one=True
            )
            if duplicado:
                flash('Ya existe otro turno en esa fecha y horario.', 'warning')
            else:
                modify_db(
                    'UPDATE turnos SET fecha=%s, hora_inicio=%s, hora_fin=%s WHERE id=%s',
                    (fecha, hora_inicio, hora_fin, turno_id)
                )
                flash('Turno actualizado.', 'success')
                return redirect(url_for('medico_turnos'))

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    return render_template('medico/editar_turno.html', turno=turno, tomorrow=tomorrow)


@app.route('/medico/reservas')
@medico_required
def medico_reservas():
    mid = _get_medico_id()
    reservas = query_db('''
        SELECT r.id, r.motivo, r.estado, r.fecha_reserva,
               DATE_FORMAT(t.fecha, '%%Y-%%m-%%d')   AS fecha,
               TIME_FORMAT(t.hora_inicio, '%%H:%%i') AS hora_inicio,
               TIME_FORMAT(t.hora_fin,    '%%H:%%i') AS hora_fin,
               u.nombre, u.apellido, u.email
        FROM reservas r
        JOIN turnos t   ON r.turno_id   = t.id
        JOIN usuarios u ON r.paciente_id = u.id
        WHERE t.medico_id = %s
        ORDER BY t.fecha DESC, t.hora_inicio DESC
    ''', [mid])
    return render_template('medico/reservas.html', reservas=reservas)


# ─── Admin ────────────────────────────────────────────────────────────────────

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    stats = query_db('''
        SELECT
            (SELECT COUNT(*) FROM medicos)                                            AS total_medicos,
            (SELECT COUNT(*) FROM usuarios WHERE rol = 'paciente')                   AS total_pacientes,
            (SELECT COUNT(*) FROM turnos WHERE fecha >= CURDATE())                   AS turnos_proximos,
            (SELECT COUNT(*) FROM reservas WHERE estado = 'confirmada')              AS reservas_activas,
            (SELECT COUNT(*) FROM reservas r
             JOIN turnos t ON r.turno_id = t.id
             WHERE t.fecha = CURDATE() AND r.estado = 'confirmada')                  AS reservas_hoy
    ''', one=True)

    recientes = query_db('''
        SELECT r.fecha_reserva, r.estado,
               DATE_FORMAT(t.fecha, '%%Y-%%m-%%d')   AS fecha,
               TIME_FORMAT(t.hora_inicio, '%%H:%%i') AS hora_inicio,
               up.nombre AS p_nombre, up.apellido AS p_apellido,
               um.nombre AS m_nombre, um.apellido AS m_apellido,
               m.especialidad
        FROM reservas r
        JOIN turnos t   ON r.turno_id    = t.id
        JOIN medicos m  ON t.medico_id   = m.id
        JOIN usuarios um ON m.usuario_id = um.id
        JOIN usuarios up ON r.paciente_id = up.id
        ORDER BY r.fecha_reserva DESC
        LIMIT 8
    ''')
    return render_template('admin/dashboard.html', stats=stats, recientes=recientes)


@app.route('/admin/medicos')
@admin_required
def admin_medicos():
    medicos = query_db('''
        SELECT u.id, u.nombre, u.apellido, u.email,
               DATE_FORMAT(u.created_at, '%%Y-%%m-%%d') AS created_at,
               m.id AS medico_id, m.especialidad, m.matricula,
               COUNT(CASE WHEN t.estado = 'disponible' AND t.fecha >= CURDATE() THEN 1 END) AS disponibles,
               COUNT(CASE WHEN t.estado = 'ocupado'                              THEN 1 END) AS ocupados
        FROM usuarios u
        JOIN medicos m  ON u.id = m.usuario_id
        LEFT JOIN turnos t ON m.id = t.medico_id
        GROUP BY u.id, m.id
        ORDER BY u.apellido
    ''')
    return render_template('admin/medicos.html', medicos=medicos)


@app.route('/admin/medicos/crear', methods=['GET', 'POST'])
@admin_required
def admin_crear_medico():
    if request.method == 'POST':
        nombre       = request.form.get('nombre', '').strip()
        apellido     = request.form.get('apellido', '').strip()
        email        = request.form.get('email', '').strip()
        password     = request.form.get('password', '')
        especialidad = request.form.get('especialidad', '').strip()
        matricula    = request.form.get('matricula', '').strip()
        descripcion  = request.form.get('descripcion', '').strip()

        if not all([nombre, apellido, email, password, especialidad]):
            flash('Nombre, apellido, email, contraseña y especialidad son obligatorios.', 'danger')
        elif query_db('SELECT id FROM usuarios WHERE email = %s', [email], one=True):
            flash('Ya existe un usuario con ese email.', 'danger')
        else:
            uid = modify_db_id(
                'INSERT INTO usuarios (nombre, apellido, email, password, rol) VALUES (%s,%s,%s,%s,%s)',
                (nombre, apellido, email, generate_password_hash(password), 'medico')
            )
            modify_db(
                'INSERT INTO medicos (usuario_id, especialidad, matricula, descripcion) VALUES (%s,%s,%s,%s)',
                (uid, especialidad, matricula or None, descripcion or None)
            )
            flash(f'Cuenta creada para Dr/a. {nombre} {apellido}.', 'success')
            return redirect(url_for('admin_medicos'))

    return render_template('admin/crear_medico.html')


@app.route('/admin/medicos/<int:medico_id>/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_medico(medico_id):
    tiene_futuras = query_db('''
        SELECT r.id FROM reservas r
        JOIN turnos t ON r.turno_id = t.id
        WHERE t.medico_id = %s AND t.fecha >= CURDATE() AND r.estado = 'confirmada'
        LIMIT 1
    ''', [medico_id], one=True)

    if tiene_futuras:
        flash('No se puede eliminar: el médico tiene turnos reservados próximos.', 'danger')
        return redirect(url_for('admin_medicos'))

    medico = query_db('SELECT usuario_id FROM medicos WHERE id = %s', [medico_id], one=True)
    if not medico:
        flash('Médico no encontrado.', 'danger')
        return redirect(url_for('admin_medicos'))

    modify_db('DELETE r FROM reservas r JOIN turnos t ON r.turno_id = t.id WHERE t.medico_id = %s', [medico_id])
    modify_db('DELETE FROM turnos WHERE medico_id = %s', [medico_id])
    modify_db('DELETE FROM medicos WHERE id = %s', [medico_id])
    modify_db('DELETE FROM usuarios WHERE id = %s', [medico['usuario_id']])
    flash('Médico eliminado.', 'info')
    return redirect(url_for('admin_medicos'))


@app.route('/admin/pacientes')
@admin_required
def admin_pacientes():
    pacientes = query_db('''
        SELECT u.id, u.nombre, u.apellido, u.email,
               DATE_FORMAT(u.created_at, '%%Y-%%m-%%d') AS created_at,
               COUNT(r.id)                                                           AS total_reservas,
               SUM(CASE WHEN r.estado = 'confirmada' THEN 1 ELSE 0 END)             AS reservas_activas
        FROM usuarios u
        LEFT JOIN reservas r ON u.id = r.paciente_id
        WHERE u.rol = 'paciente'
        GROUP BY u.id
        ORDER BY u.apellido
    ''')
    return render_template('admin/pacientes.html', pacientes=pacientes)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
