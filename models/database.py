import datetime
import sqlite3
import pandas as pd
import requests
import streamlit as st


def _obtener_secreto(seccion, clave, default=None):
    """Obtiene un secreto de st.secrets de manera segura sin lanzar excepciones."""
    try:
        if hasattr(st, "secrets") and seccion in st.secrets:
            return st.secrets[seccion].get(clave, default)
    except Exception:
        pass
    return default


class TursoCursor:
    """Cursor compatible con la interfaz DB-API de Python para Turso v2 Pipeline HTTP."""

    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self._rows = []

    def _format_value(self, val):
        if val is None:
            return {"type": "null"}
        elif isinstance(val, bool):
            return {"type": "integer", "value": "1" if val else "0"}
        elif isinstance(val, (int,)):
            return {"type": "integer", "value": str(val)}
        elif isinstance(val, float):
            return {"type": "float", "value": val}
        else:
            return {"type": "text", "value": str(val)}

    def _parse_row(self, row_data):
        parsed = []
        for cell in row_data:
            c_type = cell.get("type")
            c_val = cell.get("value")
            if c_type == "null" or c_val is None:
                parsed.append(None)
            elif c_type == "integer":
                parsed.append(int(c_val))
            elif c_type == "float":
                parsed.append(float(c_val))
            else:
                parsed.append(str(c_val))
        return tuple(parsed)

    def execute(self, sql, params=()):
        stmt = {"sql": sql}
        if params:
            stmt["args"] = [self._format_value(p) for p in params]

        body = {"requests": [{"type": "execute", "stmt": stmt}]}
        resp = self.connection.session.post(
            self.connection.pipeline_url, json=body, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        first_res = data["results"][0]
        if first_res.get("type") == "error":
            raise Exception(first_res.get("error", {}).get("message", "Error en Turso"))

        exec_res = first_res.get("response", {}).get("result", {})
        cols = exec_res.get("cols", [])
        self.description = [(c["name"],) for c in cols] if cols else None

        raw_rows = exec_res.get("rows", [])
        self._rows = [self._parse_row(r) for r in raw_rows]
        return self

    def executemany(self, sql, param_list, batch_size=100):
        if not param_list:
            return self

        for i in range(0, len(param_list), batch_size):
            batch = param_list[i : i + batch_size]
            requests_list = []
            for params in batch:
                stmt = {"sql": sql, "args": [self._format_value(p) for p in params]}
                requests_list.append({"type": "execute", "stmt": stmt})

            body = {"requests": requests_list}
            resp = self.connection.session.post(
                self.connection.pipeline_url, json=body, timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            for r in data.get("results", []):
                if r.get("type") == "error":
                    raise Exception(
                        r.get("error", {}).get("message", "Error por lotes en Turso")
                    )
        return self

    def fetchall(self):
        rows = self._rows
        self._rows = []
        return rows

    def fetchone(self):
        if self._rows:
            return self._rows.pop(0)
        return None

    def close(self):
        self._rows = []


class TursoConnection:
    """Conexión HTTP a Turso que implementa la interfaz estándar de conexión."""

    def __init__(self, url, auth_token):
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://") :]
        self.base_url = url.rstrip("/")
        self.pipeline_url = f"{self.base_url}/v2/pipeline"
        self.auth_token = auth_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            }
        )

    def cursor(self):
        return TursoCursor(self)

    def commit(self):
        pass

    def close(self):
        pass


class DatabaseModel:

    def __init__(self, db_name="horarios.db"):
        self.db_name = db_name

        # Obtener credenciales de Turso de forma segura
        self.turso_url = _obtener_secreto("turso", "url")
        self.turso_token = _obtener_secreto("turso", "auth_token")

        self._turso_conn = None
        if self.turso_url and self.turso_token:
            try:
                self._turso_conn = TursoConnection(self.turso_url, self.turso_token)
            except Exception as e:
                print(f"⚠️ No se pudo inicializar Turso: {e}. Usando SQLite local.")
                self._turso_conn = None

        self.crear_tablas()

    def _obtener_conexion(self):
        """Devuelve conexión a Turso si está configurado, o SQLite local."""
        if self._turso_conn is not None:
            return self._turso_conn
        return sqlite3.connect(self.db_name)

    def crear_tablas(self):
        conn = self._obtener_conexion()
        cursor = conn.cursor()

        # Tabla de horarios y eventos
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS horarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                espacio TEXT,
                fecha TEXT,
                mes TEXT,
                dia_num INTEGER,
                dia TEXT,
                hora_inicio INTEGER,
                hora_fin INTEGER,
                asignatura TEXT,
                docente TEXT,
                tipo_evento TEXT DEFAULT 'clase',
                observacion TEXT DEFAULT ''
            )
            """
        )

        # Tabla de vigencia del semestre
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vigencia_semestre (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_inicio TEXT,
                fecha_fin TEXT
            )
            """
        )

        # Tabla de novedades e inasistencias
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS novedades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                espacio TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora_inicio INTEGER NOT NULL,
                hora_fin INTEGER NOT NULL,
                tipo_novedad TEXT NOT NULL,
                observacion TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()

    def obtener_todos_los_horarios(self):
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM horarios")
        rows = cursor.fetchall()

        columnas = [description[0] for description in cursor.description]
        conn.close()

        if not rows:
            return pd.DataFrame(columns=columnas)

        return pd.DataFrame(rows, columns=columnas)

    def eliminar_horario_por_id(self, record_id):
        """Elimina un evento o clase específica usando su ID."""
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM horarios WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()

    def actualizar_horario_por_id(
        self, record_id, asignatura, docente, observacion=""
    ):
        """Actualiza los datos de una clase o evento existente."""
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE horarios 
            SET asignatura = ?, docente = ?, observacion = ?
            WHERE id = ?
            """,
            (asignatura, docente, observacion, record_id),
        )
        conn.commit()
        conn.close()

    def vaciar_base_de_datos(self):
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM horarios")
        cursor.execute("DELETE FROM vigencia_semestre")
        cursor.execute("DELETE FROM novedades")
        conn.commit()
        conn.close()

    def agregar_evento_especial(
        self,
        espacio,
        fecha,
        h_ini,
        h_fin,
        asignatura,
        docente,
        observacion="",
    ):
        conn = self._obtener_conexion()
        cursor = conn.cursor()

        fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d").date()
        meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        dias = [
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
        ]

        mes = meses[fecha_dt.month - 1]
        dia_num = fecha_dt.day
        dia = dias[fecha_dt.weekday()]

        cursor.execute(
            """
            INSERT INTO horarios (espacio, fecha, mes, dia_num, dia, hora_inicio, hora_fin, asignatura, docente, tipo_evento, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'evento', ?)
            """,
            (
                espacio,
                fecha,
                mes,
                dia_num,
                dia,
                h_ini,
                h_fin,
                asignatura,
                docente,
                observacion,
            ),
        )

        conn.commit()
        conn.close()

    def obtener_vigencia_semestre(self):
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fecha_inicio, fecha_fin FROM vigencia_semestre ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return (
                False,
                "No se han configurado las fechas del semestre.",
                None,
                None,
            )

        f_ini = datetime.datetime.strptime(str(row[0])[:10], "%Y-%m-%d").date()
        f_fin = datetime.datetime.strptime(str(row[1])[:10], "%Y-%m-%d").date()
        hoy = datetime.date.today()

        if f_ini <= hoy <= f_fin:
            return True, "Semestre activo.", f_ini, f_fin
        elif hoy < f_ini:
            return (
                False,
                f"El semestre aún no inicia (Inicia el {f_ini}).",
                f_ini,
                f_fin,
            )
        else:
            return False, f"El semestre finalizó el {f_fin}.", f_ini, f_fin

    def verificar_conflicto_horario(self, espacio, fecha, h_ini, h_fin):
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, asignatura, docente, hora_inicio, hora_fin, tipo_evento 
            FROM horarios 
            WHERE espacio = ? AND fecha = ? AND (
                (hora_inicio < ? AND hora_fin > ?)
            )
            """,
            (espacio, fecha, h_fin, h_ini),
        )
        conflictos = cursor.fetchall()
        conn.close()
        return conflictos

    def reemplazar_horarios_semestre(self, df_final, f_inicio, f_fin):
        """Reemplaza los horarios regulares proyectados para el nuevo semestre."""
        conn = self._obtener_conexion()
        cursor = conn.cursor()

        # 1. Actualizar rango de fechas del semestre
        cursor.execute("DELETE FROM vigencia_semestre")
        cursor.execute(
            "INSERT INTO vigencia_semestre (fecha_inicio, fecha_fin) VALUES (?, ?)",
            (f_inicio.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")),
        )

        # 2. Limpiar clases regulares previas
        cursor.execute("DELETE FROM horarios WHERE tipo_evento = 'clase'")

        # 3. Insertar nuevos registros proyectados
        if not df_final.empty:
            cols = [
                "espacio",
                "fecha",
                "mes",
                "dia_num",
                "dia",
                "hora_inicio",
                "hora_fin",
                "asignatura",
                "docente",
                "tipo_evento",
                "observacion",
            ]
            datos = [tuple(row[c] for c in cols) for _, row in df_final.iterrows()]
            sql_insert = """
                INSERT INTO horarios (
                    espacio, fecha, mes, dia_num, dia, 
                    hora_inicio, hora_fin, asignatura, docente, 
                    tipo_evento, observacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.executemany(sql_insert, datos)

        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # MÉTODOS DE NOVEDADES
    # -------------------------------------------------------------------------
    def agregar_novedad(self, espacio, fecha, hora_inicio, hora_fin, tipo_novedad, observacion=""):
        """Registra una novedad puntual (cancelación, inasistencia, etc.) para una fecha específica."""
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        query = """
        INSERT INTO novedades (espacio, fecha, hora_inicio, hora_fin, tipo_novedad, observacion)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (espacio.upper(), fecha, hora_inicio, hora_fin, tipo_novedad, observacion))
        conn.commit()
        conn.close()

    def obtener_novedades_fecha(self, fecha):
        """Obtiene todas las novedades registradas para una fecha específica."""
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM novedades WHERE fecha = ?", (fecha,))
        rows = cursor.fetchall()
        columnas = [description[0] for description in cursor.description]
        conn.close()
        if not rows:
            return pd.DataFrame(columns=columnas)
        return pd.DataFrame(rows, columns=columnas)

    def obtener_todas_las_novedades(self):
        """Obtiene el historial completo de novedades registradas."""
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM novedades ORDER BY fecha DESC, hora_inicio ASC")
        rows = cursor.fetchall()
        columnas = [description[0] for description in cursor.description]
        conn.close()
        if not rows:
            return pd.DataFrame(columns=columnas)
        return pd.DataFrame(rows, columns=columnas)

    def eliminar_novedad(self, novedad_id):
        """Elimina/revierte una novedad previamente registrada."""
        conn = self._obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM novedades WHERE id = ?", (novedad_id,))
        conn.commit()
        conn.close()